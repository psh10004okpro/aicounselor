"""
Conversation Management API Endpoints
대화 관리 API

Provides endpoints for managing conversation history:
- List conversations
- Get conversation details
- Get messages
- Update conversation
- Delete conversation
- Search conversations
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.core.database import get_db
from app.core.redis import RedisManager, get_redis
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.schemas.conversation import (
    ConversationListResponse,
    ConversationListItem,
    ConversationDetailResponse,
    ConversationUpdateRequest,
    MessageListResponse,
    MessageResponse,
)
from app.services.cache_service import CacheService


router = APIRouter(prefix="/conversations", tags=["conversations"])


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

@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    session_token: str,
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    status_filter: Optional[str] = Query(None, description="Filter by status (active/archived)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get paginated list of user's conversations

    사용자의 대화 목록 조회 (페이징)

    **Features:**
    - Pagination support
    - Status filtering (active/archived)
    - Sorted by last message date (newest first)
    - Includes preview of last message
    - Message count per conversation

    **Query Parameters:**
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 20, max: 100)
    - `status_filter`: Filter by status - "active" or "archived" (optional)

    **Example:**
    ```
    GET /conversations?page=1&page_size=20&status_filter=active
    ```

    **Response:**
    ```json
    {
        "conversations": [
            {
                "id": "uuid",
                "title": "불안감 상담",
                "summary": "학교 생활에서의 불안...",
                "status": "active",
                "crisis_detected": false,
                "crisis_severity": 0,
                "message_count": 15,
                "last_message_preview": "감사합니다. 많은 도움이...",
                "created_at": "2025-11-01T10:00:00Z",
                "last_message_at": "2025-11-05T14:30:00Z"
            }
        ],
        "total": 10,
        "page": 1,
        "page_size": 20,
        "has_more": false
    }
    ```
    """
    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Build query
    query = select(Conversation).where(
        Conversation.user_id == user.user_id,
        Conversation.is_deleted == False
    )

    # Apply status filter
    if status_filter:
        query = query.where(Conversation.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(desc(Conversation.last_message_at)).limit(page_size).offset(offset)

    # Execute query
    result = await db.execute(query)
    conversations = result.scalars().all()

    # Build response items
    conversation_items = []
    for conv in conversations:
        # Get message count
        msg_count_query = select(func.count()).select_from(Message).where(
            Message.conversation_id == conv.conversation_id,
            Message.is_deleted == False
        )
        msg_count_result = await db.execute(msg_count_query)
        message_count = msg_count_result.scalar()

        # Get last message preview
        last_msg_query = select(Message).where(
            Message.conversation_id == conv.conversation_id,
            Message.is_deleted == False
        ).order_by(desc(Message.created_at)).limit(1)
        last_msg_result = await db.execute(last_msg_query)
        last_message = last_msg_result.scalar_one_or_none()

        last_message_preview = None
        if last_message:
            # Truncate to 100 characters
            last_message_preview = last_message.content[:100]
            if len(last_message.content) > 100:
                last_message_preview += "..."

        conversation_items.append(
            ConversationListItem(
                id=conv.conversation_id,
                title=conv.title,
                summary=conv.summary,
                status=conv.status,
                crisis_detected=conv.crisis_detected,
                crisis_severity=conv.crisis_severity,
                message_count=message_count,
                last_message_preview=last_message_preview,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                last_message_at=conv.last_message_at,
            )
        )

    # Calculate has_more
    has_more = (offset + len(conversations)) < total

    return ConversationListResponse(
        conversations=conversation_items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_detail(
    conversation_id: UUID,
    session_token: str,
    include_messages: bool = Query(True, description="Include full message list"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed conversation information

    특정 대화 상세 조회

    **Features:**
    - Full conversation metadata
    - Crisis detection info
    - Optional message list (can be disabled for faster response)
    - Message count

    **Query Parameters:**
    - `include_messages`: Include full message list (default: true)

    **Example:**
    ```
    GET /conversations/{conversation_id}?include_messages=true
    ```

    **Response:**
    ```json
    {
        "id": "uuid",
        "user_id": "uuid",
        "title": "불안감 상담",
        "summary": "학교 생활에서의 불안 증상과 대처 방법...",
        "status": "active",
        "crisis_detected": false,
        "crisis_severity": 0,
        "crisis_keywords_found": null,
        "created_at": "2025-11-01T10:00:00Z",
        "updated_at": "2025-11-05T14:30:00Z",
        "last_message_at": "2025-11-05T14:30:00Z",
        "message_count": 15,
        "messages": [...]
    }
    ```
    """
    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Query conversation
    query = select(Conversation).where(
        Conversation.conversation_id == conversation_id,
        Conversation.user_id == user.user_id,
        Conversation.is_deleted == False
    )

    if include_messages:
        query = query.options(selectinload(Conversation.messages))

    result = await db.execute(query)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Get message count
    msg_count_query = select(func.count()).select_from(Message).where(
        Message.conversation_id == conversation.conversation_id,
        Message.is_deleted == False
    )
    msg_count_result = await db.execute(msg_count_query)
    message_count = msg_count_result.scalar()

    # Build messages list
    messages_list = []
    if include_messages:
        for msg in conversation.messages:
            if not msg.is_deleted:
                messages_list.append(
                    MessageResponse(
                        id=msg.message_id,
                        conversation_id=msg.conversation_id,
                        role=msg.role,
                        content=msg.content,
                        contains_crisis_keywords=msg.contains_crisis_keywords,
                        detected_keywords=msg.detected_keywords,
                        created_at=msg.created_at,
                    )
                )

    return ConversationDetailResponse(
        id=conversation.conversation_id,
        user_id=conversation.user_id,
        title=conversation.title,
        summary=conversation.summary,
        status=conversation.status,
        crisis_detected=conversation.crisis_detected,
        crisis_severity=conversation.crisis_severity,
        crisis_keywords_found=conversation.crisis_keywords_found,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        last_message_at=conversation.last_message_at,
        messages=messages_list,
        message_count=message_count,
    )


@router.get("/{conversation_id}/messages", response_model=MessageListResponse)
async def get_conversation_messages(
    conversation_id: UUID,
    session_token: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Messages per page (max 200)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get paginated messages for a conversation

    대화의 메시지 목록 조회 (페이징)

    **Features:**
    - Pagination support for long conversations
    - Sorted chronologically (oldest first)
    - Crisis keyword highlighting

    **Query Parameters:**
    - `page`: Page number (default: 1)
    - `page_size`: Messages per page (default: 50, max: 200)

    **Example:**
    ```
    GET /conversations/{conversation_id}/messages?page=1&page_size=50
    ```

    **Response:**
    ```json
    {
        "messages": [
            {
                "id": "uuid",
                "conversation_id": "uuid",
                "role": "user",
                "content": "안녕하세요...",
                "contains_crisis_keywords": false,
                "detected_keywords": null,
                "created_at": "2025-11-01T10:00:00Z"
            }
        ],
        "total": 50,
        "page": 1,
        "page_size": 50,
        "has_more": false,
        "conversation_id": "uuid"
    }
    ```
    """
    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Verify conversation ownership
    conv_query = select(Conversation).where(
        Conversation.conversation_id == conversation_id,
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

    # Get total message count
    count_query = select(func.count()).select_from(Message).where(
        Message.conversation_id == conversation_id,
        Message.is_deleted == False
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Query messages with pagination
    offset = (page - 1) * page_size
    msg_query = select(Message).where(
        Message.conversation_id == conversation_id,
        Message.is_deleted == False
    ).order_by(Message.created_at).limit(page_size).offset(offset)

    msg_result = await db.execute(msg_query)
    messages = msg_result.scalars().all()

    # Build response
    messages_list = []
    for msg in messages:
        messages_list.append(
            MessageResponse(
                id=msg.message_id,
                conversation_id=msg.conversation_id,
                role=msg.role,
                content=msg.content,
                contains_crisis_keywords=msg.contains_crisis_keywords,
                detected_keywords=msg.detected_keywords,
                created_at=msg.created_at,
            )
        )

    has_more = (offset + len(messages)) < total

    return MessageListResponse(
        messages=messages_list,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
        conversation_id=conversation_id,
    )


@router.put("/{conversation_id}", response_model=ConversationDetailResponse)
async def update_conversation(
    conversation_id: UUID,
    request: ConversationUpdateRequest,
    session_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Update conversation metadata

    대화 정보 수정

    **Updatable Fields:**
    - `title`: Conversation title
    - `summary`: Conversation summary
    - `status`: Conversation status (active/archived/deleted)

    **Example Request:**
    ```json
    {
        "title": "불안감 관련 상담 (수정됨)",
        "summary": "학교 생활 불안 증상 및 CBT 적용",
        "status": "archived"
    }
    ```

    **Response:**
    Full conversation details with updated fields
    """
    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Get conversation
    query = select(Conversation).where(
        Conversation.conversation_id == conversation_id,
        Conversation.user_id == user.user_id,
        Conversation.is_deleted == False
    )
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Update fields
    if request.title is not None:
        conversation.title = request.title

    if request.summary is not None:
        conversation.summary = request.summary

    if request.status is not None:
        conversation.status = request.status

    conversation.updated_at = datetime.utcnow()

    # Commit changes
    await db.commit()
    await db.refresh(conversation)

    # Get message count
    msg_count_query = select(func.count()).select_from(Message).where(
        Message.conversation_id == conversation.conversation_id,
        Message.is_deleted == False
    )
    msg_count_result = await db.execute(msg_count_query)
    message_count = msg_count_result.scalar()

    return ConversationDetailResponse(
        id=conversation.conversation_id,
        user_id=conversation.user_id,
        title=conversation.title,
        summary=conversation.summary,
        status=conversation.status,
        crisis_detected=conversation.crisis_detected,
        crisis_severity=conversation.crisis_severity,
        crisis_keywords_found=conversation.crisis_keywords_found,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        last_message_at=conversation.last_message_at,
        messages=[],
        message_count=message_count,
    )


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    session_token: str,
    hard_delete: bool = Query(False, description="Permanently delete (true) or soft delete (false)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a conversation

    대화 삭제

    **Delete Types:**
    - Soft delete (default): Marks as deleted, can be recovered
    - Hard delete: Permanently removes from database (use with caution)

    **Query Parameters:**
    - `hard_delete`: Set to true for permanent deletion (default: false)

    **Example:**
    ```
    DELETE /conversations/{conversation_id}?hard_delete=false
    ```

    **Response:**
    ```json
    {
        "success": true,
        "message": "Conversation deleted successfully",
        "conversation_id": "uuid",
        "delete_type": "soft"
    }
    ```
    """
    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Get conversation
    query = select(Conversation).where(
        Conversation.conversation_id == conversation_id,
        Conversation.user_id == user.user_id
    )
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    if hard_delete:
        # Permanent deletion
        await db.delete(conversation)
        delete_type = "hard"
    else:
        # Soft deletion
        conversation.is_deleted = True
        conversation.deleted_at = datetime.utcnow()
        delete_type = "soft"

    await db.commit()

    return {
        "success": True,
        "message": "Conversation deleted successfully",
        "conversation_id": str(conversation_id),
        "delete_type": delete_type,
    }


@router.get("/search/query")
async def search_conversations(
    session_token: str,
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Search conversations by keyword

    키워드로 대화 검색

    **Searches:**
    - Conversation titles
    - Conversation summaries
    - Message content

    **Query Parameters:**
    - `q`: Search keyword (required)
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 20)

    **Example:**
    ```
    GET /conversations/search/query?q=불안&page=1&page_size=20
    ```

    **Response:**
    Same format as conversation list with matching results
    """
    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Build search query
    search_pattern = f"%{q}%"

    query = select(Conversation).where(
        Conversation.user_id == user.user_id,
        Conversation.is_deleted == False,
        or_(
            Conversation.title.ilike(search_pattern),
            Conversation.summary.ilike(search_pattern)
        )
    )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(desc(Conversation.last_message_at)).limit(page_size).offset(offset)

    # Execute
    result = await db.execute(query)
    conversations = result.scalars().all()

    # Build response (similar to list_conversations)
    conversation_items = []
    for conv in conversations:
        # Get message count
        msg_count_query = select(func.count()).select_from(Message).where(
            Message.conversation_id == conv.conversation_id,
            Message.is_deleted == False
        )
        msg_count_result = await db.execute(msg_count_query)
        message_count = msg_count_result.scalar()

        # Get last message preview
        last_msg_query = select(Message).where(
            Message.conversation_id == conv.conversation_id,
            Message.is_deleted == False
        ).order_by(desc(Message.created_at)).limit(1)
        last_msg_result = await db.execute(last_msg_query)
        last_message = last_msg_result.scalar_one_or_none()

        last_message_preview = None
        if last_message:
            last_message_preview = last_message.content[:100]
            if len(last_message.content) > 100:
                last_message_preview += "..."

        conversation_items.append(
            ConversationListItem(
                id=conv.conversation_id,
                title=conv.title,
                summary=conv.summary,
                status=conv.status,
                crisis_detected=conv.crisis_detected,
                crisis_severity=conv.crisis_severity,
                message_count=message_count,
                last_message_preview=last_message_preview,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                last_message_at=conv.last_message_at,
            )
        )

    has_more = (offset + len(conversations)) < total

    return ConversationListResponse(
        conversations=conversation_items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )
