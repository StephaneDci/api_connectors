import httpx
from .exceptions import APIError
from .logger import get_logger
from typing import Dict, Any

logger = get_logger(__name__)


class HTTPClient:
    """Client HTTP asynchrone basé sur httpx pour les appels API externes."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        # Le client 'httpx' doit être instancié, mais la connexion gérée
        # par le context manager pour une meilleure pratique.
        # On utilise des settings par défaut pour le client
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0)

        # La méthode doit devenir asynchrone

    async def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        url = endpoint.lstrip('/')
        logger.debug(f"➡️ GET {self.base_url}/{url} | params={params}")

        try:
            # Utilisation de 'await' pour un I/O non-bloquant
            response = await self._client.get(url, params=params)

        except httpx.HTTPError as e:
            # Gérer les erreurs de connexion/timeout de httpx
            logger.error(f"HTTPX Error on {url}: {e}")
            raise APIError(f"Erreur HTTPX: {e}")

        logger.debug(f"⬅️ Response {response.status_code}: {response.text[:300]}")

        if not response.is_success:  # 'is_success' est le statut de succès standard de httpx
            logger.error(f"API Error {response.status_code}: {response.text}")
            raise APIError(f"HTTP {response.status_code}: {response.text}")

        return response.json()

    # Ajout du support pour l'utilisation dans un bloc 'async with'
    async def __aenter__(self):
        """Ouverture du client pour le context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Fermeture propre de la connexion."""
        await self._client.aclose()

# Note : Si vous instanciez le client en dehors de l'application principale
# (e.g., dans api_client.py), vous pourriez vouloir le créer à l'intérieur d'un
# context manager ou utiliser un singleton géré par FastAPI lifecycle.
# Pour l'instant, nous le laissons ainsi, et gérons l'asynchronisme dans api_client.