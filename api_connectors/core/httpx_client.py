import httpx
from typing import Any, Optional


class HTTPClient:
    """
    Client HTTP asynchrone générique basé sur httpx.
    - Gère les connexions via contexte async (startup/shutdown)
    - Fournit un accès facile via get/post/etc.
    - Permet l'injection (tests/mocking)
    """

    def __init__(self, base_url: Optional[str] = None, timeout: int = 10):
        self._client = httpx.AsyncClient(base_url=base_url or "", timeout=timeout)

    async def get(self, url: str, params: Optional[dict[str, Any]] = None) -> Any:
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def post(self, url: str, data: Optional[dict[str, Any]] = None, json: Any = None) -> Any:
        response = await self._client.post(url, data=data, json=json)
        response.raise_for_status()
        return response.json()

    async def aclose(self):
        """Ferme explicitement le client HTTP."""
        await self._client.aclose()

    async def __aenter__(self):
        """Utilisation contextuelle : `async with HTTPClient() as client:`"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()
