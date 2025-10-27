import requests
from .exceptions import APIError
from .logger import get_logger

logger = get_logger(__name__)

class HTTPClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def get(self, endpoint: str, params: dict = None):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        logger.debug(f"➡️ GET {url} | params={params}")
        response = requests.get(url, params=params, timeout=10)
        logger.debug(f"⬅️ Response {response.status_code}: {response.text[:300]}")
        if not response.ok:
            raise APIError(f"HTTP {response.status_code}: {response.text}")
        return response.json()
