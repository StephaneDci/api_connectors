import json
import os
import asyncio
from api_connectors.openweather.api_client import OpenWeatherClient

# Assurez-vous que la variable d'environnement OPENWEATHER_API_KEY est définie
client = OpenWeatherClient(api_key=os.getenv("OPENWEATHER_API_KEY"))

CITY = "Rome"
COUNTRY = "IT"

# L'OUTPUT_DIR doit être le chemin exact où vous voulez stocker vos mocks
# Pour la cohérence des tests précédents, il est probable que ce soit :
OUTPUT_DIR = "./tests/openweather/test_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def generate_tests_files():
    """Fonction asynchrone qui effectue les appels API."""
    print(f"🌍 Starting API calls for {CITY}, {COUNTRY}...")

    # Utilisez asyncio.gather pour lancer les trois appels en parallèle
    current_weather, forecast, air_pollution = await asyncio.gather(
        client.get_current_weather(city=CITY, country=COUNTRY),
        client.get_forecast(city=CITY, country=COUNTRY),
        client.get_air_pollution(city=CITY, country=COUNTRY),
    )

    samples = {
        f"current_weather_{CITY}.json": current_weather,
        f"forecast_{CITY}.json": forecast,
        f"air_pollution_{CITY}.json": air_pollution,
    }

    print(samples)

    for filename, data in samples.items():
        path = os.path.join(OUTPUT_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {path}")


if __name__ == "__main__":
    # <--  Exécute la fonction asynchrone dans la boucle d'événements
    asyncio.run(generate_tests_files())