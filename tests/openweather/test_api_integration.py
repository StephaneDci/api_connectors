"""
Tests d'intégration pour l'API OpenWeather.

Structure des fichiers de test attendue:
tests/openweather/test_data/
    ├── current_weather_Rome.json
    ├── forecast_Rome.json
    ├── air_pollution_Rome.json
    ├── current_weather_Paris.json
    ├── forecast_Paris.json
    └── air_pollution_Paris.json
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any
import json
import pytest
from unittest.mock import patch
from httpx import ConnectError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api_connectors.openweather_database.models import WeatherRecord


# ============================================================================
# CONFIGURATION DES DONNÉES DE TEST
# ============================================================================

TEST_DATA_DIR = Path("./tests/openweather/test_data")


@dataclass
class LocationTestData:
    """Représente un jeu de données de test pour une localisation."""

    city: str
    country: str
    lat: float
    lon: float
    expected_temp: float
    expected_aqi: int

    # Données mockées (chargées automatiquement)
    mock_current_weather: Dict[str, Any] = None
    mock_forecast: Dict[str, Any] = None
    mock_air_pollution: Dict[str, Any] = None
    mock_geocoding: list = None

    @property
    def location_name(self) -> str:
        """Retourne le nom complet de la localisation (ex: 'Rome,IT')."""
        return f"{self.city},{self.country}"

    @classmethod
    def from_json_files(cls, city: str, country: str):
        """
        Crée une instance en chargeant automatiquement les fichiers JSON.
        Extrait TOUTES les données depuis les fichiers (coordonnées, température, AQI).

        Fichiers attendus:
        - current_weather_{city}.json
        - forecast_{city}.json
        - air_pollution_{city}.json
        """
        # Chargement des fichiers JSON
        try:
            with open(TEST_DATA_DIR / f"current_weather_{city}.json", 'r') as f:
                current_weather = json.load(f)

            with open(TEST_DATA_DIR / f"forecast_{city}.json", 'r') as f:
                forecast = json.load(f)

            with open(TEST_DATA_DIR / f"air_pollution_{city}.json", 'r') as f:
                air_pollution = json.load(f)

            # ✅ Extraction automatique des données depuis les JSON
            lat = current_weather["coord"]["lat"]
            lon = current_weather["coord"]["lon"]
            expected_temp = current_weather["main"]["temp"]
            expected_aqi = air_pollution["list"][0]["main"]["aqi"]

            # Création de l'instance
            instance = cls(
                city=city,
                country=country,
                lat=lat,
                lon=lon,
                expected_temp=expected_temp,
                expected_aqi=expected_aqi
            )

            # Stockage des données mockées
            instance.mock_current_weather = current_weather
            instance.mock_forecast = forecast
            instance.mock_air_pollution = air_pollution

            # Génération du mock de géocodage
            instance.mock_geocoding = [{
                "name": city,
                "lat": lat,
                "lon": lon,
                "country": country
            }]

            print(f"✅ Mock chargés pour {city} (temp={expected_temp}°C, aqi={expected_aqi})")

        except FileNotFoundError as e:
            print(f"❌ ERREUR: Fichier manquant pour {city}: {e}")
            raise
        except KeyError as e:
            print(f"❌ ERREUR: Clé manquante dans les fichiers JSON de {city}: {e}")
            raise

        return instance


# ============================================================================
# DÉFINITION DES DONNÉES DE TEST
# ============================================================================

# Ajoutez simplement de nouvelles villes ici une fois que vous avez générés les données.

TEST_LOCATIONS = {
    "Rome": LocationTestData.from_json_files(city="Rome", country="IT"),
    "Paris": LocationTestData.from_json_files(city="Paris", country="FR"),
}


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_http_client_get():
    """
    Mock universel du HTTPClient.get qui gère toutes les localisations de TEST_LOCATIONS.
    """

    async def mocked_get(self, endpoint: str, params: dict = None):
        """Mock asynchrone adaptatif basé sur les données de TEST_LOCATIONS."""

        # --- Géocodage direct (city → coordinates) ---
        if "/geo/1.0/direct" in endpoint:
            if not params or 'q' not in params:
                return []

            query = params['q']

            # Recherche dans toutes les localisations configurées
            for location_data in TEST_LOCATIONS.values():
                if location_data.city in query or location_data.location_name == query:
                    return location_data.mock_geocoding

            return []

        # --- Endpoints météo (weather, forecast, air_pollution) ---
        if params:
            try:
                request_lat = float(params.get('lat', 0))
                request_lon = float(params.get('lon', 0))
            except (ValueError, TypeError):
                return {}

            # Recherche de la localisation correspondante
            for location_data in TEST_LOCATIONS.values():
                if request_lat == location_data.lat and request_lon == location_data.lon:

                    if "/data/2.5/weather" in endpoint:
                        return location_data.mock_current_weather

                    elif "/data/2.5/forecast" in endpoint:
                        return location_data.mock_forecast

                    elif "/data/2.5/air_pollution" in endpoint:
                        return location_data.mock_air_pollution

        return {}

    # Application du patch
    with patch.object(
        target=__import__('api_connectors.core.httpx_client', fromlist=['HTTPClient']).HTTPClient,
        attribute='get',
        new=mocked_get
    ):
        yield


# ============================================================================
# TESTS PARAMÉTRÉS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("location_key", TEST_LOCATIONS.keys())
async def test_get_weather_report_success(client, mock_http_client_get, location_key):
    """
    Test GET /weather/ (Récupération SANS persistance).
    Ce test est exécuté pour chaque localisation définie dans TEST_LOCATIONS.
    """
    location_data = TEST_LOCATIONS[location_key]

    response = client.get(f"/weather/?location={location_data.location_name}")

    assert response.status_code == 200, (
        f"Expected 200 for {location_key}, got {response.status_code}. "
        f"Response: {response.json()}"
    )

    data = response.json()

    # Vérifications génériques
    assert data["current_weather"]["current_temp"] == pytest.approx(
        location_data.expected_temp, rel=0.01
    ), f"Temperature mismatch for {location_key}"

    assert data["location"]["city"] == location_data.city, (
        f"City mismatch for {location_key}"
    )

    assert len(data["forecast"]) >= 10, (
        f"Not enough forecast items for {location_key}"
    )

    assert data["air_pollution"]["aqi"] == location_data.expected_aqi, (
        f"AQI mismatch for {location_key}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("location_key", TEST_LOCATIONS.keys())
async def test_fetch_and_save_weather_report_success(
    async_client,
    mock_http_client_get,
    override_db_dependency,
    TestingSessionLocal,
    location_key
):
    """
    Test POST /weather/fetch-and-save (Récupération et persistance).
    Ce test est exécuté pour chaque localisation définie dans TEST_LOCATIONS.
    """
    location_data = TEST_LOCATIONS[location_key]

    response = await async_client.post(
        f"/weather/fetch-and-save?location={location_data.location_name}"
    )

    assert response.status_code == 201, (
        f"Expected 201 for {location_key}, got {response.status_code}. "
        f"Response: {response.json()}"
    )

    # Vérification de la persistance en base de données
    async with TestingSessionLocal() as db_session:
        stmt = (
            select(WeatherRecord)
            .filter_by(location_name=location_data.location_name)
            .options(selectinload(WeatherRecord.air_pollution))
        )

        result = await db_session.execute(stmt)
        db_record = result.scalar_one_or_none()

        assert db_record is not None, f"Record not found in DB for {location_key}"

        assert db_record.current_temp == location_data.expected_temp, f"Temperature mismatch in DB for {location_key}"

        assert db_record.location_name == location_data.location_name, (
            f"Location name mismatch in DB for {location_key}"
        )

        assert db_record.air_pollution.aqi == location_data.expected_aqi, (
            f"AQI mismatch in DB for {location_key}"
        )


# ============================================================================
# TESTS DE GESTION D'ERREURS (NON PARAMÉTRÉS)
# ============================================================================

@pytest.mark.asyncio
async def test_get_weather_report_network_failure(async_client):
    """Test la réponse lorsque le client HTTP lève une erreur de connexion."""

    async def raise_connect_error(self, *args, **kwargs):
        raise ConnectError("Simulated network loss")

    with patch.object(
        target=__import__('api_connectors.core.httpx_client', fromlist=['HTTPClient']).HTTPClient,
        attribute='get',
        new=raise_connect_error
    ):
        response = await async_client.get("/weather/?location=AnyCity,XX")

        assert response.status_code == 503, (
            f"Expected 503, got {response.status_code}. Response: {response.json()}"
        )

        response_data = response.json()
        assert "Service OpenWeather non disponible" in response_data.get("detail", "")


@pytest.mark.asyncio
async def test_get_weather_report_invalid_location(client, mock_http_client_get):
    """Test avec une localisation inexistante."""

    response = client.get("/weather/?location=UnknownCity,XX")

    # Devrait retourner une erreur (500 ou 404 selon votre implémentation)
    assert response.status_code in [400, 404, 500], (
        f"Expected error status for unknown city, got {response.status_code}"
    )
