# Fichier: api_connectors/weather/openweather_service.py

import json
import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from api_connectors.database.crud import create_weather_record
from api_connectors.weather.openweather_report import OpenWeatherReport
from datetime import datetime, timedelta


# --- Fonctions Utilitaires (Déplacées de api_server.py) ---

def convert_unix_to_localtime(timestamp: int, timezone_offset: int) -> str:
    """Convertit un timestamp UNIX UTC en heure locale formatée (HH:MM:SS)."""
    dt_utc = datetime.utcfromtimestamp(timestamp)
    # # Ajouter le décalage (offset) de fuseau horaire
    dt_local = dt_utc + timedelta(seconds=timezone_offset)
    return dt_local.strftime('%H:%M:%S')


def map_weather_data(data: Dict[str, Any], timezone_offset: int) -> Dict[str, Any]:
    """
    Mappe les clés de données brutes vers les clés Pydantic attendues
    et convertit les timestamps.
    """
    if not data:
        print("map_weather_data NO DATA")
        return {}



    # Clés principales
    mapped_data = {
        'temperature': data.get('temperature'),
        'description': data.get('description'),
        'humidite': data.get('humidite'),
        'vitesse_vent': data.get('vitesse_vent'),
    }


    # Conversion des timestamps pour la météo actuelle
    if 'sunrise' in data and 'sunset' in data:
        mapped_data['sunrise_time'] = convert_unix_to_localtime(data['lever_soleil'], timezone_offset)
        mapped_data['sunset_time'] = convert_unix_to_localtime(data['coucher_soleil'], timezone_offset)

    # Gestion des autres champs (lat, lon, etc.)
    if 'lat' in data: mapped_data['lat'] = data.get('lat')
    if 'lon' in data: mapped_data['lon'] = data.get('lon')

    # Le reste du mapping des prévisions et autres champs peut être complexe
    # et sera traité plus tard. Pour l'instant, nous nous concentrons sur le corps principal.

    return mapped_data


class WeatherService:
    """
    Service de gestion des données météo.
    Encapsule l'appel à l'API externe et la persistance en base de données.
    """

    @staticmethod
    async def get_and_save_weather_report(
            session: AsyncSession,
            location_name: str,
            forecast_limit: int,
            include_air_quality: bool
    ) -> Dict[str, Any]:
        """
        Récupère les données météo, les enregistre dans la base de données,
        et retourne la réponse formatée pour l'API.
        """
        print(f"Début de requête météo pour la Location: {location_name}")

        # 1. Appel au client API pour les données
        report_data = await OpenWeatherReport.fetch(
            city=location_name,
            forecast_limit=forecast_limit,
        )

        if not report_data:
            return None  # Laisse l'API lever l'exception 404

        # Les données de timezone sont utilisées pour la conversion du lever/coucher du soleil
        timezone_offset = report_data.get('timezone', 0)

        print(f"report_data")
        print(json.dumps(report_data, indent=2, ensure_ascii=False))

        # 2. Mappage des données météo actuelles
        mapped_current_weather = map_weather_data(report_data.get('data').get('weather', {}), timezone_offset)

        logging.info(f"mapped_current_weather: {mapped_current_weather}")

        # Préparation des données de localisation
        location_data = {
            'city': report_data.get('location', {}).get('city', location_name.split(',')[0]),
            'country': report_data.get('location', {}).get('country', location_name.split(',')[-1]),
            'lat': report_data.get('location', {}).get('lat'),
            'lon': report_data.get('location', {}).get('lon'),
        }

        logging.info(f"location_data: {location_data}")


        # 3. Préparation et Enregistrement dans la base de données

        # Data for WeatherRecord
        weather_record_data = {
            "location_name": location_data['city'],
            "country_code": location_data['country'],
            "latitude": location_data['lat'],
            "longitude": location_data['lon'],
            "measure_timestamp": report_data.get('data').get('weather').get('dt'),
            "temperature": mapped_current_weather['temperature'],
            "description": mapped_current_weather['description'],
            "humidite": mapped_current_weather['humidite'],
            "vitesse_vent": mapped_current_weather['vitesse_vent'],
            "lever_soleil": report_data.get('data').get('weather', {}).get('lever_soleil'),
            "coucher_soleil": report_data.get('data').get('weather', {}).get('coucher_soleil'),
        }

        logging.info(f"weather_record_data: {weather_record_data}")


        # Data for AirPollutionRecord (if available)
        air_pollution_data = None
        if include_air_quality and report_data.get('air_pollution'):
            print("Récupération Air Quality")
            aq_data = report_data['air_pollution']
            print(f"aq_data: {aq_data}")
            air_pollution_data = {
                "aqi": aq_data.get('aqi'),
                "co": aq_data.get('components', {}).get('co'),
                "no": aq_data.get('components', {}).get('no'),
                "no2": aq_data.get('components', {}).get('no2'),
                "o3": aq_data.get('components', {}).get('o3'),
                "so2": aq_data.get('components', {}).get('so2'),
                "pm2_5": aq_data.get('components', {}).get('pm2_5'),
                "pm10": aq_data.get('components', {}).get('pm10'),
                "nh3": aq_data.get('components', {}).get('nh3'),
            }

        print(f"air_pollution_data: {air_pollution_data}")


        await create_weather_record(
            session=session,
            weather_data=weather_record_data,
            air_pollution_data=air_pollution_data
        )


        return report_data
