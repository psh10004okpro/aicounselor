"""Conversation management service"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, Message
from app.models.user import User
from app.schemas.conversation import ConversationCreate, MessageCreate
from app.services.openai_service import OpenAIService
from app.core.config import settings


class ConversationService:
    """Service for managing conversations and messages"""

    def __init__(
        self,
        db: AsyncSession,
        openai_service: OpenAIService,
    ):
        self.db = db
        self.openai_service = openai_service

    async def create_conversation(
        self, user_id: UUID, title: Optional[str] = None
    ) -> Conversation:
        """Create a new conversation"""
        conversation = Conversation(user_id=user_id, title=title)
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    async def get_conversation(
        self, conversation_id: UUID, user_id: UUID
    ) -> Optional[Conversation]:
        """Get conversation by ID with messages"""
        result = await self.db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
                Conversation.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_conversations(
        self, user_id: UUID, limit: int = 50
    ) -> List[Conversation]:
        """Get all conversations for a user"""
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.is_deleted == False)
            .order_by(Conversation.last_message_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        embedding: Optional[List[float]] = None,
        crisis_keywords: Optional[List[str]] = None,
    ) -> Message:
        """
        Add a message to a conversation.

        Args:
            conversation_id: Conversation UUID
            role: Message role (user, assistant, system)
            content: Message content
            embedding: Optional embedding vector
            crisis_keywords: Optional list of detected crisis keywords

        Returns:
            Created message
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            embedding=embedding,
            contains_crisis_keywords=bool(crisis_keywords),
            detected_keywords=crisis_keywords,
        )

        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_conversation_context(
        self, conversation_id: UUID, max_messages: Optional[int] = None
    ) -> List[dict[str, str]]:
        """
        Get conversation context for AI completion.

        Args:
            conversation_id: Conversation ID
            max_messages: Maximum number of messages to include

        Returns:
            List of message dicts for OpenAI API
        """
        max_messages = max_messages or settings.MAX_CONTEXT_MESSAGES

        result = await self.db.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.is_deleted == False,
            )
            .order_by(Message.created_at.desc())
            .limit(max_messages)
        )

        messages = list(result.scalars().all())
        messages.reverse()  # Oldest first

        # Convert to OpenAI format
        context = [{"role": msg.role, "content": msg.content} for msg in messages]

        return context

    async def search_similar_messages(
        self, conversation_id: UUID, query_embedding: List[float], top_k: int = 5
    ) -> List[Message]:
        """
        Search for similar messages using vector similarity.

        Args:
            conversation_id: Conversation ID
            query_embedding: Query embedding vector
            top_k: Number of results to return

        Returns:
            List of similar messages
        """
        # Use pgvector's cosine distance operator
        result = await self.db.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.embedding.isnot(None),
                Message.is_deleted == False,
            )
            .order_by(Message.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )

        return list(result.scalars().all())

    async def delete_conversation(self, conversation_id: UUID, user_id: UUID) -> bool:
        """Soft delete a conversation and its messages"""
        conversation = await self.get_conversation(conversation_id, user_id)
        if not conversation:
            return False

        conversation.is_deleted = True

        # Also soft delete all messages
        result = await self.db.execute(
            select(Message).where(Message.conversation_id == conversation_id)
        )
        messages = result.scalars().all()
        for message in messages:
            message.is_deleted = True

        await self.db.commit()
        return True
