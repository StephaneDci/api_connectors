# api_connectors/openweather/report.py
import asyncio
import time
from typing import Optional, Dict, Any
from datetime import datetime

from dotenv import load_dotenv, dotenv_values

from api_connectors.core.config import OPENWEATHER_API_KEY
from api_connectors.openweather.api_client import OpenWeatherClient
from api_connectors.core.logger import get_logger
from api_connectors.core.utils import convert_unix_to_localtime

logger = get_logger(__name__)


class OpenWeatherReport:
    """
    Agrégateur de données OpenWeather pour générer un rapport Json
    Fournit les méthodes suivantes:
      - instance.fetch_all_async(...)  -> asynchrone, parallélise les appels
      - instance.fetch_all(...)        -> wrapper synchrone (utilise asyncio.run)
      - OpenWeatherReport.fetch(...)   -> méthode de classe pratique (factory)
    Output:
        - Une sortie Json représentant les données aggrégées
    """

    def __init__(self, client: Optional[OpenWeatherClient] = None, api_key: Optional[str] = None, country: str = "FR"):
        if client is None:
            if not api_key:
                client = OpenWeatherClient(api_key=OPENWEATHER_API_KEY, country=country)
            else:
                client = OpenWeatherClient(api_key=api_key, country=country)
        self.client = client


    # -------- Méthode de classe pratique --------
    @classmethod
    async def fetch(cls,
                    city: Optional[str] = None,
                    country: Optional[str] = None,
                    lat: Optional[float] = None,
                    lon: Optional[float] = None,
                    **kwargs
                    ) -> Dict[str, Any]:
        """
        :param city: la ville ( optionnel si on passe les lat/lon)
        :param country: le pays qui correspond à la ville
        :param kwargs: les keywords arguments
        :return: le rapport méteo
        """

        api_key = OPENWEATHER_API_KEY
        if not api_key:
            raise ValueError("OPENWEATHER_API_KEY is not set in environment variables.")

        # Vérification de l'exclusivité des paramètres fournis:
        # Soit les coordonnées lattitude / longitude
        # Soit la ville / pays
        if city and (lat is not None or lon is not None):
            raise ValueError("Fournir soit `city` (et éventuellement `country`), soit `lat`/`lon`, mais pas les deux.")
        if not city and (lat is None or lon is None):
            raise ValueError("Vous devez fournir soit `city`, soit `lat` ET `lon`.")

        client = OpenWeatherClient(api_key=api_key, country=country or "FR")

        inst = cls(client)
        return await inst.fetch_all_async(city=city, country=country, lat=lat, lon=lon, **kwargs)


    # -------- Méthodes de filtrage --------
    def _filter_current_weather(self, data: Dict[str, Any]) -> Dict[str, Any]:

        # Récupérer le décalage horaire en secondes
        timezone_offset = data.get("timezone", 0)

        return {
            "description": data["weather"][0]["description"],
            "temperature": data["main"]["temp"],
            "ressenti": data["main"]["feels_like"],
            "humidite": data["main"]["humidity"],
            "vitesse_vent": data["wind"].get("speed"),
            "lever_soleil": convert_unix_to_localtime(data["sys"].get("sunrise"), timezone_offset),
            "coucher_soleil": convert_unix_to_localtime(data["sys"].get("sunset"), timezone_offset),
            "dt" : data.get("dt")
        }

    def _filter_forecast(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "datetime": item.get("dt_txt"),
            "description": item["weather"][0]["description"],
            "temperature": item["main"]["temp"],
            "humidite": item["main"]["humidity"]
        }

    def _filter_air_pollution(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "aqi": data["list"][0]["main"]["aqi"],
            "components": data["list"][0]["components"]
        }

    # -------- Helpers pour normalisation de la sortie --------
    def _make_location_meta(self, city: Optional[str], country: Optional[str], lat: Optional[float], lon: Optional[float]) -> Dict[str, Any]:
        return {
            "city": city,
            "country": country,
            "lat": lat,
            "lon": lon
        }

    async def fetch_all_async(
        self,
        city: Optional[str] = None,
        country: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        include_weather: bool = True,
        include_forecast: bool = True,
        include_air: bool = True,
        forecast_limit: Optional[int] = 10,
    ) -> Dict[str, Any]:
        """
        Lance en parallèle les appels demandés et renvoie un résultat normalisé.
        """
        # Préparation des tâches selon les flags
        tasks = []
        if include_weather:
            tasks.append(self.client.get_current_weather(city=city, country=country, lat=lat, lon=lon))
        if include_forecast:
            tasks.append(self.client.get_forecast(city=city, country=country, lat=lat, lon=lon))
        if include_air:
            tasks.append(self.client.get_air_pollution(city=city, country=country, lat=lat, lon=lon))

        if not tasks:
            return {}

        start = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.perf_counter() - start
        logger.debug("fetch_all_async completed in %.3fs", elapsed)

        out: Dict[str, Any] = {}
        idx = 0

        # On cherche à enrichir la location (city/country/lat/lon) via reverse geocode si nécessaire.
        # Si l'appel weather/forecast/air renvoi des infos de location, on peut les récupérer ici.
        # Par simplicité, on essaie d'obtenir city/country via reverse_geocode when lat/lon provided.
        # Resolve lat/lon for meta:
        resolved_lat = lat
        resolved_lon = lon
        if (lat is None or lon is None) and city:
            # try to resolve coordinates (sync call executed in thread)
            try:
                resolved_lat, resolved_lon = await self.client.get_lat_lon_by_city_name(city, country)
            except Exception:
                # ignore: meta will be partial
                resolved_lat, resolved_lon = None, None

        if include_weather:
            raw_weather = results[idx]; idx += 1
            out["weather"] = self._filter_current_weather(raw_weather)

        if include_forecast:
            raw_forecast = results[idx]; idx += 1
            forecast_list = raw_forecast.get("list", [])
            if forecast_limit is not None:
                forecast_list = forecast_list[:forecast_limit]
            out["forecast"] = [self._filter_forecast(item) for item in forecast_list]

        if include_air:
            raw_air = results[idx]
            out["air_pollution"] = self._filter_air_pollution(raw_air)

        out_meta = {
            "location": self._make_location_meta(city, country, resolved_lat, resolved_lon),
            "meta": {
                "source": "OpenWeather",
                "fetch_time_s": round(elapsed, 3),
                "timestamp": datetime.now().timestamp()
            }
        }

        return {"data": out, **out_meta}

    # -------- Wrapper synchrone --------
    def fetch_all(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Wrapper synchrone. Attention : si tu appelles depuis une boucle asyncio active,
        tu dois utiliser fetch_all_async() directement.
        """
        return asyncio.run(self.fetch_all_async(*args, **kwargs))


