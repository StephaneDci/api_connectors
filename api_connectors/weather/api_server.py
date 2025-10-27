import os
from typing import Optional, List, Dict, Any
from datetime import datetime  # NOUVEAU: Importation pour la conversion de timestamp

from fastapi import FastAPI, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field

# Correction de tous les imports pour utiliser le chemin absolu du package
from api_connectors.weather.openweather_report import OpenWeatherReport


# --- Modèles de Données (Pydantic) ---

class Location(BaseModel):
    city: str
    country: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class CurrentWeather(BaseModel):
    temp: float = Field(..., description="Temperature in Kelvin or Celsius (if converted).")
    description: str = Field(..., description="Short weather description.")
    humidity: int = Field(..., description="Valeur de l'humidité.")
    wind_speed: float = Field(..., description="Valeur du vent.")


class ForecastItem(BaseModel):
    dt: int = Field(..., description="Timestamp of the forecast (UNIX time).")
    temp: float
    description: str


class AirPollution(BaseModel):
    aqi: int = Field(..., description="Air Quality Index (1=Good, 5=Very Poor).")


class WeatherReportResponse(BaseModel):
    """Modèle pour la réponse finale du rapport météo"""
    location: Location
    current_weather: CurrentWeather
    forecast: List[ForecastItem]
    air_pollution: AirPollution

    class Config:
        populate_by_name = True


# --- Initialisation de l'API ---

app = FastAPI(
    title="OpenWeather API Proxy",
    description="API pour obtenir la météo et les prévisions via OpenWeatherMap.",
)


# --- Dépendance pour la Clé API ---

def get_api_key():
    """Récupère la clé API de l'environnement et lève une erreur si absente."""
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La clé API OpenWeather n'est pas configurée dans les variables d'environnement du serveur."
        )
    return api_key


# --- Fonction utilitaire de mapping ---

def map_weather_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Renomme et convertit les clés de la météo pour correspondre au modèle Pydantic.
    """
    if 'temperature' in data:
        data['temp'] = data.pop('temperature')
    if 'datetime' in data:
        # CORRECTION: Convertit la chaîne de date/heure en timestamp UNIX (int)
        dt_str = data.pop('datetime')
        try:
            # Le format: 'YYYY-MM-DD HH:MM:SS'
            dt_object = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
            data['dt'] = int(dt_object.timestamp())
        except ValueError as e:
            # Gère le cas où le format de la date est incorrect.
            print(f"Erreur de format de date pour '{dt_str}': {e}")
            # Si la conversion échoue, nous laissons 'dt' manquant pour que Pydantic signale l'erreur
            # ou vous pouvez la définir à 0 ou None si le champ est Optional
            pass  # Laissez le champ 'dt' manquant ou gérer l'erreur plus haut

    # Renomme 'wind_speed' si votre connecteur l'appelle différemment (non nécessaire ici, mais bonne pratique)
    # Exemple: if 'wind_spd' in data: data['wind_speed'] = data.pop('wind_spd')

    return data


# --- Endpoint de Météo Asynchrone (GET) ---

@app.get(
    "/weather/{city},{country_code}",
    response_model=WeatherReportResponse,
    summary="Obtenir le rapport météo complet pour une ville",
)
async def get_weather_report(
        city: str,
        country_code: Optional[str] = None,
        # CORRECTION ICI: Utilisation de Query pour définir un paramètre d'URL
        forecast_limit: int = Query(10, ge=1, le=50, description="Limite le nombre de prévisions."),
        api_key: str = Depends(get_api_key)
):
    """
    Récupère la météo actuelle, les prévisions et la qualité de l'air pour la ville spécifiée.
    """
    try:
        raw_report = await OpenWeatherReport.fetch(
            city=city,
            country=country_code,
            api_key=api_key
        )

        report_data = raw_report.get("data", {})
        location_data = raw_report.get("location", {})
        current_weather_data = report_data.get("weather", {})
        forecast_list = report_data.get("forecast", [])

        # 1. Mapping pour la météo actuelle
        mapped_current_weather = map_weather_data(current_weather_data)

        # 2. Mapping pour les prévisions
        # La limite est appliquée après le mapping au cas où le mapping échoue
        mapped_forecast = [map_weather_data(item) for item in forecast_list][:forecast_limit]

        response_payload = {
            "location": location_data,
            "current_weather": mapped_current_weather,
            # Appliquer la limite de la prévision
            "forecast": mapped_forecast,
            "air_pollution": report_data.get("air_pollution", {}),
        }

        return response_payload

    except Exception as e:
        detail = str(e)
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        if "404" in detail:
            status_code = status.HTTP_404_NOT_FOUND
            detail = f"Ville non trouvée ou donnée météo indisponible pour {city}."
        elif "401" in detail or "API_KEY" in detail:
            status_code = status.HTTP_401_UNAUTHORIZED
            detail = "Clé API non valide ou non autorisée."

        raise HTTPException(status_code=status_code, detail=detail)


# --- Endpoint de Santé (Health Check) ---

@app.get("/health", summary="Vérification de l'état du service.")
def health_check():
    return {"status": "ok", "service": app.title}
