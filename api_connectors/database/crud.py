from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from api_connectors.database.models import WeatherRecord, AirPollutionRecord
from typing import Dict, Any, Optional


# --- Fonctions de Création ---

async def create_weather_record(
        session: AsyncSession,
        weather_data: Dict[str, Any],
        air_pollution_data: Optional[Dict[str, Any]] = None
) -> WeatherRecord:
    """
    Crée un enregistrement WeatherRecord et, si les données sont disponibles,
    un enregistrement AirPollutionRecord associé dans une seule transaction.

    Args:
        session: La session asynchrone SQLAlchemy.
        weather_data: Dictionnaire contenant les données pour WeatherRecord.
        air_pollution_data: Dictionnaire optionnel contenant les données d'AQI.

    Returns:
        L'objet WeatherRecord créé.
    """

    # 1. Préparation des données météo pour l'enregistrement principal
    # Nous allons créer un dictionnaire qui correspond aux colonnes du modèle WeatherRecord.
    record_data = {
        # Note: 'measure_timestamp' est défini par défaut par le modèle (datetime.utcnow)
        "location_name": weather_data.get("location_name"),
        "lat": weather_data.get("latitude"),
        "lon": weather_data.get("longitude"),
        "measure_timestamp": datetime.fromtimestamp(weather_data.get("measure_timestamp")),
        "current_temp": weather_data.get("temperature", {}),
        "weather_description": weather_data.get("description"),
        "humidity": weather_data.get("humidite", {}),
        "wind_speed": weather_data.get("vitesse_vent", {}),
    }

    print(f"Record data: {record_data}")

    # Création de l'objet WeatherRecord
    db_record = WeatherRecord(**record_data)

    print(f"db_record data: {db_record}")
    session.add(db_record)

    # 2. Gestion de l'enregistrement de la qualité de l'air (optionnel)
    if air_pollution_data and "aqi" in air_pollution_data:
        # Assurez-vous que les clés correspondent aux colonnes AirPollutionRecord
        pollution_components = air_pollution_data.get("components", {})

        pollution_data = {
            "aqi": air_pollution_data["aqi"],
            "co": pollution_components.get("co"),
            "no": pollution_components.get("no"),
            "no2": pollution_components.get("no2"),
            "o3": pollution_components.get("o3"),
            "so2": pollution_components.get("so2"),
            "pm2_5": pollution_components.get("pm2_5"),
            "pm10": pollution_components.get("pm10"),
            "nh3": pollution_components.get("nh3"),
        }

        # Création de l'objet AirPollutionRecord.
        # La clé étrangère sera définie implicitement par SQLAlchemy lors du commit
        db_pollution = AirPollutionRecord(**pollution_data)

        # Lier l'enregistrement de pollution à l'enregistrement météo
        db_pollution.weather_record = db_record
        session.add(db_pollution)

    # 3. Commit de la transaction
    await session.commit()
    await session.refresh(db_record)
    return db_record

# --- Fonctions de Lecture (Lecture) ---

# Vous pouvez ajouter ici des fonctions pour interroger l'historique, par exemple:
# async def get_weather_history_by_location(session: AsyncSession, location: str, limit: int = 10):
#     # Implémentation de la requête utilisant les index pour le tri (ORDER BY)
#     ...
