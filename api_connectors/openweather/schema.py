from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


# --- Schéma pour AirPollution ---
# Utilise alias=True pour permettre le mapping depuis des clés
# comme 'pm2_5' (qui ne sont pas des noms de variables valides)
# Bien que Pydantic v2 gère cela, utiliser des noms valides est plus propre.


class LocationModel(BaseModel):
    """Modèle pour les informations de localisation."""
    city: str   = Field(..., description="Localisation de la mesure, suivie du code Pays (ex Paris,FR ou Rome,IT")
    country: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

class AirPollutionComponentsModel(BaseModel):
    """Composants détaillés de la pollution de l'air"""
    co: float
    no: float
    no2: float
    o3: float
    so2: float
    pm2_5: float  # Nom de champ Pydantic valide
    pm10: float
    nh3: float

    class Config:
        orm_mode = True  # Permet de mapper depuis des objets ORM


class AirPollutionModel(BaseModel):
    """Schéma pour la création d'un enregistrement de pollution"""
    aqi: int = Field(..., description="Air Quality Index (1=Bon, 5=Très mauvais).")
    components: AirPollutionComponentsModel


# --- Schéma pour WeatherRecord ---

class WeatherRecordModel(BaseModel):
    """
    Schéma Pydantic utilisé pour valider les données
    """
    location_name: str
    lat: float | None = None
    lon: float | None = None

    # Données de la météo actuelle
    measure_timestamp: datetime  # Doit être un objet datetime
    current_temp: float = Field(..., description="Temperature en Celsius.")
    feels_like: float = Field(..., description="Temperature ressentie en Celsius.")
    humidity: int = Field(..., description="Valeur de l'humidité (%).")
    wind_speed: float = Field(..., description="Vitesse du vent (m/s).")
    description: str = Field(..., description="Courte description de la météo.")
    sunrise_time: str = Field(None, description="Heure locale du lever du soleil (HH:MM:SS).")
    sunset_time: str = Field(None, description="Heure locale du coucher du soleil (HH:MM:SS).")


    # Relation (optionnelle)
    air_pollution: AirPollutionModel | None = None

class ForecastItemModel(BaseModel):
    """Modèle pour un élément de prévision."""
    dt: int = Field(..., description="Timestamp de la prévision (UNIX time).")
    temp: float  = Field(..., description="Température pour le forecast en Celcius.")
    description: str = Field(..., description="Courte description de la météo.")


class WeatherReportModel(BaseModel):
    """Modèle de la réponse complète de l'API."""
    location: LocationModel
    current_weather: WeatherRecordModel
    forecast: List[ForecastItemModel]
    air_pollution: Optional[AirPollutionModel] = None