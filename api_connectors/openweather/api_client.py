# api_connectors/openweather/api_client.py

import httpx
from api_connectors.core.exceptions import NetworkOrServerError
from typing import Optional, Tuple, Dict, Any
from api_connectors.core.httpx_client import HTTPClient
from api_connectors.core.logger import get_logger
from api_connectors.core.exceptions import APIError

logger = get_logger(__name__)


class OpenWeatherClient:
    """
    Client pour OpenWeatherMap.

    Stocke api_key et un country par défaut (ISO alpha-2).

    Fournit les méthodes pour accéder aux API:
     - get_lat_lon_by_city_name(city, country)  https://openweathermap.org/api/geocoding-api
     - reverse_geocode(lat, lon)                https://openweathermap.org/api/geocoding-api
     - get_current_weather(city|lat/lon)        https://openweathermap.org/current
     - get_forecast(city|lat/lon)               https://openweathermap.org/forecast5
     - get_air_pollution(city|lat/lon)          https://openweathermap.org/api/air-pollution
    """

    BASE_URL = "https://api.openweathermap.org"

    def __init__(self, api_key: str, country: str = "FR", http_client: Optional[HTTPClient] = None):
        self.api_key = api_key
        self.country = (country or "FR").upper()
        # HTTPClient wrapper (testable / injectable)
        self.http = http_client if http_client is not None else HTTPClient(base_url=self.BASE_URL)

    # ---------------- Validation utilitaires ----------------
    @staticmethod
    def _validate_coordinates_values(lat: float, lon: float):
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"Latitude invalide : {lat} (doit être entre -90 et 90).")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"Longitude invalide : {lon} (doit être entre -180 et 180).")

    @staticmethod
    def _validate_city_and_coords_exclusive(city: Optional[str], lat: Optional[float], lon: Optional[float]):
        # exclusivité : soit city (optionally with country) soit lat AND lon.
        if city and (lat is not None or lon is not None):
            raise ValueError("Fournir soit `city` (et éventuellement `country`), soit `lat`/`lon`, mais pas les deux.")
        if not city and (lat is None or lon is None):
            raise ValueError("Vous devez fournir soit `city`, soit `lat` ET `lon`.")

    # ---------------- Géocoding helpers ----------------
    async def get_lat_lon_by_city_name(self, city: str, country: Optional[str] = None) -> Tuple[float, float]:
        """
        Utilise la Geocoding API OpenWeather pour convertir 'city,country' en (lat, lon).
        Retourne (lat, lon) ou lève ValueError si introuvable.
        """
        country = (country or self.country or "").upper()
        params = {"q": f"{city},{country}", "limit": 1, "appid": self.api_key}

        logger.debug("Récupération des coordonnées : %s,%s", city, country)

        try:
            data = await self.http.get("/geo/1.0/direct", params=params)
        except httpx.ConnectError as e:
            raise NetworkOrServerError(f"Impossible de se connecter à l'API OpenWeather: {e}") from e
        except APIError as e:
            logger.debug("Erreur geocoding: %s", e)
            raise

        if not data or not isinstance(data, list) or len(data) == 0:
            raise ValueError(f"Ville '{city},{country}' introuvable via geocoding.")

        first = data[0]
        if "lat" not in first or "lon" not in first:
            raise ValueError("Réponse geocoding invalide : champs lat/lon manquants.")

        lat, lon = float(first["lat"]), float(first["lon"])
        self._validate_coordinates_values(lat, lon)
        return lat, lon

    async def reverse_geocode(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
        """
        Reverse geocoding : retourne (city, country) si disponible.
        """
        self._validate_coordinates_values(lat, lon)
        params = {"lat": lat, "lon": lon, "limit": 1, "appid": self.api_key}

        try:
            data = await self.http.get("/geo/1.0/reverse", params=params)
        except httpx.ConnectError as e:
            raise NetworkOrServerError(f"Impossible de se connecter à l'API OpenWeather: {e}") from e
        except APIError:
            raise

        if not data or not isinstance(data, list) or len(data) == 0:
            return None, None
        first = data[0]
        return first.get("name"), first.get("country")

    # ---------------- Résolution de coordonnées ----------------
    async def _resolve_coordinates(self, city: Optional[str], country: Optional[str],
                                   lat: Optional[float], lon: Optional[float]) -> Tuple[float, float]:
        """
        Retourne (lat, lon) à utiliser pour les appels d'API.
        Valide les entrées et appelle la geocoding API si nécessaire.
        """
        # Vérifier exclusivité / complétude
        self._validate_city_and_coords_exclusive(city, lat, lon)

        if lat is not None and lon is not None:
            # validation valeurs
            self._validate_coordinates_values(lat, lon)
            return lat, lon

        # sinon on a city défini
        return await self.get_lat_lon_by_city_name(city, country)

    # ---------------- Endpoints ----------------
    async def get_current_weather(self, city: Optional[str] = None, country: Optional[str] = None,
                                  lat: Optional[float] = None, lon: Optional[float] = None,
                                  units: str = "metric", lang: str = "fr") -> Dict[str, Any]:
        """
        Récupère la météo actuelle pour la position résolue.
        """
        lat, lon = await self._resolve_coordinates(city, country, lat, lon)
        params = {"lat": lat, "lon": lon, "appid": self.api_key, "units": units, "lang": lang}
        logger.debug("GET current weather | lat=%s lon=%s", lat, lon)

        try:
            return await self.http.get("/data/2.5/weather", params=params)
        except httpx.ConnectError as e:
            raise NetworkOrServerError(f"Impossible de se connecter à l'API OpenWeather: {e}") from e
        except APIError as e:
            if "401" in str(e):
                raise APIError("Invalid API key for Current Weather API.")
            raise

    async def get_forecast(self, city: Optional[str] = None, country: Optional[str] = None,
                           lat: Optional[float] = None, lon: Optional[float] = None,
                           units: str = "metric", lang: str = "fr") -> Dict[str, Any]:
        """
        Récupère le forecast 3h (endpoint 5-days/3h).
        """
        lat, lon = await self._resolve_coordinates(city, country, lat, lon)
        params = {"lat": lat, "lon": lon, "appid": self.api_key, "units": units, "lang": lang}
        logger.debug("GET forecast | lat=%s lon=%s", lat, lon)

        try:
            return await self.http.get("/data/2.5/forecast", params=params)
        except httpx.ConnectError as e:
            raise NetworkOrServerError(f"Impossible de se connecter à l'API OpenWeather: {e}") from e
        except APIError as e:
            if "401" in str(e):
                raise APIError("Invalid API key for Forecast API.")
            raise

    async def get_air_pollution(self, city: Optional[str] = None, country: Optional[str] = None,
                                lat: Optional[float] = None, lon: Optional[float] = None) -> Dict[str, Any]:
        """
        Récupère la qualité de l'air (endpoint air_pollution).
        """
        lat, lon = await self._resolve_coordinates(city, country, lat, lon)
        params = {"lat": lat, "lon": lon, "appid": self.api_key}
        logger.debug("GET air pollution | lat=%s lon=%s", lat, lon)

        try:
            return await self.http.get("/data/2.5/air_pollution", params=params)
        except httpx.ConnectError as e:
            raise NetworkOrServerError(f"Impossible de se connecter à l'API OpenWeather: {e}") from e
        except APIError as e:
            if "401" in str(e):
                raise APIError("Invalid API key or plan restrictions for Air Pollution API.")
            raise
