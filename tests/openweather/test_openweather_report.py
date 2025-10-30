import pytest
import json
import os
from unittest.mock import patch, AsyncMock
from api_connectors.openweather.report import OpenWeatherReport


# ---------------- Utilitaire pour charger les fichiers JSON ----------------
def load_json(filename):
    """Charge un fichier JSON depuis tests/openweather/test_data/"""

    # Trouver le répertoire courant du fichier de test
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Construction du chemin d'accès au fichier de données
    # Supposant que le répertoire 'test_data' est au même niveau que le fichier de test
    path = os.path.join(base_dir, "test_data", filename)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------- Test fetch_async (Méthodes corrigées pour AsyncMock) ----------------

@pytest.mark.asyncio
async def test_fetch_async_default_forecast_limit():
    # Charger les données mockées
    current_weather = load_json("current_weather_Paris.json")
    forecast = load_json("forecast_Paris.json")
    air_pollution = load_json("air_pollution_Paris.json")

    # Patch OpenWeatherClient pour ne pas faire de vrai HTTP
    with patch("api_connectors.openweather.report.OpenWeatherClient") as MockClient:
        instance = MockClient.return_value

        # CORRECTION : Les méthodes de l'instance doivent être des AsyncMock
        instance.get_current_weather = AsyncMock(return_value=current_weather)
        instance.get_forecast = AsyncMock(return_value=forecast)
        instance.get_air_pollution = AsyncMock(return_value=air_pollution)

        result = await OpenWeatherReport.fetch(city="Paris", country="FR")

        # print(json.dumps(result, indent=2, ensure_ascii=False))

        # Vérifications
        assert "weather" in result["data"]
        assert "forecast" in result["data"]
        assert "air_pollution" in result["data"]
        assert "meta" in result

        assert len(result["data"]["forecast"]) == 10
        # Note: L'assertion 2 doit correspondre à la structure de votre rapport
        # J'ai corrigé l'espace dans l'ancienne assertion: result["data"]["air_pollution"]["aqi"]
        assert result["data"]["air_pollution"]["aqi"] == 2
        assert result["data"]["weather"]["description"] == "nuageux"


@pytest.mark.asyncio
async def test_fetch_async_parameters():
    # Charger les données mockées
    current_weather = load_json("current_weather_Paris.json")
    forecast = load_json("forecast_Paris.json")
    air_pollution = load_json("air_pollution_Paris.json")

    # Patch OpenWeatherClient pour ne pas faire de vrai HTTP
    with patch("api_connectors.openweather.report.OpenWeatherClient") as MockClient:
        instance = MockClient.return_value

        # CORRECTION : Les méthodes de l'instance doivent être des AsyncMock
        instance.get_current_weather = AsyncMock(return_value=current_weather)
        instance.get_forecast = AsyncMock(return_value=forecast)
        instance.get_air_pollution = AsyncMock(return_value=air_pollution)

        result = await OpenWeatherReport.fetch(city="Paris")

        # print(json.dumps(result, indent=2, ensure_ascii=False))

        # Vérifications
        assert "weather" in result["data"]
        assert "forecast" in result["data"]
        assert "air_pollution" in result["data"]
        assert "meta" in result

        assert len(result["data"]["forecast"]) == 10
        assert result["data"]["air_pollution"]["aqi"] == 2
        assert result["data"]["weather"]["description"] == "nuageux"


# ---------------- Test fetch_async avec forecast_limit spécifique ----------------
@pytest.mark.asyncio
async def test_fetch_async_with_forecast_limit():
    city = "Paris"
    api_key = "FAKE_KEY"
    LIMIT = 5

    current_weather = load_json("current_weather_Paris.json")
    forecast = load_json("forecast_Paris.json")
    air_pollution = load_json("air_pollution_Paris.json")

    # Le patch doit englober l'instanciation si l'OpenWeatherClient est instancié à l'intérieur
    with patch("api_connectors.openweather.report.OpenWeatherClient") as MockClient:
        instance = MockClient.return_value

        # CORRECTION : Les méthodes de l'instance doivent être des AsyncMock
        instance.get_current_weather = AsyncMock(return_value=current_weather)
        instance.get_forecast = AsyncMock(return_value=forecast)
        instance.get_air_pollution = AsyncMock(return_value=air_pollution)

        # Instancier le rapport ici
        report = OpenWeatherReport(api_key=api_key)

        # Si 'fetch_all_async' est une méthode d'instance, l'appel est correct
        result = await report.fetch_all_async(city, forecast_limit=LIMIT)

        # Le résultat est un dictionnaire selon les tests précédents, pas OpenWeatherReport
        assert isinstance(result, dict)

        # Les assertions doivent être décommentées pour valider la limite
        # Note : Si le résultat est un objet, vous devez accéder aux attributs autrement
        # Pour l'instant on garde la logique de dictionnaire
        # Si le report.fetch_all_async retourne le rapport mappé (pas le dictionnaire brut),
        # vous devez ajuster l'assertion. Nous gardons l'assertion de longueur pour le test.
        assert len(result["data"]["forecast"]) == LIMIT


# ---------------- Test fetch avec paramètres erronés ----------------
@pytest.mark.asyncio
async def test_fetch_duplicate_city_and_latlon():
    with pytest.raises(ValueError):
        # On ne doit pas fournir ville ET lat/lon
        await OpenWeatherReport.fetch(city="Paris", lat=1.11, lon=2.22)