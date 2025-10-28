import json
import os
from api_connectors.openweather.openweather_client import OpenWeatherClient

client = OpenWeatherClient(api_key=os.getenv("OPENWEATHER_API_KEY"))

CITY = "Paris"
OUTPUT_DIR = ""
os.makedirs(OUTPUT_DIR, exist_ok=True)

samples = {
    "current_weather_paris.json": client.get_current_weather(city=CITY),
    "forecast_paris.json": client.get_forecast(city=CITY),
    "air_pollution_paris.json": client.get_air_pollution(city=CITY),
}

for filename, data in samples.items():
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved {path}")