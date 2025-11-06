"""
Session Management API Endpoints
세션 관리 API

Provides endpoints for managing counseling sessions:
- Start/end sessions
- Generate AI summaries
- Add session notes
- View session history
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.user import User
from app.models.session import Session
from app.models.conversation import Conversation, Message
from app.schemas.session import (
    SessionStartRequest,
    SessionEndRequest,
    SessionNoteRequest,
    SessionResponse,
    SessionSummaryResponse,
    SessionListResponse,
)
from app.services.openai_client import OpenAIClientFactory


router = APIRouter(prefix="/sessions", tags=["sessions"])


# ============================================================================
# Helper Functions
# ============================================================================

async def get_current_user(
    session_token: str, db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from session token"""
    result = await db.execute(
        select(User).where(
            User.session_token == session_token, User.is_deleted == False
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token"
        )
    return user


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/start", response_model=SessionResponse)
async def start_session(
    request: SessionStartRequest,
    session_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Start a new counseling session

    새 상담 세션 시작

    **Features:**
    - Create new session
    - Link to existing conversation or create new one
    - Track start time

    **Request Body:**
    ```json
    {
        "conversation_id": "uuid (optional)",
        "title": "Session title (optional)"
    }
    ```

    **Example Response:**
    ```json
    {
        "id": "uuid",
        "conversation_id": "uuid",
        "user_id": "uuid",
        "started_at": "2025-11-06T10:00:00Z",
        "ended_at": null,
        "duration_minutes": null,
        "summary": null,
        "notes": [],
        "message_count": 0,
        "crisis_level": 0,
        "created_at": "2025-11-06T10:00:00Z",
        "updated_at": "2025-11-06T10:00:00Z"
    }
    ```
    """
    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Get or create conversation
    if request.conversation_id:
        # Verify conversation exists and belongs to user
        conv_query = select(Conversation).where(
            Conversation.conversation_id == request.conversation_id,
            Conversation.user_id == user.user_id,
            Conversation.is_deleted == False
        )
        conv_result = await db.execute(conv_query)
        conversation = conv_result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
    else:
        # Create new conversation
        from app.services.conversation_service import ConversationService
        from app.services.openai_service import OpenAIService
        from app.services.cache_service import CacheService
        from app.core.redis import redis_manager

        cache_service = CacheService(redis_manager)
        openai_service = OpenAIService(cache_service=cache_service)
        conversation_service = ConversationService(db, openai_service)

        title = request.title or f"Session - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        conversation = await conversation_service.create_conversation(
            user_id=user.user_id,
            title=title
        )

    # Create session
    session = Session(
        conversation_id=conversation.conversation_id,
        user_id=user.user_id,
        started_at=datetime.utcnow(),
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return SessionResponse(
        id=session.session_id,
        conversation_id=session.conversation_id,
        user_id=session.user_id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_minutes=session.duration_minutes,
        summary=session.summary,
        notes=session.notes,
        message_count=session.message_count,
        crisis_level=session.crisis_level,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.put("/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: UUID,
    request: SessionEndRequest,
    session_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    End a counseling session

    상담 세션 종료

    **Features:**
    - Mark session as ended
    - Calculate duration
    - Add closing notes

    **Request Body:**
    ```json
    {
        "notes": "Session ended successfully. Good progress made."
    }
    ```

    **Example Response:**
    Session response with ended_at and duration_minutes filled
    """
    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Get session
    query = select(Session).where(
        Session.session_id == session_id,
        Session.user_id == user.user_id,
        Session.is_deleted == False
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if session.ended_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session already ended"
        )

    # Calculate message count for session
    msg_count_query = select(func.count()).select_from(Message).where(
        Message.conversation_id == session.conversation_id,
        Message.created_at >= session.started_at,
        Message.is_deleted == False
    )
    msg_count_result = await db.execute(msg_count_query)
    message_count = msg_count_result.scalar()

    # Get highest crisis level during session
    crisis_query = select(func.max(Message.detected_keywords)).where(
        Message.conversation_id == session.conversation_id,
        Message.created_at >= session.started_at,
        Message.is_deleted == False
    )
    # For now, use conversation crisis severity
    conv_query = select(Conversation.crisis_severity).where(
        Conversation.conversation_id == session.conversation_id
    )
    conv_result = await db.execute(conv_query)
    crisis_level = conv_result.scalar() or 0

    # End session
    session.ended_at = datetime.utcnow()
    duration = session.ended_at - session.started_at
    session.duration_minutes = int(duration.total_seconds() / 60)
    session.message_count = message_count
    session.crisis_level = crisis_level

    # Add closing notes if provided
    if request.notes:
        session.notes.append({
            "content": request.notes,
            "created_at": datetime.utcnow().isoformat(),
            "author": "user",
            "type": "closing"
        })

    session.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(session)

    return SessionResponse(
        id=session.session_id,
        conversation_id=session.conversation_id,
        user_id=session.user_id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_minutes=session.duration_minutes,
        summary=session.summary,
        notes=session.notes,
        message_count=session.message_count,
        crisis_level=session.crisis_level,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/{session_id}/summary", response_model=SessionSummaryResponse)
async def get_session_summary(
    session_id: UUID,
    session_token: str,
    regenerate: bool = Query(False, description="Force regenerate summary"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get AI-generated session summary

    AI 생성 세션 요약 조회

    **Features:**
    - AI-generated summary of session content
    - Key topics extraction
    - Emotion detection
    - Progress notes
    - Recommendations

    **Query Parameters:**
    - `regenerate`: Force regenerate summary even if exists (default: false)

    **Example Response:**
    ```json
    {
        "session_id": "uuid",
        "summary": "이번 세션에서는 학교 생활의 불안감에 대해 논의했습니다...",
        "key_topics": ["학교 불안", "시험 스트레스", "대처 기법"],
        "emotions_detected": ["anxiety", "stress", "hope"],
        "crisis_level": 1,
        "progress_notes": "내담자가 호흡법을 배우고 실천하기로 했습니다.",
        "recommendations": [
            "호흡 연습 지속하기",
            "인지 일지 작성 시작하기"
        ],
        "generated_at": "2025-11-06T10:30:00Z"
    }
    ```
    """
    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Get session
    query = select(Session).where(
        Session.session_id == session_id,
        Session.user_id == user.user_id,
        Session.is_deleted == False
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Check if summary exists and regenerate is false
    if session.summary and not regenerate:
        # Return cached summary
        metadata = session.metadata or {}
        return SessionSummaryResponse(
            session_id=session.session_id,
            summary=session.summary,
            key_topics=metadata.get("key_topics", []),
            emotions_detected=metadata.get("emotions_detected", []),
            crisis_level=session.crisis_level,
            progress_notes=metadata.get("progress_notes"),
            recommendations=metadata.get("recommendations", []),
            generated_at=session.updated_at,
        )

    # Get messages from session
    msg_query = select(Message).where(
        Message.conversation_id == session.conversation_id,
        Message.created_at >= session.started_at,
        Message.is_deleted == False
    )
    if session.ended_at:
        msg_query = msg_query.where(Message.created_at <= session.ended_at)

    msg_result = await db.execute(msg_query)
    messages = msg_result.scalars().all()

    if not messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No messages in session to summarize"
        )

    # Build conversation text
    conversation_text = ""
    for msg in messages:
        conversation_text += f"{msg.role}: {msg.content}\n\n"

    # Generate summary using GPT-4
    openai_client = OpenAIClientFactory.get_client()

    summary_prompt = f"""
다음 상담 세션의 내용을 분석하여 요약해주세요.

세션 대화:
{conversation_text}

다음 JSON 형식으로 반환하세요:
{{
    "summary": "세션 전체 요약 (2-3 문장)",
    "key_topics": ["주요 주제1", "주요 주제2", "주요 주제3"],
    "emotions_detected": ["감지된 주요 감정들"],
    "progress_notes": "세션에서의 진행사항 및 내담자 변화",
    "recommendations": ["다음 세션까지의 권장사항1", "권장사항2"]
}}
"""

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 전문 심리상담사입니다. 세션 내용을 요약하고 분석합니다."
                },
                {
                    "role": "user",
                    "content": summary_prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=800
        )

        import json
        summary_data = json.loads(response.choices[0].message.content)

        # Save to session
        session.summary = summary_data.get("summary", "")
        metadata = session.metadata or {}
        metadata.update({
            "key_topics": summary_data.get("key_topics", []),
            "emotions_detected": summary_data.get("emotions_detected", []),
            "progress_notes": summary_data.get("progress_notes"),
            "recommendations": summary_data.get("recommendations", []),
        })
        session.metadata = metadata
        session.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(session)

        return SessionSummaryResponse(
            session_id=session.session_id,
            summary=session.summary,
            key_topics=metadata.get("key_topics", []),
            emotions_detected=metadata.get("emotions_detected", []),
            crisis_level=session.crisis_level,
            progress_notes=metadata.get("progress_notes"),
            recommendations=metadata.get("recommendations", []),
            generated_at=datetime.utcnow(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate summary: {str(e)}"
        )


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    session_token: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user's session history

    세션 이력 조회

    **Features:**
    - Paginated list of sessions
    - Sorted by start time (newest first)
    - Includes session statistics

    **Query Parameters:**
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 20, max: 100)

    **Example Response:**
    ```json
    {
        "sessions": [
            {
                "id": "uuid",
                "conversation_id": "uuid",
                "started_at": "2025-11-06T10:00:00Z",
                "ended_at": "2025-11-06T10:45:00Z",
                "duration_minutes": 45,
                "summary": "Session summary...",
                "message_count": 23,
                "crisis_level": 1
            }
        ],
        "total": 5,
        "page": 1,
        "page_size": 20,
        "has_more": false
    }
    ```
    """
    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Build query
    query = select(Session).where(
        Session.user_id == user.user_id,
        Session.is_deleted == False
    )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(desc(Session.started_at)).limit(page_size).offset(offset)

    # Execute
    result = await db.execute(query)
    sessions = result.scalars().all()

    # Build response
    session_list = []
    for sess in sessions:
        session_list.append(
            SessionResponse(
                id=sess.session_id,
                conversation_id=sess.conversation_id,
                user_id=sess.user_id,
                started_at=sess.started_at,
                ended_at=sess.ended_at,
                duration_minutes=sess.duration_minutes,
                summary=sess.summary,
                notes=sess.notes,
                message_count=sess.message_count,
                crisis_level=sess.crisis_level,
                created_at=sess.created_at,
                updated_at=sess.updated_at,
            )
        )

    has_more = (offset + len(sessions)) < total

    return SessionListResponse(
        sessions=session_list,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.post("/{session_id}/notes", response_model=SessionResponse)
async def add_session_note(
    session_id: UUID,
    request: SessionNoteRequest,
    session_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Add a note to a session

    세션에 노트 추가

    **Features:**
    - Add timestamped notes
    - Multiple notes per session
    - Track note author

    **Request Body:**
    ```json
    {
        "content": "내담자가 호흡법을 잘 이해하고 적용하겠다고 했습니다."
    }
    ```

    **Example Response:**
    Session response with updated notes array
    """
    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Get session
    query = select(Session).where(
        Session.session_id == session_id,
        Session.user_id == user.user_id,
        Session.is_deleted == False
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Add note
    session.notes.append({
        "content": request.content,
        "created_at": datetime.utcnow().isoformat(),
        "author": "user",
        "type": "general"
    })

    session.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(session)

    return SessionResponse(
        id=session.session_id,
        conversation_id=session.conversation_id,
        user_id=session.user_id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_minutes=session.duration_minutes,
        summary=session.summary,
        notes=session.notes,
        message_count=session.message_count,
        crisis_level=session.crisis_level,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session_detail(
    session_id: UUID,
    session_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed session information

    세션 상세 조회

    **Example Response:**
    Full session details including all notes and metadata
    """
    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Get session
    query = select(Session).where(
        Session.session_id == session_id,
        Session.user_id == user.user_id,
        Session.is_deleted == False
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    return SessionResponse(
        id=session.session_id,
        conversation_id=session.conversation_id,
        user_id=session.user_id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_minutes=session.duration_minutes,
        summary=session.summary,
        notes=session.notes,
        message_count=session.message_count,
        crisis_level=session.crisis_level,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )
