from sqlalchemy.ext.asyncio import AsyncSession
import json
from api_connectors.core.logger import get_logger
from api_connectors.openweather.report import OpenWeatherReport
from api_connectors.openweather_database import crud
from api_connectors.openweather.schema import *


log = get_logger(__name__)


class WeatherService:
    """
    Service pour la logique métier:
    Sépare la logique API (api_server) de la logique de persistance (crud).
    Permet de valider les modèles de données et la présentation
    """

    # ------Méthode Post

    @staticmethod
    async def save_weather_report(
            session: AsyncSession,
            weather_report: WeatherReportModel
    ) -> WeatherRecordDBModel:
        """
        Persistance d'un rapport
        :param session: Session pour persistance
        :param weather_report: rapport météo a enregistrer
        :return: le record
        """

        # Initialisation de record Database à partir du report API
        weather_record = WeatherRecordDBModel(
            location_name = weather_report.location.city + "," + weather_report.location.country,   # ex: "Paris,FR"
            lat = weather_report.location.lat,
            lon = weather_report.location.lon,
            measure_timestamp = weather_report.current_weather.measure_timestamp,
            current_temp = weather_report.current_weather.current_temp,
            feels_like = weather_report.current_weather.feels_like,
            humidity =  weather_report.current_weather.humidity,
            wind_speed =  weather_report.current_weather.wind_speed,
            description =  weather_report.current_weather.description,
            sunrise_time = weather_report.current_weather.sunrise_time,
            sunset_time = weather_report.current_weather.sunset_time,
            air_pollution = weather_report.air_pollution
        )

        # Appel au CRUD avec les schémas Pydantic validés
        await crud.create_weather_record(
            session=session,
            record_data=weather_record
        )

        return weather_record


#------Méthode Get

    @staticmethod
    async def get_weather_report(
            location_name: str,
            include_air_quality: bool = True
    ) -> WeatherReportModel:
        """
        Orchestre la récupération et le mapping des données météos.
        :param location_name: paramètre fournit par le user (ex: Paris,FR)
        :param include_air_quality: bool
        :return: le rapport météo validé par le schéma WeatherReportModel
        """

        # 1. Split de location name en city et country
        location = location_name.split(",")
        city = location[0]
        country = location[1]

        # 1. Appel au client API pour récupérer les données brutes
        r = OpenWeatherReport()
        report_data = await r.fetch_all_async(
            city=city,
            country = country
        )

        log.info(json.dumps(report_data, indent=2, ensure_ascii=False))

        # 2. Logique de MAPPING (Dict brut -> Schémas Pydantic)
        # C'est la  couche qui gère les dictionnaires bruts et les conversions de type.

        try:
            # a) Mapping des données de la localisation
            location = report_data.get("location", {})

            location_schema_data = LocationModel(
                city=location.get("city"),
                country=location.get("country"),
                lat=location.get("lat"),
                lon=location.get("lon"),
            )

            # b) Mapping des données des prévisions
            forecast_items = report_data.get("data").get("forecast")
            forecast_models = [ForecastItemModel(**item) for item in forecast_items]

            # c) Mapping des données Modèle météo
            current_weather = report_data.get('data').get("weather", {})

            weather_body_data = WeatherBodyModel(
                # Conversion du timestamp UNIX en objet datetime
                measure_timestamp=datetime.fromtimestamp(current_weather.get("dt")),
                current_temp=current_weather.get("temperature", {}),
                feels_like=current_weather.get("ressenti", {}),
                humidity=current_weather.get("humidite", {}),
                wind_speed=current_weather.get("vitesse_vent", {}),
                description=current_weather.get("description", ["N/A"]),
                sunrise_time=current_weather.get("lever_soleil"),
                sunset_time=current_weather.get("coucher_soleil"),
            )

            # d) Mapping des données de pollution (si demandées et présentes)
            air_pollution_schema = {}

            if include_air_quality and report_data.get('data').get('air_pollution'):
                air_data = report_data.get('data').get('air_pollution', {})
                components_data = air_data.get("components", {})

                # Création des schémas de pollution
                air_components_schema = AirPollutionComponentsModel(
                    co=components_data.get("co"),
                    no=components_data.get("no"),
                    no2=components_data.get("no2"),
                    o3=components_data.get("o3"),
                    so2=components_data.get("so2"),
                    pm2_5=components_data.get("pm2_5"),  # Clé JSON = Nom Pydantic
                    pm10=components_data.get("pm10"),
                    nh3=components_data.get("nh3"),
                )

                air_pollution_schema = AirPollutionModel(
                    aqi=air_data.get("aqi"),
                    components=air_components_schema
                )

            # Mapping final du Rapport Météo
            weather_report = WeatherReportModel(
                location = location_schema_data,
                current_weather = weather_body_data,
                forecast = forecast_models,
                air_pollution = air_pollution_schema
            )

            log.info(f"weather_report: {weather_report}")

        except (KeyError, TypeError, IndexError, AttributeError, ValueError) as e:
            # Gérer une erreur de mapping si les données de l'API sont invalides
            # logger.error(f"Erreur de mapping des données OpenWeather: {e}")
            raise ValueError(f"Erreur lors du mapping des données de l'API externe: {e}")

        # 4. Retourner les données mises en forme à l'API Server
        return weather_report
