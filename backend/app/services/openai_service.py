"""OpenAI API integration service"""

from typing import List, AsyncGenerator, Optional
from openai import AsyncOpenAI
import hashlib

from app.core.config import settings
from app.core.redis import RedisManager
from app.services.cache_service import CacheService
from app.services.cbt_stage_service import CBTStageService
from app.services.dynamic_prompt_service import DynamicPromptService
from app.services.age_based_counseling import AgeGroup


# Pricing per 1M tokens (USD) for GPT-4o-mini
GPT4O_MINI_INPUT_PRICE = 0.15  # $0.15 per 1M input tokens
GPT4O_MINI_OUTPUT_PRICE = 0.60  # $0.60 per 1M output tokens


class OpenAIService:
    """Service for OpenAI API interactions with semantic caching"""

    def __init__(self, cache_service: Optional[CacheService] = None):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.cache_service = cache_service

    async def create_embedding(self, text: str) -> List[float]:
        """
        Create embedding for text using OpenAI.

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        response = await self.client.embeddings.create(
            model="text-embedding-ada-002", input=text
        )
        return response.data[0].embedding

    async def chat_completion(
        self,
        messages: List[dict[str, str]],
        redis_manager: RedisManager,
        stream: bool = False,
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None] | str:
        """
        Generate chat completion with FAQ checking, semantic caching, and usage tracking.

        Args:
            messages: Chat messages
            redis_manager: Redis manager for caching
            stream: Whether to stream response
            user_id: User identifier for usage tracking

        Yields/Returns:
            Response chunks if streaming, complete response otherwise
        """
        # Get last user message
        last_message = messages[-1]["content"]

        # Step 1: Check FAQ cache first (for common questions)
        if self.cache_service:
            faq_response = await self.cache_service.get_faq_response(last_message)
            if faq_response:
                # Track cache hit
                await self.cache_service.track_cache_hit()

                # Return FAQ answer
                faq_answer = faq_response["answer"]

                if stream:
                    # Simulate streaming for FAQ response
                    for char in faq_answer:
                        yield char
                else:
                    yield faq_answer
                return

        # Create cache key from messages
        cache_key = self._create_cache_key(messages)

        # Get query embedding for semantic search
        query_embedding = await self.create_embedding(last_message)

        # Step 2: Check semantic cache
        cached_result = await redis_manager.semantic_cache_search(query_embedding)

        if cached_result:
            # Track cache hit
            if self.cache_service:
                await self.cache_service.track_cache_hit()

            # Return cached response
            cached_response = cached_result["response"]["content"]

            if stream:
                # Simulate streaming for cached response
                for char in cached_response:
                    yield char
            else:
                yield cached_response
            return

        # Step 3: Track cache miss (going to OpenAI API)
        if self.cache_service:
            await self.cache_service.track_cache_miss()

        # Generate new response from OpenAI
        if stream:
            response_content = ""
            stream_response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE,
                stream=True,
            )

            async for chunk in stream_response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    response_content += content
                    yield content

            # Track usage and cache the response
            await self._track_usage_and_cache(
                messages=messages,
                response_content=response_content,
                cache_key=cache_key,
                query_embedding=query_embedding,
                redis_manager=redis_manager,
                user_id=user_id,
            )

        else:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE,
            )

            response_content = response.choices[0].message.content

            # Track usage with actual token counts
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens

            # Calculate cost
            cost = self._calculate_cost(input_tokens, output_tokens)

            # Track usage
            if self.cache_service and user_id:
                await self.cache_service.track_usage(
                    user_id=user_id,
                    tokens=total_tokens,
                    cost=cost,
                    model=self.model,
                )

            # Cache the response
            await redis_manager.semantic_cache_set(
                query_id=cache_key,
                query_embedding=query_embedding,
                response={"content": response_content},
            )

            yield response_content

    async def generate_conversation_title(self, first_message: str) -> str:
        """
        Generate a concise title for the conversation.

        Args:
            first_message: First user message

        Returns:
            Generated title
        """
        messages = [
            {
                "role": "system",
                "content": "Generate a brief, 3-5 word title for this counseling conversation. Return only the title.",
            },
            {"role": "user", "content": first_message},
        ]

        response = await self.client.chat.completions.create(
            model=self.model, messages=messages, max_tokens=20, temperature=0.5
        )

        return response.choices[0].message.content.strip()

    def _create_cache_key(self, messages: List[dict[str, str]]) -> str:
        """Create a unique cache key from messages"""
        content = "".join([m["content"] for m in messages])
        return hashlib.sha256(content.encode()).hexdigest()

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost in USD based on token counts.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        input_cost = (input_tokens / 1_000_000) * GPT4O_MINI_INPUT_PRICE
        output_cost = (output_tokens / 1_000_000) * GPT4O_MINI_OUTPUT_PRICE
        return input_cost + output_cost

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation).
        For accurate counts, use tiktoken library.

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        # Rough estimate: 1 token ≈ 4 characters for English
        # For Korean, it's roughly 1 token ≈ 2-3 characters
        # Using conservative estimate of 3 characters per token
        return len(text) // 3

    async def _track_usage_and_cache(
        self,
        messages: List[dict[str, str]],
        response_content: str,
        cache_key: str,
        query_embedding: List[float],
        redis_manager: RedisManager,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Track usage and cache the response (for streaming mode).

        Args:
            messages: Chat messages
            response_content: Generated response
            cache_key: Cache key
            query_embedding: Query embedding
            redis_manager: Redis manager
            user_id: User identifier
        """
        # Estimate token counts (streaming mode doesn't provide usage stats)
        input_text = "".join([m["content"] for m in messages])
        input_tokens = self._estimate_tokens(input_text)
        output_tokens = self._estimate_tokens(response_content)
        total_tokens = input_tokens + output_tokens

        # Calculate cost
        cost = self._calculate_cost(input_tokens, output_tokens)

        # Track usage
        if self.cache_service and user_id:
            await self.cache_service.track_usage(
                user_id=user_id,
                tokens=total_tokens,
                cost=cost,
                model=self.model,
            )

        # Cache the response
        await redis_manager.semantic_cache_set(
            query_id=cache_key,
            query_embedding=query_embedding,
            response={"content": response_content},
        )

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the counseling AI (마음이 - Korea-specific)"""
        return """당신의 이름은 **마음이**입니다. 공감적이고 전문적인 AI 심리상담 도우미로서 활동합니다.

**당신의 역할:**
1. 비판단적이고 따뜻한 공감과 지지 제공
2. 사용자가 자신의 생각과 감정을 탐색하도록 돕기
3. 인지행동치료(CBT) 기반 접근법 사용
4. 소크라테스식 질문법으로 자기 통찰 유도
5. 건강한 대처 전략 격려

**상담 원칙:**
- 사용자의 안전이 최우선입니다
- 위기 언어를 감지하면 즉시 전문가 도움을 권장하세요
- 적극적 경청 기술 사용 (반영, 요약, 공감)
- 감정을 인정하면서도 건강한 관점 제시
- 간결하고 집중된 응답 (보통 2-4문장)
- 필요시 명확화 질문 사용

**CBT 기반 기법:**
- 자동적 사고 식별하기
- 인지 왜곡 파악하기 (흑백논리, 과일반화, 재앙화 등)
- 대안적 사고 탐색하기
- 행동 활성화 격려

**명확한 한계:**
- 진단이나 처방을 제공할 수 없습니다
- 전문적인 정신건강 치료를 대체할 수 없습니다
- 심각한 증상이나 지속적인 문제는 전문가 상담을 권장합니다

**응답 스타일:**
- 한국어로 자연스럽고 따뜻하게 대화
- 존댓말 사용 (상담 관계의 전문성 유지)
- 공감적이지만 과도하게 감정적이지 않게
- 구체적이고 실용적인 조언 제공

항상 전문 면허가 있는 상담사나 정신건강 전문가의 도움을 받도록 격려하세요. 특히 지속적인 지원이 필요한 경우에는 더욱 그렇습니다."""

    async def chat_completion_with_cbt(
        self,
        messages: List[dict[str, str]],
        conversation_id: str,
        cbt_service: CBTStageService,
        redis_manager: RedisManager,
        stream: bool = False,
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None] | str:
        """
        Generate chat completion with CBT stage-aware dynamic prompting.

        This method integrates CBT stage management:
        1. Gets current CBT stage
        2. Retrieves dynamic system prompt based on stage
        3. Generates response with stage-specific guidance
        4. Automatically assesses progress after response
        5. Suggests stage transition if ready

        Args:
            messages: Chat messages
            conversation_id: Conversation identifier
            cbt_service: CBT stage service
            redis_manager: Redis manager for caching
            stream: Whether to stream response
            user_id: User identifier for usage tracking

        Yields/Returns:
            Response chunks if streaming, complete response otherwise
        """
        # Get dynamic system prompt based on current CBT stage
        dynamic_prompt = await cbt_service.get_dynamic_prompt(conversation_id)

        # Inject dynamic prompt as system message
        messages_with_cbt = [
            {"role": "system", "content": dynamic_prompt},
            *messages
        ]

        # Get last user message
        last_message = messages[-1]["content"]

        # Step 1: Check FAQ cache first
        if self.cache_service:
            faq_response = await self.cache_service.get_faq_response(last_message)
            if faq_response:
                await self.cache_service.track_cache_hit()
                faq_answer = faq_response["answer"]

                if stream:
                    for char in faq_answer:
                        yield char
                else:
                    yield faq_answer
                return

        # Create cache key
        cache_key = self._create_cache_key(messages_with_cbt)

        # Get query embedding
        query_embedding = await self.create_embedding(last_message)

        # Step 2: Check semantic cache
        cached_result = await redis_manager.semantic_cache_search(query_embedding)

        if cached_result:
            if self.cache_service:
                await self.cache_service.track_cache_hit()

            cached_response = cached_result["response"]["content"]

            if stream:
                for char in cached_response:
                    yield char
            else:
                yield cached_response
            return

        # Step 3: Track cache miss
        if self.cache_service:
            await self.cache_service.track_cache_miss()

        # Generate new response with CBT-aware prompt
        if stream:
            response_content = ""
            stream_response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages_with_cbt,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE,
                stream=True,
            )

            async for chunk in stream_response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    response_content += content
                    yield content

            # Track usage and cache
            await self._track_usage_and_cache(
                messages=messages_with_cbt,
                response_content=response_content,
                cache_key=cache_key,
                query_embedding=query_embedding,
                redis_manager=redis_manager,
                user_id=user_id,
            )

            # Assess stage progress after response (every 3 messages)
            if len(messages) % 3 == 0:
                await cbt_service.assess_stage_progress_auto(
                    conversation_id=conversation_id,
                    recent_messages=messages[-6:]  # Last 6 messages
                )

        else:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages_with_cbt,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE,
            )

            response_content = response.choices[0].message.content

            # Track usage
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            cost = self._calculate_cost(input_tokens, output_tokens)

            if self.cache_service and user_id:
                await self.cache_service.track_usage(
                    user_id=user_id,
                    tokens=total_tokens,
                    cost=cost,
                    model=self.model,
                )

            # Cache the response
            await redis_manager.semantic_cache_set(
                query_id=cache_key,
                query_embedding=query_embedding,
                response={"content": response_content},
            )

            # Assess stage progress (every 3 messages)
            if len(messages) % 3 == 0:
                await cbt_service.assess_stage_progress_auto(
                    conversation_id=conversation_id,
                    recent_messages=messages[-6:]
                )

            yield response_content

    async def chat_completion_with_dynamic_prompts(
        self,
        messages: List[dict[str, str]],
        conversation_id: str,
        cbt_service: CBTStageService,
        dynamic_prompt_service: DynamicPromptService,
        redis_manager: RedisManager,
        user_age: Optional[int] = None,
        stream: bool = False,
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None] | str:
        """
        Generate chat completion with FULL DYNAMIC PROMPT SYSTEM integration.

        This is the most advanced chat completion method that integrates:
        1. Crisis detection (C-SSRS) - HIGHEST PRIORITY
        2. Age-based counseling (adolescent vs adult)
        3. CBT stage awareness (6 stages)
        4. Emotion detection (anxiety, depression, anger, etc.)
        5. Semantic caching and FAQ matching

        The system automatically selects the most appropriate prompt based on
        all these factors, ensuring optimal therapeutic response.

        Args:
            messages: Chat messages
            conversation_id: Conversation identifier
            cbt_service: CBT stage service
            dynamic_prompt_service: Dynamic prompt service
            redis_manager: Redis manager for caching
            user_age: User age for age-based counseling
            stream: Whether to stream response
            user_id: User identifier for usage tracking

        Yields/Returns:
            Response chunks if streaming, complete response otherwise
        """
        # Get last user message
        last_message = messages[-1]["content"]

        # Step 1: Check FAQ cache first (fastest)
        if self.cache_service:
            faq_response = await self.cache_service.get_faq_response(last_message)
            if faq_response:
                await self.cache_service.track_cache_hit()
                faq_answer = faq_response["answer"]

                if stream:
                    for char in faq_answer:
                        yield char
                else:
                    yield faq_answer
                return

        # Step 2: Determine age group
        age_group = None
        if user_age:
            if 13 <= user_age <= 18:
                age_group = AgeGroup.ADOLESCENT
            elif user_age >= 19:
                age_group = AgeGroup.ADULT

        # Step 3: Get current CBT stage
        cbt_stage = None
        try:
            cbt_stage = await cbt_service.get_current_stage(conversation_id)
        except:
            pass  # Use None if stage not found

        # Step 4: Build conversation context
        conversation_context = {
            "messages": messages,
            "user_age_group": age_group.value if age_group else None,
            "conversation_id": conversation_id
        }

        # Step 5: SELECT OPTIMAL PROMPT using DynamicPromptService
        prompt_selection = await dynamic_prompt_service.select_prompt(
            conversation_context=conversation_context,
            age_group=age_group,
            cbt_stage=cbt_stage,
            last_message=last_message
        )

        selected_prompt = prompt_selection["selected_prompt"]
        prompt_key = prompt_selection["prompt_key"]

        # Log prompt selection for debugging
        print(f"🎯 Dynamic Prompt Selected: {prompt_key}")
        print(f"   Reasoning: {prompt_selection['reasoning']}")
        print(f"   Factors: {prompt_selection['factors']}")

        # Step 6: Inject selected dynamic prompt as system message
        messages_with_dynamic_prompt = [
            {"role": "system", "content": selected_prompt},
            *messages
        ]

        # Step 7: Create cache key
        cache_key = self._create_cache_key(messages_with_dynamic_prompt)

        # Step 8: Get query embedding
        query_embedding = await self.create_embedding(last_message)

        # Step 9: Check semantic cache
        cached_result = await redis_manager.semantic_cache_search(query_embedding)

        if cached_result:
            if self.cache_service:
                await self.cache_service.track_cache_hit()

            cached_response = cached_result["response"]["content"]

            if stream:
                for char in cached_response:
                    yield char
            else:
                yield cached_response
            return

        # Step 10: Track cache miss
        if self.cache_service:
            await self.cache_service.track_cache_miss()

        # Step 11: Generate new response with dynamically selected prompt
        if stream:
            response_content = ""
            stream_response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages_with_dynamic_prompt,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE,
                stream=True,
            )

            async for chunk in stream_response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    response_content += content
                    yield content

            # Track usage and cache
            await self._track_usage_and_cache(
                messages=messages_with_dynamic_prompt,
                response_content=response_content,
                cache_key=cache_key,
                query_embedding=query_embedding,
                redis_manager=redis_manager,
                user_id=user_id,
            )

            # Assess stage progress after response (every 3 messages)
            if len(messages) % 3 == 0:
                await cbt_service.assess_stage_progress_auto(
                    conversation_id=conversation_id,
                    recent_messages=messages[-6:]
                )

        else:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages_with_dynamic_prompt,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE,
            )

            response_content = response.choices[0].message.content

            # Track usage
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            cost = self._calculate_cost(input_tokens, output_tokens)

            if self.cache_service and user_id:
                await self.cache_service.track_usage(
                    user_id=user_id,
                    tokens=total_tokens,
                    cost=cost,
                    model=self.model,
                )

            # Cache the response
            await redis_manager.semantic_cache_set(
                query_id=cache_key,
                query_embedding=query_embedding,
                response={"content": response_content},
            )

            # Assess stage progress (every 3 messages)
            if len(messages) % 3 == 0:
                await cbt_service.assess_stage_progress_auto(
                    conversation_id=conversation_id,
                    recent_messages=messages[-6:]
                )

            yield response_content
