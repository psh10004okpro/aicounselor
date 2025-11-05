"""Memory management service for long-term context"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.services.openai_service import OpenAIService


class MemoryService:
    """Service for managing user memories (semantic, episodic, fact)"""

    def __init__(self, db: AsyncSession, openai_service: OpenAIService):
        self.db = db
        self.openai_service = openai_service

    async def create_memory(
        self,
        user_id: UUID,
        memory_type: str,
        content: str,
        importance_score: float = 0.5,
        source_conversation_id: Optional[UUID] = None,
        source_message_id: Optional[UUID] = None,
        metadata: dict = None,
    ) -> Memory:
        """
        Create a new memory.

        Args:
            user_id: User identifier
            memory_type: Type of memory (semantic/episodic/fact)
            content: Memory content
            importance_score: Importance score (0-1)
            source_conversation_id: Source conversation
            source_message_id: Source message
            metadata: Additional metadata

        Returns:
            Created memory
        """
        # Generate embedding
        embedding = await self.openai_service.create_embedding(content)

        memory = Memory(
            user_id=user_id,
            memory_type=memory_type,
            content=content,
            embedding=embedding,
            importance_score=importance_score,
            source_conversation_id=source_conversation_id,
            source_message_id=source_message_id,
            metadata=metadata or {},
        )

        self.db.add(memory)
        await self.db.commit()
        await self.db.refresh(memory)

        return memory

    async def get_relevant_memories(
        self,
        user_id: UUID,
        query: str,
        memory_types: Optional[List[str]] = None,
        min_importance: float = 0.3,
        max_results: int = 10,
    ) -> List[dict]:
        """
        Get relevant memories using vector similarity.

        Args:
            user_id: User identifier
            query: Query text
            memory_types: Filter by memory types
            min_importance: Minimum importance score
            max_results: Maximum number of results

        Returns:
            List of relevant memories with similarity scores
        """
        # Generate query embedding
        query_embedding = await self.openai_service.create_embedding(query)

        # Use SQL function to get relevant memories
        sql = """
        SELECT * FROM get_relevant_memories(
            :query_embedding,
            :user_id,
            :memory_types,
            :min_importance,
            :max_results
        )
        """

        result = await self.db.execute(
            sql,
            {
                "query_embedding": query_embedding,
                "user_id": user_id,
                "memory_types": memory_types,
                "min_importance": min_importance,
                "max_results": max_results,
            },
        )

        memories = []
        for row in result:
            memories.append(
                {
                    "memory_id": row.memory_id,
                    "memory_type": row.memory_type,
                    "content": row.content,
                    "importance_score": row.importance_score,
                    "similarity": row.similarity,
                }
            )

        # Update access counts
        memory_ids = [m["memory_id"] for m in memories]
        if memory_ids:
            await self.db.execute(
                select(Memory)
                .where(Memory.memory_id.in_(memory_ids))
                .update(
                    {
                        Memory.access_count: Memory.access_count + 1,
                        Memory.last_accessed_at: func.now(),
                    }
                )
            )
            await self.db.commit()

        return memories

    async def extract_memories_from_conversation(
        self, user_id: UUID, conversation_id: UUID, messages: List[dict]
    ) -> List[Memory]:
        """
        Extract important memories from a conversation using AI.

        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            messages: List of messages

        Returns:
            List of extracted memories
        """
        # Create a prompt to extract memories
        conversation_text = "\n".join(
            [f"{m['role']}: {m['content']}" for m in messages]
        )

        prompt = f"""다음 상담 대화에서 중요한 정보를 추출하여 분류해주세요:

{conversation_text}

다음 형식으로 JSON 배열로 반환해주세요:
[
    {{
        "type": "semantic|episodic|fact",
        "content": "추출된 내용",
        "importance": 0.0-1.0
    }}
]

- semantic: 일반적인 지식이나 개념
- episodic: 구체적인 사건이나 경험
- fact: 사용자에 대한 사실적 정보 (이름, 직업, 관심사 등)

중요도가 0.5 이상인 것만 추출하세요."""

        try:
            # Use OpenAI to extract memories
            response = await self.openai_service.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )

            import json

            extracted = json.loads(response.choices[0].message.content)

            # Create memories
            memories = []
            for item in extracted.get("memories", []):
                memory = await self.create_memory(
                    user_id=user_id,
                    memory_type=item["type"],
                    content=item["content"],
                    importance_score=item["importance"],
                    source_conversation_id=conversation_id,
                )
                memories.append(memory)

            return memories

        except Exception as e:
            print(f"Error extracting memories: {e}")
            return []

    async def get_user_memories(
        self,
        user_id: UUID,
        memory_type: Optional[str] = None,
        min_importance: float = 0.0,
        limit: int = 50,
    ) -> List[Memory]:
        """Get all memories for a user"""
        query = select(Memory).where(
            Memory.user_id == user_id,
            Memory.is_deleted == False,
            Memory.importance_score >= min_importance,
        )

        if memory_type:
            query = query.where(Memory.memory_type == memory_type)

        query = query.order_by(Memory.importance_score.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_memory_importance(
        self, memory_id: UUID, importance_score: float
    ) -> Optional[Memory]:
        """Update memory importance score"""
        memory = await self.db.get(Memory, memory_id)
        if memory:
            memory.importance_score = max(0.0, min(1.0, importance_score))
            await self.db.commit()
            await self.db.refresh(memory)
        return memory

    async def delete_memory(self, memory_id: UUID) -> bool:
        """Soft delete a memory"""
        memory = await self.db.get(Memory, memory_id)
        if memory:
            memory.is_deleted = True
            await self.db.commit()
            return True
        return False

    async def consolidate_memories(self, user_id: UUID, threshold: int = 100):
        """
        Consolidate similar memories to reduce redundancy.

        This should be run periodically to merge similar memories
        and adjust importance scores based on access patterns.
        """
        # Get all user memories
        memories = await self.get_user_memories(user_id, limit=threshold)

        # Group similar memories (simple implementation)
        # In production, use more sophisticated clustering

        # Boost importance of frequently accessed memories
        for memory in memories:
            if memory.access_count > 5:
                new_importance = min(
                    1.0, memory.importance_score + (memory.access_count * 0.01)
                )
                memory.importance_score = new_importance

        await self.db.commit()

        # Decay importance of old, unaccessed memories
        # This helps keep only relevant information
        from datetime import datetime, timedelta

        old_threshold = datetime.utcnow() - timedelta(days=30)
        for memory in memories:
            if memory.last_accessed_at and memory.last_accessed_at < old_threshold:
                memory.importance_score = max(0.0, memory.importance_score - 0.1)

        await self.db.commit()
