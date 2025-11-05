"""Chat API endpoints with streaming support"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import RedisManager, get_redis
from app.schemas.conversation import ChatRequest, ChatResponse, StreamChunk
from app.services.openai_service import OpenAIService
from app.services.crisis_detection import CrisisDetectionService
from app.services.conversation_service import ConversationService
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
    openai_service = OpenAIService()
    crisis_service = CrisisDetectionService()
    conversation_service = ConversationService(db, openai_service, crisis_service)

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

    # Create user message embedding
    user_embedding = await openai_service.create_embedding(request.message)

    # Add user message
    user_message = await conversation_service.add_message(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
        embedding=user_embedding,
    )

    # Check for crisis
    is_crisis, severity, keywords = crisis_service.detect_crisis(request.message)

    if is_crisis:
        # Log crisis event
        await crisis_service.log_crisis_event(
            user_id=str(user.id),
            conversation_id=str(conversation.id),
            message=request.message,
            severity=severity,
            keywords=keywords,
        )

        # Get crisis response
        crisis_response = crisis_service.get_crisis_response(severity)

        # Add crisis response message
        assistant_message = await conversation_service.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=crisis_response,
        )

        return ChatResponse(
            conversation_id=conversation.id,
            message=assistant_message,
            crisis_detected=True,
            crisis_severity=severity,
        )

    # Get conversation context
    context = await conversation_service.get_conversation_context(conversation.id)

    # Add system prompt
    system_prompt = openai_service._build_system_prompt()
    messages = [{"role": "system", "content": system_prompt}] + context

    # Get AI response (non-streaming)
    response_generator = openai_service.chat_completion(
        messages=messages, redis_manager=redis, stream=False
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
            openai_service = OpenAIService()
            crisis_service = CrisisDetectionService()
            conversation_service = ConversationService(
                db, openai_service, crisis_service
            )

            # Get or create conversation
            if request.conversation_id:
                conversation = await conversation_service.get_conversation(
                    request.conversation_id, user.id
                )
                if not conversation:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Conversation not found",
                    )
            else:
                title = await openai_service.generate_conversation_title(
                    request.message
                )
                conversation = await conversation_service.create_conversation(
                    user_id=user.id, title=title
                )

            # Create user message embedding
            user_embedding = await openai_service.create_embedding(request.message)

            # Add user message
            user_message = await conversation_service.add_message(
                conversation_id=conversation.id,
                role="user",
                content=request.message,
                embedding=user_embedding,
            )

            # Check for crisis
            is_crisis, severity, keywords = crisis_service.detect_crisis(
                request.message
            )

            if is_crisis:
                # Log crisis event
                await crisis_service.log_crisis_event(
                    user_id=str(user.id),
                    conversation_id=str(conversation.id),
                    message=request.message,
                    severity=severity,
                    keywords=keywords,
                )

                # Send crisis response
                crisis_response = crisis_service.get_crisis_response(severity)

                # Stream crisis response character by character
                for char in crisis_response:
                    chunk = StreamChunk(
                        content=char,
                        conversation_id=conversation.id,
                        crisis_detected=True,
                    )
                    yield f"data: {chunk.model_dump_json()}\n\n"

                # Add crisis response to database
                await conversation_service.add_message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=crisis_response,
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

            # Get conversation context
            context = await conversation_service.get_conversation_context(
                conversation.id
            )

            # Add system prompt
            system_prompt = openai_service._build_system_prompt()
            messages = [{"role": "system", "content": system_prompt}] + context

            # Stream AI response
            complete_response = ""
            async for chunk in openai_service.chat_completion(
                messages=messages, redis_manager=redis, stream=True
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
