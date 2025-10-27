from pydantic import BaseModel
from datetime import datetime


# --- Schéma pour AirPollution ---
# Utilise alias=True pour permettre le mapping depuis des clés
# comme 'pm2_5' (qui ne sont pas des noms de variables valides)
# Bien que Pydantic v2 gère cela, utiliser des noms valides est plus propre.

class AirPollutionComponents(BaseModel):
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


class AirPollutionCreate(BaseModel):
    """Schéma pour la création d'un enregistrement de pollution"""
    aqi: int
    components: AirPollutionComponents


# --- Schéma pour WeatherRecord ---

class WeatherRecordCreate(BaseModel):
    """
    Schéma Pydantic (DTO) utilisé pour valider les données
    AVANT de les envoyer à la couche CRUD.
    """
    location_name: str
    lat: float | None = None
    lon: float | None = None

    # Données de la météo actuelle
    measure_timestamp: datetime  # Doit être un objet datetime
    current_temp: float
    feels_like: float
    humidity: int
    wind_speed: float
    description: str

    # Relation (optionnelle)
    air_pollution: AirPollutionCreate | None = None

