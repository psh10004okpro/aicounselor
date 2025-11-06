"""
User Profile Management API Endpoints
사용자 프로필 관리 API

Provides endpoints for managing user profiles and statistics:
- Get user profile
- Update user profile
- Get user statistics
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.crisis_log import CrisisLog
from app.schemas.user import (
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserStatisticsResponse,
)


router = APIRouter(prefix="/users", tags=["users"])


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

@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    session_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get current user's profile

    내 프로필 조회

    **Returns:**
    - User ID
    - Email (if not anonymous)
    - Anonymous status
    - Consent information
    - Timestamps
    - Metadata (age, display_name, preferences)

    **Example Response:**
    ```json
    {
        "id": "uuid",
        "email": "user@example.com",
        "is_anonymous": false,
        "consent_given": true,
        "consent_timestamp": "2025-11-01T10:00:00Z",
        "created_at": "2025-11-01T10:00:00Z",
        "updated_at": "2025-11-05T14:30:00Z",
        "last_active": "2025-11-06T09:15:00Z",
        "age": 25,
        "display_name": "김철수",
        "preferences": {
            "theme": "light",
            "notifications_enabled": true
        }
    }
    ```
    """
    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Extract metadata fields
    metadata = user.metadata or {}
    age = metadata.get("age")
    display_name = metadata.get("display_name")
    preferences = metadata.get("preferences")

    return UserProfileResponse(
        id=user.user_id,
        email=user.email_encrypted,  # TODO: Decrypt if needed
        is_anonymous=user.is_anonymous,
        consent_given=user.consent_given,
        consent_timestamp=user.consent_timestamp,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_active=user.last_active,
        age=age,
        display_name=display_name,
        preferences=preferences,
    )


@router.put("/me", response_model=UserProfileResponse)
async def update_my_profile(
    request: UserProfileUpdateRequest,
    session_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user's profile

    내 프로필 수정

    **Updatable Fields:**
    - `age`: User age (13-120)
    - `display_name`: Display name (max 100 chars)
    - `preferences`: User preferences dictionary

    **Example Request:**
    ```json
    {
        "age": 26,
        "display_name": "김철수",
        "preferences": {
            "theme": "dark",
            "notifications_enabled": true,
            "language": "ko"
        }
    }
    ```

    **Example Response:**
    Updated profile with new values
    """
    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Get current metadata
    metadata = user.metadata or {}

    # Update metadata fields
    if request.age is not None:
        metadata["age"] = request.age

    if request.display_name is not None:
        metadata["display_name"] = request.display_name

    if request.preferences is not None:
        # Merge with existing preferences
        existing_prefs = metadata.get("preferences", {})
        existing_prefs.update(request.preferences)
        metadata["preferences"] = existing_prefs

    # Update user
    user.metadata = metadata
    user.updated_at = datetime.utcnow()
    user.last_active = datetime.utcnow()

    # Commit changes
    await db.commit()
    await db.refresh(user)

    # Extract updated metadata
    age = metadata.get("age")
    display_name = metadata.get("display_name")
    preferences = metadata.get("preferences")

    return UserProfileResponse(
        id=user.user_id,
        email=user.email_encrypted,
        is_anonymous=user.is_anonymous,
        consent_given=user.consent_given,
        consent_timestamp=user.consent_timestamp,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_active=user.last_active,
        age=age,
        display_name=display_name,
        preferences=preferences,
    )


@router.get("/me/statistics", response_model=UserStatisticsResponse)
async def get_my_statistics(
    session_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get current user's usage statistics

    내 사용 통계 조회

    **Provides:**
    - Total conversations count
    - Total messages count
    - Total sessions count
    - Crisis events count
    - Average crisis level
    - First and last session dates
    - Most common emotion
    - Current CBT stage
    - Days active
    - Emotion distribution
    - Crisis level trend

    **Example Response:**
    ```json
    {
        "user_id": "uuid",
        "total_conversations": 5,
        "total_messages": 127,
        "total_sessions": 8,
        "crisis_events_count": 2,
        "average_crisis_level": 1.2,
        "first_session_date": "2025-11-01T10:00:00Z",
        "last_session_date": "2025-11-06T09:15:00Z",
        "most_common_emotion": "anxiety",
        "current_cbt_stage": "skills_acquisition",
        "days_active": 6,
        "emotion_distribution": {
            "anxiety": 35,
            "depression": 20,
            "neutral": 45
        },
        "crisis_level_trend": [
            {"date": "2025-11-01", "level": 2},
            {"date": "2025-11-02", "level": 1}
        ]
    }
    ```
    """
    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Get total conversations
    conv_count_query = select(func.count()).select_from(Conversation).where(
        Conversation.user_id == user.user_id,
        Conversation.is_deleted == False
    )
    conv_count_result = await db.execute(conv_count_query)
    total_conversations = conv_count_result.scalar()

    # Get total messages
    msg_count_query = select(func.count()).select_from(Message).join(
        Conversation, Message.conversation_id == Conversation.conversation_id
    ).where(
        Conversation.user_id == user.user_id,
        Message.is_deleted == False
    )
    msg_count_result = await db.execute(msg_count_query)
    total_messages = msg_count_result.scalar()

    # Get crisis events count
    crisis_count_query = select(func.count()).select_from(CrisisLog).where(
        CrisisLog.user_id == user.user_id
    )
    crisis_count_result = await db.execute(crisis_count_query)
    crisis_events_count = crisis_count_result.scalar()

    # Get average crisis level
    avg_crisis_query = select(func.avg(Conversation.crisis_severity)).where(
        Conversation.user_id == user.user_id,
        Conversation.is_deleted == False
    )
    avg_crisis_result = await db.execute(avg_crisis_query)
    average_crisis_level = avg_crisis_result.scalar() or 0.0

    # Get first and last session dates
    first_conv_query = select(Conversation.created_at).where(
        Conversation.user_id == user.user_id,
        Conversation.is_deleted == False
    ).order_by(Conversation.created_at).limit(1)
    first_conv_result = await db.execute(first_conv_query)
    first_session_date = first_conv_result.scalar_one_or_none()

    last_conv_query = select(Conversation.last_message_at).where(
        Conversation.user_id == user.user_id,
        Conversation.is_deleted == False
    ).order_by(Conversation.last_message_at.desc()).limit(1)
    last_conv_result = await db.execute(last_conv_query)
    last_session_date = last_conv_result.scalar_one_or_none()

    # Calculate days active
    days_active = 0
    if first_session_date:
        days_active = (datetime.utcnow() - first_session_date).days + 1

    # Get crisis level trend (last 7 days)
    crisis_trend = []
    if crisis_events_count > 0:
        trend_query = select(
            func.date_trunc('day', CrisisLog.detected_at).label('date'),
            func.max(CrisisLog.risk_level).label('level')
        ).where(
            CrisisLog.user_id == user.user_id,
            CrisisLog.detected_at >= datetime.utcnow() - timedelta(days=7)
        ).group_by(
            func.date_trunc('day', CrisisLog.detected_at)
        ).order_by(
            func.date_trunc('day', CrisisLog.detected_at)
        )
        trend_result = await db.execute(trend_query)
        trend_rows = trend_result.all()

        for row in trend_rows:
            crisis_trend.append({
                "date": row.date.strftime("%Y-%m-%d"),
                "level": row.level
            })

    # TODO: Implement emotion distribution and most common emotion
    # This would require storing emotion data in a separate table or message metadata
    emotion_distribution = None
    most_common_emotion = None

    # TODO: Get current CBT stage
    # This would require querying the CBT stage tracking system
    current_cbt_stage = None

    # Total sessions = total conversations (for now)
    total_sessions = total_conversations

    return UserStatisticsResponse(
        user_id=user.user_id,
        total_conversations=total_conversations,
        total_messages=total_messages,
        total_sessions=total_sessions,
        crisis_events_count=crisis_events_count,
        average_crisis_level=float(average_crisis_level),
        first_session_date=first_session_date,
        last_session_date=last_session_date,
        most_common_emotion=most_common_emotion,
        current_cbt_stage=current_cbt_stage,
        days_active=days_active,
        emotion_distribution=emotion_distribution,
        crisis_level_trend=crisis_trend,
    )


@router.delete("/me")
async def delete_my_account(
    session_token: str,
    confirm: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete current user account

    내 계정 삭제

    **IMPORTANT:**
    This is a permanent action. All user data will be marked as deleted.

    **Query Parameters:**
    - `confirm`: Must be set to true to confirm deletion

    **Example:**
    ```
    DELETE /users/me?confirm=true
    ```

    **Response:**
    ```json
    {
        "success": true,
        "message": "Account deleted successfully",
        "user_id": "uuid"
    }
    ```
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must set confirm=true to delete account"
        )

    # Get authenticated user
    user = await get_current_user(session_token, db)

    # Soft delete user
    user.is_deleted = True
    user.deleted_at = datetime.utcnow()

    # Soft delete all conversations
    conversations_query = select(Conversation).where(
        Conversation.user_id == user.user_id
    )
    conversations_result = await db.execute(conversations_query)
    conversations = conversations_result.scalars().all()

    for conv in conversations:
        conv.is_deleted = True
        conv.deleted_at = datetime.utcnow()

    await db.commit()

    return {
        "success": True,
        "message": "Account deleted successfully",
        "user_id": str(user.user_id),
    }
