# api_connectors/core/config.py

from dotenv import load_dotenv
import os

load_dotenv()

def get_openweather_api_key() -> str:
    key = os.getenv("OPENWEATHER_API_KEY")
    if not key:
        raise RuntimeError("OPENWEATHER_API_KEY manquante. Définir la var d'environnement ou passer en mode mock.")
    return key