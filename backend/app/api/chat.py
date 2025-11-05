"""Chat API endpoints with advanced crisis detection"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import RedisManager, get_redis
from app.schemas.conversation import ChatRequest, ChatResponse, StreamChunk
from app.services.openai_service import OpenAIService
from app.services.crisis_detector import crisis_detection_system, RiskLevel
from app.services.conversation_service import ConversationService
from app.services.cache_service import CacheService
from app.services.cbt_stage_service import CBTStageService
from app.models.user import User
import json

router = APIRouter(prefix="/chat", tags=["chat"])


async def get_current_user(
    session_token: str, db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from session token"""
    from sqlalchemy import select

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


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    session_token: str,
    db: AsyncSession = Depends(get_db),
    redis: RedisManager = Depends(get_redis),
):
    """
    Send a message and get AI response (non-streaming).

    Args:
        request: Chat request with message and optional conversation_id
        session_token: User session token
        db: Database session
        redis: Redis manager

    Returns:
        Chat response with AI message
    """
    # Get user
    user = await get_current_user(session_token, db)

    # Initialize services
    cache_service = CacheService(redis)
    openai_service = OpenAIService(cache_service=cache_service)
    conversation_service = ConversationService(db, openai_service)
    cbt_service = CBTStageService(db=db, openai_client=openai_service.client)

    # Rate limiting check (10 requests per minute)
    rate_limit_key = f"user:{user.id}"
    is_allowed, rate_info = await cache_service.rate_limit_per_minute(
        rate_limit_key, max_requests=10
    )

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Rate limit exceeded. Please try again later.",
                "requests_remaining": rate_info["requests_remaining"],
                "reset_time": rate_info["reset_time"],
            },
        )

    # Get or create conversation
    if request.conversation_id:
        conversation = await conversation_service.get_conversation(
            request.conversation_id, user.id
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )
    else:
        # Generate title from first message
        title = await openai_service.generate_conversation_title(request.message)
        conversation = await conversation_service.create_conversation(
            user_id=user.id, title=title
        )

        # Initialize CBT stage for new conversation
        await cbt_service.initialize_stage(str(conversation.id))

    # Create user message embedding
    user_embedding = await openai_service.create_embedding(request.message)

    # Add user message
    user_message = await conversation_service.add_message(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
        embedding=user_embedding,
    )

    # Get conversation context for crisis detection
    context = await conversation_service.get_conversation_context(conversation.id)

    # Advanced 3-stage crisis detection
    assessment = await crisis_detection_system.detect(
        message=request.message,
        conversation_history=context
    )

    # Handle crisis detection
    if assessment["risk_level"] in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
        # Log crisis event to database
        await crisis_detection_system.emergency_protocol(
            assessment=assessment,
            user_id=str(user.id),
            conversation_id=str(conversation.id)
        )

        # Get appropriate crisis response message
        crisis_response = crisis_detection_system.get_crisis_response_message(assessment)

        # Add crisis response message with detected keywords
        assistant_message = await conversation_service.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=crisis_response,
            crisis_keywords=assessment.get("detected_keywords", []),
        )

        return ChatResponse(
            conversation_id=conversation.id,
            message=assistant_message,
            crisis_detected=True,
            crisis_severity=assessment["risk_level"].value,
        )

    # Get AI response with CBT-aware dynamic prompting (non-streaming)
    response_generator = openai_service.chat_completion_with_cbt(
        messages=context,
        conversation_id=str(conversation.id),
        cbt_service=cbt_service,
        redis_manager=redis,
        stream=False,
        user_id=str(user.id)
    )

    # Get complete response
    complete_response = ""
    async for chunk in response_generator:
        complete_response = chunk

    # Add assistant message
    assistant_message = await conversation_service.add_message(
        conversation_id=conversation.id,
        role="assistant",
        content=complete_response,
    )

    return ChatResponse(
        conversation_id=conversation.id,
        message=assistant_message,
        crisis_detected=False,
        crisis_severity=0,
    )


@router.post("/stream")
async def stream_message(
    request: ChatRequest,
    session_token: str,
    db: AsyncSession = Depends(get_db),
    redis: RedisManager = Depends(get_redis),
):
    """
    Send a message and get streaming AI response (SSE).

    Args:
        request: Chat request with message and optional conversation_id
        session_token: User session token
        db: Database session
        redis: Redis manager

    Returns:
        Server-Sent Events stream
    """

    async def generate():
        try:
            # Get user
            user = await get_current_user(session_token, db)

            # Initialize services
            cache_service = CacheService(redis)
            openai_service = OpenAIService(cache_service=cache_service)
            conversation_service = ConversationService(db, openai_service)
            cbt_service = CBTStageService(db=db, openai_client=openai_service.client)

            # Rate limiting check (10 requests per minute)
            rate_limit_key = f"user:{user.id}"
            is_allowed, rate_info = await cache_service.rate_limit_per_minute(
                rate_limit_key, max_requests=10
            )

            if not is_allowed:
                error_chunk = StreamChunk(
                    content=f"Rate limit exceeded. Please try again in {rate_info['reset_time']} seconds.",
                    done=True
                )
                yield f"data: {error_chunk.model_dump_json()}\n\n"
                return

            # Get or create conversation
            if request.conversation_id:
                conversation = await conversation_service.get_conversation(
                    request.conversation_id, user.id
                )
                if not conversation:
                    error_chunk = StreamChunk(
                        content="Conversation not found",
                        done=True
                    )
                    yield f"data: {error_chunk.model_dump_json()}\n\n"
                    return
            else:
                title = await openai_service.generate_conversation_title(
                    request.message
                )
                conversation = await conversation_service.create_conversation(
                    user_id=user.id, title=title
                )

                # Initialize CBT stage for new conversation
                await cbt_service.initialize_stage(str(conversation.id))

            # Create user message embedding
            user_embedding = await openai_service.create_embedding(request.message)

            # Add user message
            user_message = await conversation_service.add_message(
                conversation_id=conversation.id,
                role="user",
                content=request.message,
                embedding=user_embedding,
            )

            # Get conversation context for crisis detection
            context = await conversation_service.get_conversation_context(
                conversation.id
            )

            # Advanced 3-stage crisis detection
            assessment = await crisis_detection_system.detect(
                message=request.message,
                conversation_history=context
            )

            # Handle crisis detection
            if assessment["risk_level"] in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                # Log crisis event to database
                await crisis_detection_system.emergency_protocol(
                    assessment=assessment,
                    user_id=str(user.id),
                    conversation_id=str(conversation.id)
                )

                # Get appropriate crisis response message
                crisis_response = crisis_detection_system.get_crisis_response_message(assessment)

                # Stream crisis response character by character
                for char in crisis_response:
                    chunk = StreamChunk(
                        content=char,
                        conversation_id=conversation.id,
                        crisis_detected=True,
                    )
                    yield f"data: {chunk.model_dump_json()}\n\n"

                # Add crisis response to database with detected keywords
                await conversation_service.add_message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=crisis_response,
                    crisis_keywords=assessment.get("detected_keywords", []),
                )

                # Send done signal
                done_chunk = StreamChunk(
                    content="",
                    done=True,
                    conversation_id=conversation.id,
                    crisis_detected=True,
                )
                yield f"data: {done_chunk.model_dump_json()}\n\n"
                return

            # Stream AI response with CBT-aware dynamic prompting
            complete_response = ""
            async for chunk in openai_service.chat_completion_with_cbt(
                messages=context,
                conversation_id=str(conversation.id),
                cbt_service=cbt_service,
                redis_manager=redis,
                stream=True,
                user_id=str(user.id)
            ):
                complete_response += chunk
                stream_chunk = StreamChunk(
                    content=chunk,
                    conversation_id=conversation.id,
                    crisis_detected=False,
                )
                yield f"data: {stream_chunk.model_dump_json()}\n\n"

            # Add complete assistant message to database
            await conversation_service.add_message(
                conversation_id=conversation.id,
                role="assistant",
                content=complete_response,
            )

            # Send done signal
            done_chunk = StreamChunk(
                content="",
                done=True,
                conversation_id=conversation.id,
                crisis_detected=False,
            )
            yield f"data: {done_chunk.model_dump_json()}\n\n"

        except Exception as e:
            error_chunk = StreamChunk(content=f"Error: {str(e)}", done=True)
            yield f"data: {error_chunk.model_dump_json()}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
