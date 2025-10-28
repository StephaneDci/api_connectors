# Fichier: api_connectors/openweather/api_server.py

import logging
from fastapi import FastAPI, Depends, HTTPException, Query           # Import de la partie API
from sqlalchemy.ext.asyncio import AsyncSession                      # Import de la persistance
# Imports de la logique de l'application et des modèles (ORM / API)
from api_connectors.openweather_database.database import init_db, get_db_session
from api_connectors.openweather.service import WeatherService
from api_connectors.openweather.schema import WeatherReportModel, WeatherRecordDBModel


# --- Initialisation de l'application FastAPI ---

app = FastAPI(
    title="API Connectors - Weather Service",
    description="Service pour récupérer les données météo et qualité de l'air.",
    version="0.2.0"
)


# --- Gestion des Événements de l'Application ---

@app.on_event("startup")
async def startup_event():
    """Initialise la connexion à la base de données au démarrage de l'application."""
    await init_db()
    print("INFO: Initialisation de la base de données terminée.")


# --- Endpoint GET de l'API (Utilise le Service / Récupération Sans la persistance) ---

@app.get("/weather/", response_model=WeatherReportModel, summary="Génère le rapport Météo.")
async def get_weather_report(
        location: str = Query(None, description="format attendu: 'Ville,CodePays' (ex: 'Paris,FR' ou 'Rome,IT')"),
):
    """
    Récupère les données météo actuelles pour une localisation donnée SANS les enregistrer en base.
    """
    try:
        # On utilise le service pour obtenir le rapport
        weather_report = await WeatherService.get_weather_report(location_name=location)
        return weather_report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des données météo: {e}")


# --- Endpoint POST de l'API (Persistance en base de données d'un rapport.) ---

@app.post("/weather/", response_model=WeatherRecordDBModel, summary="Enregistre un rapport météo." )
async def post_weather_record(
    weather_report: WeatherReportModel,                  # Rapport à presister
    session: AsyncSession = Depends(get_db_session)      # Injection de la dépendance de session DB
):
    try:
        logging.info(f"Rapport a enregistrer: {weather_report}")

        # Délègue la logique métier (validation schéma, persistance) au service
        weather_record = await WeatherService.save_weather_report(
            session=session,
            weather_report=weather_report
        )

        if weather_record is None:
            raise HTTPException(status_code=500, detail=f"Echec de la persistance")

        return weather_record

    except HTTPException:
        raise                   # Renvoyer les exceptions HTTP sans les logger ici (FastAPI le gère)
    except Exception as e:
        print(f"ERROR: Une erreur s'est produite lors du traitement de la requête: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur lors de la persistence des données.")
