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
        """Build the system prompt for the counseling AI"""
        return """You are a compassionate and professional AI counseling assistant. Your role is to:

1. Provide empathetic, non-judgmental support
2. Help users explore their thoughts and feelings
3. Encourage healthy coping strategies
4. Maintain professional boundaries
5. Never diagnose or prescribe treatment

Important guidelines:
- Always prioritize user safety
- If you detect crisis language, express concern and encourage professional help
- Use active listening techniques
- Validate feelings while promoting healthy perspectives
- Keep responses concise and focused (2-4 sentences typically)
- Ask clarifying questions when helpful

You are NOT a replacement for professional mental health care. Always encourage users to seek licensed professionals for ongoing support."""
