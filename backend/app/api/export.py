"""
Data Export API Endpoints
데이터 내보내기 API

Provides endpoints for exporting user data:
- Export conversations (PDF/JSON)
- Generate progress reports
- Export all data (GDPR compliance)
"""

import json
import io
from typing import Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.crisis_log import CrisisLog
from app.models.session import Session
from app.schemas.export import (
    ConversationExportRequest,
    ProgressReportRequest,
    AllDataExportRequest,
    ExportResponse,
)


router = APIRouter(prefix="/export", tags=["export"])


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


def generate_conversation_json(conversation: Conversation, messages: list, metadata: dict) -> dict:
    """Generate JSON export of conversation"""
    return {
        "export_info": {
            "export_date": datetime.utcnow().isoformat(),
            "export_type": "conversation",
            "format_version": "1.0"
        },
        "conversation": {
            "id": str(conversation.conversation_id),
            "title": conversation.title,
            "summary": conversation.summary,
            "status": conversation.status,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "last_message_at": conversation.last_message_at.isoformat(),
        },
        "metadata": metadata,
        "messages": [
            {
                "id": str(msg.message_id),
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "contains_crisis_keywords": msg.contains_crisis_keywords,
                "detected_keywords": msg.detected_keywords,
            }
            for msg in messages
        ],
        "statistics": {
            "total_messages": len(messages),
            "user_messages": sum(1 for msg in messages if msg.role == "user"),
            "assistant_messages": sum(1 for msg in messages if msg.role == "assistant"),
            "crisis_messages": sum(1 for msg in messages if msg.contains_crisis_keywords),
        }
    }


def generate_conversation_pdf_placeholder(data: dict) -> bytes:
    """
    Generate PDF export of conversation

    TODO: Implement PDF generation using reportlab or weasyprint

    Required dependencies:
    - pip install reportlab
    OR
    - pip install weasyprint

    Implementation outline:
    1. Create PDF document
    2. Add header with conversation title and date
    3. Format messages with proper styling
    4. Add metadata section
    5. Include statistics
    6. Return PDF bytes
    """
    # Placeholder: Return JSON as text for now
    # In production, this should generate actual PDF
    pdf_content = f"""
    CONVERSATION EXPORT (PDF)
    =========================

    Title: {data['conversation']['title']}
    Date: {data['export_info']['export_date']}

    Messages: {data['statistics']['total_messages']}

    [PDF generation requires reportlab or weasyprint library]

    For now, please use JSON format for full export.
    """
    return pdf_content.encode('utf-8')


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/conversations/{conversation_id}")
async def export_conversation(
    conversation_id: UUID,
    request: ConversationExportRequest,
    session_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Export a conversation

    대화 내보내기 (PDF 또는 JSON)

    **Features:**
    - Export in PDF or JSON format
    - Include/exclude metadata
    - Include/exclude system messages
    - Direct download

    **Request Body:**
    ```json
    {
        "format": "pdf",
        "include_metadata": true,
        "include_system_messages": false
    }
    ```

    **Response:**
    Direct file download (PDF or JSON)

    **Formats:**
    - **JSON**: Complete structured data export
    - **PDF**: Formatted, readable document (requires reportlab/weasyprint)
    """
    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Get conversation
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

    # Get messages
    msg_query = select(Message).where(
        Message.conversation_id == conversation_id,
        Message.is_deleted == False
    ).order_by(Message.created_at)

    if not request.include_system_messages:
        msg_query = msg_query.where(Message.role != "system")

    msg_result = await db.execute(msg_query)
    messages = msg_result.scalars().all()

    # Build metadata
    metadata = {}
    if request.include_metadata:
        metadata = {
            "crisis_detected": conversation.crisis_detected,
            "crisis_severity": conversation.crisis_severity,
            "crisis_keywords_found": conversation.crisis_keywords_found,
            "crisis_timestamp": conversation.crisis_timestamp.isoformat() if conversation.crisis_timestamp else None,
        }

    # Generate export data
    export_data = generate_conversation_json(conversation, messages, metadata)

    # Return based on format
    if request.format == "json":
        # Return JSON file
        json_content = json.dumps(export_data, ensure_ascii=False, indent=2)

        return StreamingResponse(
            io.BytesIO(json_content.encode('utf-8')),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="conversation_{conversation_id}.json"'
            }
        )
    else:  # PDF
        # Generate PDF (placeholder for now)
        pdf_content = generate_conversation_pdf_placeholder(export_data)

        return StreamingResponse(
            io.BytesIO(pdf_content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="conversation_{conversation_id}.pdf"'
            }
        )


@router.post("/progress-report")
async def export_progress_report(
    request: ProgressReportRequest,
    session_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate progress report

    진행 보고서 생성

    **Features:**
    - User statistics and progress
    - Crisis history
    - Emotion timeline (if available)
    - Date range filtering
    - PDF or JSON format

    **Request Body:**
    ```json
    {
        "format": "pdf",
        "include_statistics": true,
        "include_crisis_history": true,
        "include_emotion_timeline": true,
        "date_from": "2025-11-01T00:00:00Z",
        "date_to": "2025-11-06T23:59:59Z"
    }
    ```

    **Response:**
    Direct file download with progress report
    """
    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Set date range
    date_from = request.date_from or (datetime.utcnow() - timedelta(days=30))
    date_to = request.date_to or datetime.utcnow()

    # Build report data
    report_data = {
        "report_info": {
            "generated_at": datetime.utcnow().isoformat(),
            "report_type": "progress_report",
            "date_range": {
                "from": date_from.isoformat(),
                "to": date_to.isoformat()
            },
            "format_version": "1.0"
        },
        "user_info": {
            "user_id": str(user.user_id),
            "created_at": user.created_at.isoformat(),
            "last_active": user.last_active.isoformat(),
        }
    }

    # Add statistics if requested
    if request.include_statistics:
        from sqlalchemy import func

        # Get conversation count
        conv_count_query = select(func.count()).select_from(Conversation).where(
            Conversation.user_id == user.user_id,
            Conversation.created_at >= date_from,
            Conversation.created_at <= date_to,
            Conversation.is_deleted == False
        )
        conv_count_result = await db.execute(conv_count_query)
        conversation_count = conv_count_result.scalar()

        # Get message count
        msg_count_query = select(func.count()).select_from(Message).join(
            Conversation, Message.conversation_id == Conversation.conversation_id
        ).where(
            Conversation.user_id == user.user_id,
            Message.created_at >= date_from,
            Message.created_at <= date_to,
            Message.is_deleted == False
        )
        msg_count_result = await db.execute(msg_count_query)
        message_count = msg_count_result.scalar()

        # Get session count
        session_count_query = select(func.count()).select_from(Session).where(
            Session.user_id == user.user_id,
            Session.started_at >= date_from,
            Session.started_at <= date_to,
            Session.is_deleted == False
        )
        session_count_result = await db.execute(session_count_query)
        session_count = session_count_result.scalar()

        report_data["statistics"] = {
            "conversations": conversation_count,
            "messages": message_count,
            "sessions": session_count,
        }

    # Add crisis history if requested
    if request.include_crisis_history:
        crisis_query = select(CrisisLog).where(
            CrisisLog.user_id == user.user_id,
            CrisisLog.detected_at >= date_from,
            CrisisLog.detected_at <= date_to
        ).order_by(CrisisLog.detected_at)

        crisis_result = await db.execute(crisis_query)
        crisis_logs = crisis_result.scalars().all()

        report_data["crisis_history"] = [
            {
                "id": str(log.crisis_log_id),
                "detected_at": log.detected_at.isoformat(),
                "risk_level": log.risk_level,
                "detected_keywords": log.detected_keywords,
            }
            for log in crisis_logs
        ]

    # Add emotion timeline placeholder
    if request.include_emotion_timeline:
        report_data["emotion_timeline"] = {
            "note": "Emotion tracking feature coming soon",
            "implementation": "Requires emotion data storage in message metadata"
        }

    # Return based on format
    if request.format == "json":
        json_content = json.dumps(report_data, ensure_ascii=False, indent=2)

        return StreamingResponse(
            io.BytesIO(json_content.encode('utf-8')),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="progress_report_{user.user_id}.json"'
            }
        )
    else:  # PDF
        # Placeholder PDF generation
        pdf_content = f"""
        PROGRESS REPORT
        ===============

        Generated: {report_data['report_info']['generated_at']}
        Date Range: {date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}

        [PDF generation requires reportlab or weasyprint library]

        For now, please use JSON format for full export.
        """.encode('utf-8')

        return StreamingResponse(
            io.BytesIO(pdf_content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="progress_report_{user.user_id}.pdf"'
            }
        )


@router.post("/all-data")
async def export_all_data(
    request: AllDataExportRequest,
    session_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Export all user data (GDPR compliance)

    전체 데이터 내보내기 (GDPR 준수)

    **Features:**
    - Complete data export
    - GDPR right to data portability
    - Includes all conversations, messages, sessions
    - Optional: include soft-deleted data
    - JSON or ZIP format

    **Request Body:**
    ```json
    {
        "format": "json",
        "include_deleted": false
    }
    ```

    **Response:**
    Complete data archive download

    **Data Included:**
    - User profile
    - All conversations
    - All messages
    - All sessions
    - Crisis logs
    - User statistics
    """
    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Build complete data export
    export_data = {
        "export_info": {
            "exported_at": datetime.utcnow().isoformat(),
            "export_type": "complete_data_export",
            "user_id": str(user.user_id),
            "format_version": "1.0",
            "gdpr_compliant": True
        },
        "user_profile": {
            "user_id": str(user.user_id),
            "email": user.email_encrypted,
            "is_anonymous": user.is_anonymous,
            "consent_given": user.consent_given,
            "consent_timestamp": user.consent_timestamp.isoformat() if user.consent_timestamp else None,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
            "last_active": user.last_active.isoformat(),
            "metadata": user.metadata,
        }
    }

    # Get all conversations
    conv_query = select(Conversation).where(
        Conversation.user_id == user.user_id
    )
    if not request.include_deleted:
        conv_query = conv_query.where(Conversation.is_deleted == False)

    conv_result = await db.execute(conv_query)
    conversations = conv_result.scalars().all()

    export_data["conversations"] = []
    for conv in conversations:
        # Get messages for this conversation
        msg_query = select(Message).where(
            Message.conversation_id == conv.conversation_id
        )
        if not request.include_deleted:
            msg_query = msg_query.where(Message.is_deleted == False)

        msg_result = await db.execute(msg_query)
        messages = msg_result.scalars().all()

        export_data["conversations"].append({
            "id": str(conv.conversation_id),
            "title": conv.title,
            "summary": conv.summary,
            "status": conv.status,
            "crisis_detected": conv.crisis_detected,
            "crisis_severity": conv.crisis_severity,
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.updated_at.isoformat(),
            "is_deleted": conv.is_deleted,
            "messages": [
                {
                    "id": str(msg.message_id),
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                    "contains_crisis_keywords": msg.contains_crisis_keywords,
                    "detected_keywords": msg.detected_keywords,
                }
                for msg in messages
            ]
        })

    # Get all sessions
    session_query = select(Session).where(
        Session.user_id == user.user_id
    )
    if not request.include_deleted:
        session_query = session_query.where(Session.is_deleted == False)

    session_result = await db.execute(session_query)
    sessions = session_result.scalars().all()

    export_data["sessions"] = [
        {
            "id": str(sess.session_id),
            "conversation_id": str(sess.conversation_id),
            "started_at": sess.started_at.isoformat(),
            "ended_at": sess.ended_at.isoformat() if sess.ended_at else None,
            "duration_minutes": sess.duration_minutes,
            "summary": sess.summary,
            "notes": sess.notes,
            "message_count": sess.message_count,
            "crisis_level": sess.crisis_level,
        }
        for sess in sessions
    ]

    # Get crisis logs
    crisis_query = select(CrisisLog).where(
        CrisisLog.user_id == user.user_id
    )
    crisis_result = await db.execute(crisis_query)
    crisis_logs = crisis_result.scalars().all()

    export_data["crisis_logs"] = [
        {
            "id": str(log.crisis_log_id),
            "detected_at": log.detected_at.isoformat(),
            "risk_level": log.risk_level,
            "detected_keywords": log.detected_keywords,
            "conversation_id": str(log.conversation_id) if log.conversation_id else None,
        }
        for log in crisis_logs
    ]

    # Statistics
    export_data["statistics"] = {
        "total_conversations": len(export_data["conversations"]),
        "total_messages": sum(len(conv["messages"]) for conv in export_data["conversations"]),
        "total_sessions": len(export_data["sessions"]),
        "total_crisis_events": len(export_data["crisis_logs"]),
    }

    # Return as JSON
    if request.format == "json":
        json_content = json.dumps(export_data, ensure_ascii=False, indent=2)

        return StreamingResponse(
            io.BytesIO(json_content.encode('utf-8')),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="user_data_export_{user.user_id}.json"'
            }
        )
    else:  # ZIP
        # TODO: Implement ZIP export with multiple files
        # Would include separate JSON files for each data type
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="ZIP format not yet implemented. Please use JSON format."
        )
