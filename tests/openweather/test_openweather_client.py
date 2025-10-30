# Fichier : tests/weather/test_openweather_client.py
import pytest
import json
import os
from unittest.mock import AsyncMock
from api_connectors.openweather.api_client import OpenWeatherClient


# Assurez-vous d'avoir installé pytest-asyncio

def load_json(filename):
    """Charge un fichier JSON depuis tests/weather/data/"""
    # NOTE: Assurez-vous que le chemin d'accès au fichier est correct
    # Si 'test_data' est au même niveau que le fichier de test, utilisez simplement le chemin relatif.
    base = os.path.dirname(os.path.abspath(__file__))

    # Tentative d'accès à un répertoire plus sûr (si test_data est au même niveau que le fichier de test)
    # Dans un environnement de projet classique, si tests/weather/test_data existe :
    # path = os.path.join(base, "test_data", filename)
    path = os.path.join(os.path.dirname(base), "test_data", filename)
    if not os.path.exists(path):
        # Fallback au cas où le chemin est incorrect
        path = os.path.join(base, "test_data", filename)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.asyncio  # Décorateur pour exécuter la classe de tests en asynchrone
class TestOpenWeatherClientOffline:

    def setup_method(self):
        """Initialisation du client avec une API Key factice"""
        self.client = OpenWeatherClient(api_key="FAKE_KEY")
        # On remplace l'objet http.get synchrone (lambda) par un AsyncMock

    async def test_get_lat_lon_by_city_name(self):
        """Test résolution city -> lat/lon (asynchrone)"""
        mock_geo = [{"lat": 48.8566, "lon": 2.3522}]

        # Le mock doit être un AsyncMock pour simuler le retour d'une coroutine
        self.client.http.get = AsyncMock(return_value=mock_geo)

        # L'appel doit être awaité
        lat, lon = await self.client.get_lat_lon_by_city_name("Paris")

        assert lat == 48.8566
        assert lon == 2.3522
        # Vérification que la méthode mockée a été appelée
        self.client.http.get.assert_called_once()

    async def test_get_current_weather(self):
        """Test météo actuelle avec mock (asynchrone)"""
        mock_geo = [{"lat": 48.8566, "lon": 2.3522}]

        # Si vous utilisez un `try/except` pour le load_json, assurez-vous qu'il réussisse
        mock_weather = load_json("current_weather_Paris.json")

        # 1. Mock de la méthode de géocodage qui est maintenant ASYNCHRONE
        self.client.get_lat_lon_by_city_name = AsyncMock(
            return_value=(mock_geo[0]["lat"], mock_geo[0]["lon"])
        )

        # 2. Mock de la méthode HTTP GET
        self.client.http.get = AsyncMock(return_value=mock_weather)

        # L'appel doit être awaité
        result = await self.client.get_current_weather(city="Paris")

        assert result["weather"][0]["description"] == "nuageux"
        assert "temp" in result["main"]
        self.client.get_lat_lon_by_city_name.assert_called_once()
        self.client.http.get.assert_called_once()

    async def test_get_forecast(self):
        """Test prévisions 5 jours / 3h avec mock (asynchrone)"""
        mock_geo = [{"lat": 48.8566, "lon": 2.3522}]
        mock_forecast = load_json("forecast_Paris.json")

        self.client.get_lat_lon_by_city_name = AsyncMock(
            return_value=(mock_geo[0]["lat"], mock_geo[0]["lon"])
        )
        self.client.http.get = AsyncMock(return_value=mock_forecast)

        # L'appel doit être awaité
        result = await self.client.get_forecast(city="Paris")

        assert "list" in result
        assert len(result["list"]) > 0
        assert "dt_txt" in result["list"][0]
        assert "main" in result["list"][0]
        self.client.http.get.assert_called_once()

    async def test_get_air_pollution(self):
        """Test qualité de l'air avec mock (asynchrone)"""
        mock_geo = [{"lat": 48.8566, "lon": 2.3522}]
        mock_air = load_json("air_pollution_Paris.json")

        self.client.get_lat_lon_by_city_name = AsyncMock(
            return_value=(mock_geo[0]["lat"], mock_geo[0]["lon"])
        )
        self.client.http.get = AsyncMock(return_value=mock_air)

        # L'appel doit être awaité
        result = await self.client.get_air_pollution(city="Paris")

        assert "list" in result
        assert result["list"][0]["main"]["aqi"] in [1, 2, 3, 4, 5]
        assert "components" in result["list"][0]
        self.client.http.get.assert_called_once()

    async def test_get_city_by_lat_lon(self):
        """Test lat/lon -> city mock (asynchrone)"""
        mock_reverse_geo = [{"name": "Paris", "country": "FR"}]  # Ajout du pays pour la cohérence
        self.client.http.get = AsyncMock(return_value=mock_reverse_geo)

        # L'appel doit être awaité
        city_name, country_code = await self.client.reverse_geocode(lat=48.8566, lon=2.3522)

        assert city_name == "Paris"
        assert country_code == "FR"
        self.client.http.get.assert_called_once()
