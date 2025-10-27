import pytest
import json
from unittest.mock import patch, AsyncMock
from api_connectors.weather.openweather_report import OpenWeatherReport

# ---------------- Utilitaire pour charger les fichiers JSON ----------------
def load_json(filename):
    with open(f"./tests/weather/openweather_test_data/{filename}", "r", encoding="utf-8") as f:
        return json.load(f)

# ---------------- Test fetch_async ----------------
@pytest.mark.asyncio
async def test_fetch_async_default_forecast_limit():

    # Charger les données mockées
    current_weather = load_json("current_weather_paris.json")
    forecast = load_json("forecast_paris.json")
    air_pollution = load_json("air_pollution_paris.json")

    # Patch OpenWeatherClient pour ne pas faire de vrai HTTP
    with patch("api_connectors.weather.openweather_report.OpenWeatherClient") as MockClient:
        instance = MockClient.return_value
        instance.get_current_weather.return_value = current_weather
        instance.get_forecast.return_value = forecast
        instance.get_air_pollution.return_value = air_pollution

        result = await OpenWeatherReport.fetch(api_key="FakeKey", city="Paris")

        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Vérifications
        assert "weather" in result["data"]
        assert "forecast" in result["data"]
        assert "air_pollution" in result["data"]
        assert "meta" in result

        assert len(result["data"]["forecast"]) == 10  # par défaut le forecast est limité à 10
        assert  result["data"]["air_pollution"]["aqi"] == 2
        assert result["data"]["weather"]["description"] == "nuageux"


# ---------------- Test fetch_async ----------------
@pytest.mark.asyncio
async def test_fetch_async_parameters():

    # Charger les données mockées
    current_weather = load_json("current_weather_paris.json")
    forecast = load_json("forecast_paris.json")
    air_pollution = load_json("air_pollution_paris.json")

    # Patch OpenWeatherClient pour ne pas faire de vrai HTTP
    with patch("api_connectors.weather.openweather_report.OpenWeatherClient") as MockClient:
        instance = MockClient.return_value
        instance.get_current_weather.return_value = current_weather
        instance.get_forecast.return_value = forecast
        instance.get_air_pollution.return_value = air_pollution

        result = await OpenWeatherReport.fetch(api_key="FAKE", city="Paris")

        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Vérifications
        assert "weather" in result["data"]
        assert "forecast" in result["data"]
        assert "air_pollution" in result["data"]
        assert "meta" in result

        assert len(result["data"]["forecast"]) == 10  # par défaut le forecast est limité à 10
        assert  result["data"]["air_pollution"]["aqi"] == 2
        assert result["data"]["weather"]["description"] == "nuageux"

# ---------------- Test fetch_async avec forecast_limit spécifique ----------------
@pytest.mark.asyncio
async def test_fetch_async_with_forecast_limit():
    city = "Paris"
    api_key = "FAKE_KEY"
    LIMIT = 5

    current_weather = load_json("current_weather_paris.json")
    forecast = load_json("forecast_paris.json")
    air_pollution = load_json("air_pollution_paris.json")

    with patch("api_connectors.weather.openweather_report.OpenWeatherClient") as MockClient:
        instance = MockClient.return_value
        instance.get_current_weather.return_value = current_weather
        instance.get_forecast.return_value = forecast
        instance.get_air_pollution.return_value = air_pollution

        report = OpenWeatherReport(api_key=api_key)
        result = await report.fetch_all_async(city, forecast_limit=LIMIT)

        assert len(result["data"]["forecast"]) == LIMIT


# ---------------- Test fetch sans API key ----------------
@pytest.mark.asyncio
async def test_fetch_missing_api_key():
    with pytest.raises(ValueError):
        await OpenWeatherReport.fetch(city="Paris")


# ---------------- Test fetch avec paramètres erronés ----------------
@pytest.mark.asyncio
async def test_fetch_duplicate_city_and_latlon():
    with pytest.raises(ValueError):
        # On ne doit pas fournir ville ET lat/lon
        await OpenWeatherReport.fetch(api_key="FAKE", city="Paris", lat=1.11, lon=2.22)