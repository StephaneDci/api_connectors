from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import json

# Importer le client API de rapport
from api_connectors.weather.openweather_report import OpenWeatherReport
# Importer le CRUD
from api_connectors.database import crud
# Importer les schémas
from  api_connectors.database.openweather_schema import WeatherRecordCreate, AirPollutionCreate, AirPollutionComponents


class WeatherService:
    """
    Service pour la logique métier (orchestration).
    Sépare la logique API (api_server) de la logique de persistance (crud).
    """

    @staticmethod
    async def get_and_save_weather_report(
            session: AsyncSession,
            location_name: str,
            forecast_limit: int,
            lat: float | None = None,
            lon: float | None = None,
            include_air_quality: bool = True
    ) -> dict:  # Le service retourne le dict brut pour l'API
        """
        Orchestre la récupération, le mapping complexe et la sauvegarde des données météo.
        """

        # 1. Appel au client API pour les données brutes
        # (On suppose que OpenWeatherReport gère sa propre clé API)
        report_data = await OpenWeatherReport.fetch(
            city=location_name,
            lat=lat,
            lon=lon,
            forecast_limit= forecast_limit,
        )
        print(f"===============================================================")
        print(f"report_data retrieved from fetch()")
        print(json.dumps(report_data, indent=2, ensure_ascii=False))
        print(f"===============================================================")


        # 2. Logique de MAPPING (Dict brut -> Schémas Pydantic)
        # C'est la seule couche qui gère les dictionnaires bruts et
        # les conversions de type.

        try:
            current_weather = report_data.get('data').get("weather", {})
            location = report_data.get("location", {})

            print(f"current_weather")
            print(json.dumps(current_weather, indent=2, ensure_ascii=False))
            print(f"______________")

            print(f"location")
            print(json.dumps(location, indent=2, ensure_ascii=False))
            print(f"______________")

            # 2a. Mapper les données météo principales
            weather_schema_data = WeatherRecordCreate(
                location_name=location.get("city"),
                location_country=location.get("country"),
                lat=location.get("lat"),
                lon=location.get("lon"),

                # Conversion du timestamp UNIX en objet datetime
                measure_timestamp=datetime.fromtimestamp(current_weather.get("dt")),

                # Accès sécurisé aux données nichées
                current_temp=current_weather.get("temperature", {}),
                feels_like=current_weather.get("ressenti", {}),
                humidity=current_weather.get("humidite", {}),
                wind_speed=current_weather.get("vitesse_vent", {}),
                description=current_weather.get("description", ["N/A"]),
            )

            print(f"weather_schema_data")
            print(weather_schema_data)
            print(f"______________")

            # 2b. Mapper les données de pollution (si demandées et présentes)
            if include_air_quality and "air_pollution" in report_data:
                air_data = report_data.get("air_pollution", {})
                components_data = air_data.get("components", {})

                # Création des schémas de pollution
                air_components_schema = AirPollutionComponents(
                    co=components_data.get("co"),
                    no=components_data.get("no"),
                    no2=components_data.get("no2"),
                    o3=components_data.get("o3"),
                    so2=components_data.get("so2"),
                    pm2_5=components_data.get("pm2_5"),  # Clé JSON = Nom Pydantic
                    pm10=components_data.get("pm10"),
                    nh3=components_data.get("nh3"),
                )

                air_pollution_schema = AirPollutionCreate(
                    aqi=air_data.get("aqi"),
                    components=air_components_schema
                )

                print("3")

                # Lier le schéma de pollution au schéma météo
                weather_schema_data.air_pollution = air_pollution_schema

        except (KeyError, TypeError, IndexError, AttributeError, ValueError) as e:
            # Gérer une erreur de mapping si les données de l'API sont invalides
            # Idéalement, logguer l'erreur ici
            # logger.error(f"Erreur de mapping des données OpenWeather: {e}")
            raise ValueError(f"Erreur lors du mapping des données de l'API externe: {e}")


        # 3. Appel au CRUD avec les schémas Pydantic validés
        # Nous passons l'objet Pydantic, pas un dictionnaire.
        await crud.create_weather_record(
            session=session,
            record_data=weather_schema_data
        )

        # 4. Retourner les données brutes à l'API Server
        # (L'API Server est responsable du formatage final pour l'utilisateur)
        return report_data

