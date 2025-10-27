import asyncio
import json
from api_connectors.weather.openweather_report import OpenWeatherReport

async def main():


    lat = 48.8566
    lon = 2.3522
    print(f"\n⏳ Récupération asynchrone des données pour {lat}-{lon} (Paris)...\n")

    data = await OpenWeatherReport.fetch(
        lat = lat,
        lon = lon,
        forecast_limit=5
    )

    print(json.dumps(data, indent=2, ensure_ascii=False))

"""    
    city = input("🌍 Entrez le nom de la ville : ").strip()
    country = input("🏳️ Entrez le code du pays (ex: FR, US, JP) [FR par défaut] : ").strip() or "FR"

    print(f"\n⏳ Récupération asynchrone des données pour {city}-{country}...\n")

    data = await OpenWeatherReport.fetch(
        city=city,
        country=country,
        api_key=API_KEY,
        forecast_limit=5
    )

    print(json.dumps(data, indent=2, ensure_ascii=False))
"""


# --- Lancement compatible notebooks / PyCharm ---
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = None

if loop and loop.is_running():
    import nest_asyncio
    nest_asyncio.apply()  # permet d'emboîter les loops
    asyncio.create_task(main())
else:
    asyncio.run(main())
