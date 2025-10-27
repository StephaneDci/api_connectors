# tests/weather/test_openweather_client.py

import pytest
import json
import os
from api_connectors.openweather.api_client import OpenWeatherClient

def load_json(filename):
    """Charge un fichier JSON depuis tests/weather/data/"""
    base = os.path.dirname(__file__)
    path = os.path.join(base, "test_data", filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestOpenWeatherClientOffline:

    def setup_method(self):
        """Initialisation du client avec une API Key factice"""
        self.client = OpenWeatherClient(api_key="FAKE_KEY")

    def test_get_lat_lon_by_city_name(self):
        """Test résolution city -> lat/lon"""
        # mock du JSON renvoyé par l'API géocoding
        mock_geo = [{"lat": 48.8566, "lon": 2.3522}]
        self.client.http.get = lambda url, params=None: mock_geo

        lat, lon = self.client.get_lat_lon_by_city_name("Paris")
        assert lat == 48.8566
        assert lon == 2.3522

    def test_get_current_weather(self):
        """Test météo actuelle avec mock"""
        mock_geo = [{"lat": 48.8566, "lon": 2.3522}]
        mock_weather = load_json("current_weather_paris.json")

        # mock get_lat_lon_by_city_name pour éviter l'appel réel à l'API géocoding
        self.client.get_lat_lon_by_city_name = lambda city, country="FR": (mock_geo[0]["lat"], mock_geo[0]["lon"])
        self.client.http.get = lambda url, params=None: mock_weather

        result = self.client.get_current_weather(city="Paris")
        assert result["weather"][0]["description"] == "nuageux"
        assert "temp" in result["main"]

    def test_get_forecast(self):
        """Test prévisions 5 jours / 3h avec mock"""
        mock_geo = [{"lat": 48.8566, "lon": 2.3522}]
        mock_forecast = load_json("forecast_paris.json")

        self.client.get_lat_lon_by_city_name = lambda city, country="FR": (mock_geo[0]["lat"], mock_geo[0]["lon"])
        self.client.http.get = lambda url, params=None: mock_forecast

        result = self.client.get_forecast(city="Paris")
        assert "list" in result
        assert len(result["list"]) > 0
        assert "dt_txt" in result["list"][0]
        assert "main" in result["list"][0]

    def test_get_air_pollution(self):
        """Test qualité de l'air avec mock"""
        mock_geo = [{"lat": 48.8566, "lon": 2.3522}]
        mock_air = load_json("air_pollution_paris.json")

        self.client.get_lat_lon_by_city_name = lambda city, country="FR": (mock_geo[0]["lat"], mock_geo[0]["lon"])
        self.client.http.get = lambda url, params=None: mock_air

        result = self.client.get_air_pollution(city="Paris")
        assert "list" in result
        assert result["list"][0]["main"]["aqi"] in [1, 2, 3, 4, 5]
        assert "components" in result["list"][0]

    def test_get_city_by_lat_lon(self):
        """Test lat/lon -> city mock"""
        mock_reverse_geo = [{"name": "Paris"}]
        self.client.http.get = lambda url, params=None: mock_reverse_geo

        city = self.client.reverse_geocode(lat=48.8566, lon=2.3522)
        # CORRECTION : Le retour est un tuple (city_name, country_code)
        assert city == ("Paris", None)
