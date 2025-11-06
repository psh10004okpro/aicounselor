"""
OpenAI Client Factory
OpenAI 클라이언트 팩토리 (싱글톤 패턴)

Centralized management of OpenAI API client instances.
"""

from openai import AsyncOpenAI
from app.core.config import settings


class OpenAIClientFactory:
    """
    OpenAI 클라이언트 팩토리

    싱글톤 패턴으로 단일 클라이언트 인스턴스 관리.
    모든 서비스에서 동일한 클라이언트를 공유하여 연결 풀을 효율적으로 사용.

    Usage:
        ```python
        from app.services.openai_client import OpenAIClientFactory

        client = OpenAIClientFactory.get_client()
        response = await client.chat.completions.create(...)
        ```
    """

    _client: AsyncOpenAI = None

    @classmethod
    def get_client(cls) -> AsyncOpenAI:
        """
        Get OpenAI client instance (singleton)

        싱글톤 패턴으로 클라이언트 반환.
        처음 호출 시에만 새 인스턴스를 생성하고, 이후에는 기존 인스턴스를 재사용.

        Returns:
            AsyncOpenAI: OpenAI API 클라이언트 인스턴스

        Example:
            ```python
            client = OpenAIClientFactory.get_client()
            ```
        """
        if cls._client is None:
            cls._client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=30.0,  # 30초 타임아웃
                max_retries=3  # 최대 3회 재시도
            )
        return cls._client

    @classmethod
    def reset_client(cls):
        """
        Reset client instance (for testing)

        테스트용 클라이언트 리셋.
        주로 단위 테스트에서 Mock 객체로 교체하기 전에 사용.

        Example:
            ```python
            # In test
            OpenAIClientFactory.reset_client()
            OpenAIClientFactory._client = MockOpenAIClient()
            ```
        """
        cls._client = None

    @classmethod
    def is_initialized(cls) -> bool:
        """
        Check if client is initialized

        클라이언트가 초기화되었는지 확인.

        Returns:
            bool: 초기화 여부

        Example:
            ```python
            if OpenAIClientFactory.is_initialized():
                print("Client is ready")
            ```
        """
        return cls._client is not None
