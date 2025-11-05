"""Chat API endpoints with advanced crisis detection"""

from typing import Optional, List, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.redis import RedisManager, get_redis
from app.schemas.conversation import ChatRequest, ChatResponse, StreamChunk
from app.services.openai_service import OpenAIService
from app.services.crisis_detector import crisis_detection_system, RiskLevel
from app.services.conversation_service import ConversationService
from app.services.cache_service import CacheService
from app.services.cbt_stage_service import CBTStageService
from app.services.realtime_analyzer import RealtimeMessageAnalyzer, EnhancedPromptSelector
from app.services.alert_system import CrisisAlertSystem
from app.services.age_based_counseling import AgeCounselingService
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


# ============================================================================
# Integrated Chat System (All Systems Combined)
# ============================================================================

class IntegratedChatRequest(BaseModel):
    """Request for integrated chat endpoint"""
    user_id: str = Field(..., description="User ID")
    message: str = Field(..., description="User message")
    conversation_history: Optional[List[Dict]] = Field(
        None, description="Recent conversation history (last 10 messages)"
    )
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")


class IntegratedChatResponse(BaseModel):
    """Response from integrated chat endpoint"""
    response: str = Field(..., description="Assistant response")
    alert: Optional[Dict] = Field(None, description="Crisis alert if detected")
    emotion_detected: Dict = Field(..., description="Detected emotions")
    crisis_level: int = Field(..., description="Crisis level (0-4)")
    prompt_used: str = Field(..., description="Prompt key that was selected")
    analysis: Dict = Field(..., description="Full GPT-4 analysis")
    conversation_id: str = Field(..., description="Conversation ID")


@router.post("/api/chat", response_model=IntegratedChatResponse)
async def integrated_chat_endpoint(
    request: IntegratedChatRequest,
    session_token: str,
    db: AsyncSession = Depends(get_db),
    redis: RedisManager = Depends(get_redis),
):
    """
    🎯 **Integrated Chat Endpoint - All Systems Combined**

    통합 상담 API 엔드포인트 - 모든 시스템 통합

    This endpoint integrates ALL counseling systems:
    1. ✅ User profile loading (age, session count)
    2. ✅ Long-term memory retrieval (vector search top-k=5)
    3. ✅ GPT-4 powered realtime analysis (emotions, crisis)
    4. ✅ Dynamic prompt selection (crisis/age/stage/emotion)
    5. ✅ OpenAI GPT-4 response generation
    6. ✅ Message embedding and storage
    7. ✅ Crisis alert generation (Level 2+)
    8. ✅ CBT stage tracking
    9. ✅ Age-based counseling differentiation

    **Flow:**
    ```
    User Message
         ↓
    1. Load Profile (age, sessions)
         ↓
    2. Search Memory (vector top-5)
         ↓
    3. GPT-4 Analysis (emotion/crisis)
         ↓
    4. Select Prompt (crisis/age/stage/emotion)
         ↓
    5. Generate Response (GPT-4)
         ↓
    6. Save to Memory (embedding)
         ↓
    7. Check Alert (if crisis >= 2)
         ↓
    Return Response + Alert + Analysis
    ```

    **Example Request:**
    ```json
    {
        "user_id": "user123",
        "message": "요즘 너무 힘들어서 아무것도 하기 싫어요",
        "conversation_history": [
            {"role": "user", "content": "안녕하세요"},
            {"role": "assistant", "content": "안녕하세요, 무엇을 도와드릴까요?"}
        ]
    }
    ```

    **Example Response:**
    ```json
    {
        "response": "힘든 시기를 보내고 계시는군요. 얼마나 힘드신지 이야기해 주실 수 있나요?",
        "alert": null,
        "emotion_detected": {
            "primary": "depression",
            "secondary": ["fatigue"],
            "intensity": 0.7
        },
        "crisis_level": 2,
        "prompt_used": "adult_assessment_depression",
        "analysis": {...},
        "conversation_id": "conv_123"
    }
    ```
    """
    try:
        # Get authenticated user
        user = await get_current_user(session_token, db)

        # Verify user_id matches (security)
        if str(user.id) != request.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User ID mismatch"
            )

        # Initialize services
        cache_service = CacheService(redis)
        openai_service = OpenAIService(cache_service=cache_service)
        conversation_service = ConversationService(db, openai_service)
        cbt_service = CBTStageService(db=db, openai_client=openai_service.client)
        alert_system = CrisisAlertSystem()
        age_service = AgeCounselingService(db=db)

        # Initialize analyzers
        message_analyzer = RealtimeMessageAnalyzer(openai_client=openai_service.client)
        prompt_selector = EnhancedPromptSelector(
            message_analyzer=message_analyzer,
            prompt_library={}  # Will use built-in library
        )

        # Rate limiting check
        rate_limit_key = f"user:{user.id}"
        is_allowed, rate_info = await cache_service.rate_limit_per_minute(
            rate_limit_key, max_requests=10
        )

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "Rate limit exceeded",
                    "reset_time": rate_info["reset_time"]
                }
            )

        # ====================================================================
        # STEP 1: Load User Profile
        # ====================================================================
        user_profile = {
            "age": user.age if hasattr(user, 'age') and user.age else 25,  # Default adult
            "user_id": str(user.id),
            "session_count": 1  # TODO: Track actual session count
        }

        # ====================================================================
        # STEP 2: Get or Create Conversation
        # ====================================================================
        if request.conversation_id:
            conversation = await conversation_service.get_conversation(
                UUID(request.conversation_id), user.id
            )
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found"
                )
        else:
            # Create new conversation
            title = await openai_service.generate_conversation_title(request.message)
            conversation = await conversation_service.create_conversation(
                user_id=user.id, title=title
            )
            # Initialize CBT stage
            await cbt_service.initialize_stage(str(conversation.id))

        # ====================================================================
        # STEP 3: Retrieve Memory Context (Vector Search Top-K=5)
        # ====================================================================
        memory_context = ""
        try:
            # Get conversation history with embeddings
            context_messages = await conversation_service.get_conversation_context(
                conversation.id, limit=20
            )

            # Search for semantically similar past messages (top-k=5)
            similar_messages = await conversation_service.search_similar_messages(
                conversation_id=conversation.id,
                query_text=request.message,
                top_k=5,
                threshold=0.7
            )

            if similar_messages:
                memory_context = "\n\n**과거 유사한 대화:**\n"
                for msg in similar_messages:
                    memory_context += f"- {msg['role']}: {msg['content'][:100]}...\n"
        except Exception as e:
            print(f"Memory retrieval warning: {e}")
            memory_context = ""

        # ====================================================================
        # STEP 4: GPT-4 Realtime Analysis
        # ====================================================================
        analysis = await message_analyzer.analyze_message(
            message=request.message,
            conversation_context=request.conversation_history or [],
            user_profile=user_profile
        )

        crisis_level = analysis["crisis_level"]
        emotions = analysis["emotions"]

        # ====================================================================
        # STEP 5: Dynamic Prompt Selection
        # ====================================================================
        # Build conversation history for prompt selection
        conversation_history = []
        if request.conversation_history:
            conversation_history = request.conversation_history

        prompt_selection_result = await prompt_selector.select_dynamic_prompt(
            user_message=request.message,
            user_profile=user_profile,
            conversation_history=conversation_history,
            memory_context=memory_context
        )

        selected_prompt = prompt_selection_result["selected_prompt"]
        prompt_key = prompt_selection_result["prompt_key"]

        # ====================================================================
        # STEP 6: OpenAI GPT-4 API Call
        # ====================================================================
        # Build messages for OpenAI
        messages = [
            {"role": "system", "content": selected_prompt}
        ]

        # Add conversation history (last 10 messages)
        if conversation_history:
            messages.extend(conversation_history[-10:])

        # Add current message
        messages.append({"role": "user", "content": request.message})

        # Call OpenAI
        response = await openai_service.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )

        assistant_response = response.choices[0].message.content

        # ====================================================================
        # STEP 7: Save Messages with Embeddings
        # ====================================================================
        # Create embedding for user message
        user_embedding = await openai_service.create_embedding(request.message)

        # Add user message to database
        await conversation_service.add_message(
            conversation_id=conversation.id,
            role="user",
            content=request.message,
            embedding=user_embedding
        )

        # Create embedding for assistant response
        assistant_embedding = await openai_service.create_embedding(assistant_response)

        # Add assistant message to database
        await conversation_service.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_response,
            embedding=assistant_embedding
        )

        # ====================================================================
        # STEP 8: Crisis Alert Generation (if needed)
        # ====================================================================
        alert_data = None
        if crisis_level >= 2:  # Level 2+ requires alert
            alert_response = await alert_system.check_and_alert(
                crisis_level=crisis_level,
                user_id=request.user_id,
                message=request.message,
                crisis_indicators=analysis.get("crisis_indicators", []),
                user_age=user_profile.get("age")
            )
            alert_data = alert_response.model_dump()

        # ====================================================================
        # STEP 9: Return Comprehensive Response
        # ====================================================================
        return IntegratedChatResponse(
            response=assistant_response,
            alert=alert_data,
            emotion_detected=emotions,
            crisis_level=crisis_level,
            prompt_used=prompt_key,
            analysis=analysis,
            conversation_id=str(conversation.id)
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Integrated chat error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}"
        )
