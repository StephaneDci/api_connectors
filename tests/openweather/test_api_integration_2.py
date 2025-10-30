from sqlalchemy import select
from sqlalchemy.orm import selectinload
from api_connectors.openweather_database.models import WeatherRecord
import json
import os
from unittest.mock import patch
import pytest
from httpx import ConnectError

# --- CONSTANTES DE DONNÉES DE MOCK (Rome) ---

ROME_DATA_DIR = "./tests/openweather/test_data"
ROME_COORDS = {"lat": 41.8933, "lon": 12.4829}
ROME_CURRENT_TEMP = 17.58

try:
    with open(os.path.join(ROME_DATA_DIR, "current_weather_Rome.json"), 'r') as f:
        MOCK_CURRENT_WEATHER_ROME = json.load(f)
    with open(os.path.join(ROME_DATA_DIR, "forecast_Rome.json"), 'r') as f:
        MOCK_FORECAST_ROME = json.load(f)
    with open(os.path.join(ROME_DATA_DIR, "air_pollution_Rome.json"), 'r') as f:
        MOCK_AIR_POLLUTION_ROME = json.load(f)

    MOCK_GEO_ROME = [{"name": "Rome", "lat": ROME_COORDS["lat"], "lon": ROME_COORDS["lon"], "country": "IT"}]
    print(f"MOCK_GEO_ROME chargé: {MOCK_GEO_ROME}")

except FileNotFoundError:
    print("ERREUR: Fichiers de MOCK (Rome) non trouvés. Les mocks retourneront des valeurs vides.")


@pytest.fixture
def mock_http_client_get():
    """
    Simule la méthode 'get' du HTTPClient pour toutes les API OpenWeather.
    """

    async def mocked_get(self, endpoint: str, params: dict = None):
        """Mock asynchrone qui retourne les bonnes données selon l'endpoint."""
        if "/geo/1.0/direct" in endpoint:
            if params and 'q' in params:
                query = params['q']
                if 'Rome' in query or 'ROME' in query or 'rome' in query or 'Rome,IT' == query:
                    print(MOCK_GEO_ROME)
                    return MOCK_GEO_ROME
            return []  # <-- Si la requête ne correspond pas, retourne []

        # Utilisation de ROME_COORDS pour la comparaison exacte
        if ROME_COORDS:
            target_lat = ROME_COORDS["lat"]
            target_lon = ROME_COORDS["lon"]

            if "/data/2.5/weather" in endpoint:
                if params:
                    lat = float(params.get('lat', 0))
                    lon = float(params.get('lon', 0))
                    # Comparaison de précision très élevée (acceptable pour des mocks exacts)
                    if lat == target_lat and lon == target_lon:
                        return MOCK_CURRENT_WEATHER_ROME
                return {}

            elif "/data/2.5/forecast" in endpoint:
                if params:
                    lat = float(params.get('lat', 0))
                    lon = float(params.get('lon', 0))
                    if lat == target_lat and lon == target_lon:
                        return MOCK_FORECAST_ROME
                return {}

            elif "/data/2.5/air_pollution" in endpoint:
                if params:
                    lat = float(params.get('lat', 0))
                    lon = float(params.get('lon', 0))
                    if lat == target_lat and lon == target_lon:
                        return MOCK_AIR_POLLUTION_ROME
                return {}

        return {}

    # Patch de la méthode d'instance HTTPClient.get
    with patch.object(
            target=__import__('api_connectors.core.httpx_client', fromlist=['HTTPClient']).HTTPClient,
            attribute='get',
            new=mocked_get
    ):
        yield


# --- Tests d'Intégration ---


@pytest.mark.asyncio
async def test_get_weather_report_success(client, mock_http_client_get):  # <-- Utilisation de client (synchrone)
    """Test GET /weather/ (Récupération SANS persistance)."""
    location = "Rome,IT"
    response = client.get(f"/weather/?location={location}")  # <-- Appel synchrone

    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.json()}"
    data = response.json()

    assert data["current_weather"]["current_temp"] == ROME_CURRENT_TEMP
    assert data["location"]["city"] == "Rome"
    assert len(data["forecast"]) >= 10
    assert data["air_pollution"]["aqi"] == 2


@pytest.mark.asyncio
async def test_fetch_and_save_weather_report_success(
        async_client, # MODIFIÉ: Utilisation du client asynchrone
        mock_http_client_get,
        override_db_dependency,
        TestingSessionLocal,
        setup_db
):
    """Test POST /weather/fetch-and-save (Récupération et persistance)."""
    location = "Rome,IT"

    # MODIFIÉ: Appel asynchrone avec 'await' pour exécuter la route dans un contexte asyncio
    response = await async_client.post(f"/weather/fetch-and-save?location={location}")

    assert response.status_code == 201, f"Expected 201, got {response.status_code}. Response: {response.json()}"

    # Vérification de la persistance en base de données de test
    async with TestingSessionLocal() as db_session:
        # La session de vérification utilise le même moteur DB en mémoire
        stmt = (
            select(WeatherRecord)
            .filter_by(location_name=location)
            .options(selectinload(WeatherRecord.air_pollution))
        )
        result = await db_session.execute(stmt)
        db_record = result.scalar_one_or_none()

        assert db_record is not None, "Record not found in database"
        assert db_record.current_temp == ROME_CURRENT_TEMP
        assert db_record.location_name == location
        assert db_record.air_pollution.aqi == 2


@pytest.mark.asyncio
async def test_get_weather_report_network_failure(async_client):  # <-- Utilisation de async_client
    """Test la réponse lorsque le client HTTP lève une erreur de connexion (503 attendue)."""

    async def raise_connect_error(self, *args, **kwargs):
        """Simule une erreur de connexion."""
        raise ConnectError("Simulated network loss")

    # Patch correct avec patch.object
    with patch.object(
            target=__import__('api_connectors.core.httpx_client', fromlist=['HTTPClient']).HTTPClient,
            attribute='get',
            new=raise_connect_error
    ):
        response = await async_client.get("/weather/?location=Naples,IT")  # <-- Appel asynchrone

        assert response.status_code == 503, f"Expected 503, got {response.status_code}. Response: {response.json()}"
        response_data = response.json()
        assert "Service OpenWeather non disponible" in response_data.get("detail", "")