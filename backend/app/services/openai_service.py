"""OpenAI API integration service"""

from typing import List, AsyncGenerator
from openai import AsyncOpenAI
import hashlib

from app.core.config import settings
from app.core.redis import RedisManager


class OpenAIService:
    """Service for OpenAI API interactions with semantic caching"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

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
    ) -> AsyncGenerator[str, None] | str:
        """
        Generate chat completion with semantic caching.

        Args:
            messages: Chat messages
            redis_manager: Redis manager for caching
            stream: Whether to stream response

        Yields/Returns:
            Response chunks if streaming, complete response otherwise
        """
        # Create cache key from messages
        cache_key = self._create_cache_key(messages)

        # Get query embedding for semantic search
        last_message = messages[-1]["content"]
        query_embedding = await self.create_embedding(last_message)

        # Check semantic cache
        cached_result = await redis_manager.semantic_cache_search(query_embedding)

        if cached_result:
            # Return cached response
            cached_response = cached_result["response"]["content"]

            if stream:
                # Simulate streaming for cached response
                for char in cached_response:
                    yield char
            else:
                yield cached_response
            return

        # Generate new response
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

            # Cache the complete response
            await redis_manager.semantic_cache_set(
                query_id=cache_key,
                query_embedding=query_embedding,
                response={"content": response_content},
            )

        else:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                temperature=settings.OPENAI_TEMPERATURE,
            )

            response_content = response.choices[0].message.content

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
