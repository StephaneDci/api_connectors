from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List


# --- Schéma pour AirPollution ---
# Utilise alias=True pour permettre le mapping depuis des clés
# comme 'pm2_5' (qui ne sont pas des noms de variables valides)
# Bien que Pydantic v2 gère cela, utiliser des noms valides est plus propre.

# --- Schéma pour Persistance en Database ---

class AirPollutionComponentsModel(BaseModel):
    """Composants détaillés de la pollution de l'air"""
    co: float       = Field(..., description="Сoncentration of CO (Carbon monoxide), μg/m3")
    no: float       = Field(..., description="Сoncentration of NO (Nitrogen monoxide), μg/m3")
    no2: float      = Field(..., description="Сoncentration of NO2 (Nitrogen dioxide), μg/m3")
    o3: float       = Field(..., description="Сoncentration of O3 (Ozone), μg/m3")
    so2: float      = Field(..., description="Сoncentration of SO2 (Sulphur dioxide), μg/m3")
    pm2_5: float    = Field(..., description="Сoncentration of PM2.5 (Fine particles matter), μg/m3")
    pm10: float     = Field(..., description="Сoncentration of PM10 (Coarse particulate matter), μg/m3")
    nh3: float      = Field(..., description="Сoncentration of NH3 (Ammonia), μg/m3")

    model_config = ConfigDict(from_attributes=True)  # <-- C'est ce qui remplace orm_mode


class AirPollutionModel(BaseModel):
    """Schéma pour la création d'un enregistrement de pollution"""
    aqi: int = Field(..., description=" Air Quality Index. Possible values: 1, 2, 3, 4, 5. "
                                      "Where 1 = Good, 2 = Fair, 3 = Moderate, 4 = Poor, 5 = Very Poor.")
    components: AirPollutionComponentsModel  = Field(..., description="Composés organiques")


class WeatherRecordDBModel(BaseModel):
    """
    Schéma Pydantic utilisé pour valider les données pour la peristance en Base de données (ORM)
    """
    location_name: str      = Field(..., description="Localisation de la mesure")
    lat: float              = Field(..., description="lattitude")
    lon: float              = Field(..., description="longitude")

    # Données de la météo actuelle
    measure_timestamp: datetime  # Doit être un objet datetime
    current_temp: float     = Field(..., description="Temperature en Celsius.")
    feels_like: float       = Field(..., description="Temperature ressentie en Celsius.")
    humidity: int           = Field(..., description="Valeur de l'humidité (%).")
    wind_speed: float       = Field(..., description="Vitesse du vent (m/s).")
    description: str        = Field(..., description="Courte description de la météo.")
    sunrise_time: str       = Field(None, description="Heure locale du lever du soleil (HH:MM:SS).")
    sunset_time: str        = Field(None, description="Heure locale du coucher du soleil (HH:MM:SS).")

    # Relation (optionnelle)
    air_pollution: AirPollutionModel | None = None


# --- Schéma pour Report API ---


class LocationModel(BaseModel):
    """Modèle pour les informations de localisation."""
    city: str               = Field(..., description="Ville (ex Paris, Rome, ...")
    country: str            = Field(..., description="code Pays (ex FR, IT)")
    lat: Optional[float]    = Field(None, description="lattitude")
    lon: Optional[float]    = Field(None, description="longitude")


class ForecastItemModel(BaseModel):
    """Modèle pour un élément de prévision."""
    datetime: str       = Field(..., description="Timestamp de la prévision du forecast (AAAA-MM-JJ HH:MM:SS).")
    description: str    = Field(..., description="Courte description de la météo.")
    temperature: float  = Field(..., description="Température pour le forecast en Celcius.")
    humidite: float     = Field(..., description="Humidité en % pour le forecast")


class WeatherBodyModel(BaseModel):

    measure_timestamp: datetime = Field(..., description="Date de la mesure (objet datetime)")
    current_temp: float         = Field(..., description="Temperature en Celsius.")
    feels_like: float           = Field(..., description="Temperature ressentie en Celsius.")
    humidity: int               = Field(..., description="Valeur de l'humidité (%).")
    wind_speed: float           = Field(..., description="Vitesse du vent (m/s).")
    description: str            = Field(..., description="Courte description de la météo.")
    sunrise_time: str           = Field(None, description="Heure locale du lever du soleil (HH:MM:SS).")
    sunset_time: str            = Field(None, description="Heure locale du coucher du soleil (HH:MM:SS).")


class WeatherReportModel(BaseModel):
    """Modèle de la réponse complète de l'API."""
    location: LocationModel                     = Field(..., description="Localisation du rapport météo")
    current_weather: WeatherBodyModel           = Field(..., description="Rapport météo")
    forecast: List[ForecastItemModel]           = Field(None, description="Prévisions météos par tranche de 3h")
    air_pollution: Optional[AirPollutionModel]  = Field(None, description="Modèle de pollution")