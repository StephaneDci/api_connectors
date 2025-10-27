# api_connectors/core/config.py
from dotenv import load_dotenv
import os

load_dotenv()  # charge les variables du fichier .env

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not OPENWEATHER_API_KEY:
    raise ValueError("Missing OPENWEATHER_API_KEY in environment variables")
