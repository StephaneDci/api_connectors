# api_connectors/weather/openweather_report.py
import asyncio
import time
from typing import Optional, Dict, Any

from dotenv import load_dotenv, dotenv_values

from .openweather_client import OpenWeatherClient
from api_connectors.core.logger import get_logger
from api_connectors.core.utils import convert_unix_to_localtime

logger = get_logger(__name__)


class OpenWeatherReport:
    """
    Agrégateur de données OpenWeather.
    Fournit :
      - instance.fetch_all_async(...)  -> asynchrone, parallélise les appels
      - instance.fetch_all(...)        -> wrapper synchrone (utilise asyncio.run)
      - OpenWeatherReport.fetch(...)   -> méthode de classe pratique (factory)
    """

    def __init__(self, client: Optional[OpenWeatherClient] = None, api_key: Optional[str] = None, country: str = "FR"):
        if client is None:
            if not api_key:
                raise ValueError("Provide either an OpenWeatherClient or an api_key.")
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

        # Charger les variables d'environnement dès l'importation du module
        load_dotenv()
        api_key = dotenv_values().get("OPENWEATHER_API_KEY")
        if not api_key:
            raise ValueError("OPENWEATHER_API_KEY is not set in environment variables.")

        if city and (lat is not None or lon is not None):
            raise ValueError("Fournir soit `city` (et éventuellement `country`), soit `lat`/`lon`, mais pas les deux.")
        if not city and (lat is None or lon is None):
            raise ValueError("Vous devez fournir soit `city`, soit `lat` ET `lon`.")

        client = OpenWeatherClient(api_key=api_key, country=country or "FR")

        inst = cls(client)
        return await inst.fetch_all_async(city=city, country=country, lat=lat, lon=lon, **kwargs)

    @classmethod
    def from_api_key(cls, api_key: str, country: str = "FR"):
        """Compatibilité: crée un report directement depuis api_key"""
        client = OpenWeatherClient(api_key=api_key, country=country)
        return cls(client)

    # -------- Méthodes de filtrage --------
    def _filter_current_weather(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "description": data["weather"][0]["description"],
            "temperature": data["main"]["temp"],
            "ressenti": data["main"]["feels_like"],
            "humidite": data["main"]["humidity"],
            "vitesse_vent": data["wind"].get("speed"),
            "lever_soleil": convert_unix_to_localtime(data["sys"].get("sunrise"), data.get("timezone")),
            "coucher_soleil": convert_unix_to_localtime(data["sys"].get("sunset"), data.get("timezone")),
            "dt" : data["dt"],
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

    # -------- Partie asynchrone --------
    async def _call_in_thread(self, func, *args, **kwargs):
        """
        Exécute une méthode synchrone dans un thread pool ; supporte kwargs.
        """
        logger.debug("Lancement en thread: %s args=%s kwargs=%s", getattr(func, "__name__", str(func)), args, kwargs)
        return await asyncio.to_thread(func, *args, **kwargs)

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
            tasks.append(self._call_in_thread(self.client.get_current_weather, city=city, country=country, lat=lat, lon=lon))
        if include_forecast:
            tasks.append(self._call_in_thread(self.client.get_forecast, city=city, country=country, lat=lat, lon=lon))
        if include_air:
            tasks.append(self._call_in_thread(self.client.get_air_pollution, city=city, country=country, lat=lat, lon=lon))

        if not tasks:
            return {}

        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
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
                resolved_lat, resolved_lon = await self._call_in_thread(self.client.get_lat_lon_by_city_name, city, country)
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
                "fetch_time_s": round(elapsed, 3)
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


