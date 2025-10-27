# Fichier: api_connectors/openweather/api_server.py

import logging
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
# Imports de la logique de l'application
from api_connectors.openweather_database.database import init_db, get_db_session
from api_connectors.openweather.service import WeatherService


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
    print("INFO: Initialisation de la base de données...")
    await init_db()
    print("INFO: Initialisation de la base de données terminée.")


# --- Endpoint de l'API (Utilise le Service) ---

@app.get(
    "/weather/",
    # Laisser response_model désactivé pour le moment pour éviter les ResponseValidationError
    # response_model=WeatherReport,
    summary="Récupère le rapport météo actuel et la prévision."
)
async def get_weather_report(
    location: Optional[str] = Query(None, description="Ville et pays au format 'Ville,CodePays' (ex: Paris,FR)"),
    lat: Optional[float] = Query(None, description="Latitude (si pas de city, ex: 48,85)"),
    lon: Optional[float] = Query(None, description="Longitude (si pas de city ex: 2.39)"),
    forecast_limit: int = Query(10, description="Nombre de prévisions à inclure (par pas de 3 heures)."),
    include_air_quality: bool = Query(True, description="Inclure les données de qualité de l'air (AQI)."),
    # Injection de la dépendance de session DB
    session: AsyncSession = Depends(get_db_session)
):
    """
    Récupère le rapport météo complet (actuel et prévisions) pour la localisation spécifiée,
    et enregistre les données dans l'historique via le WeatherService.
    """
    try:
        logging.info(f"Location de la requête: {location}")
        print(f"include_air_quality: {include_air_quality}")

        # Délègue toute la logique métier (appel API, validation schéma, persistance) au service
        response_data = await WeatherService.get_and_save_weather_report(
            session=session,
            location_name=location,
            forecast_limit=forecast_limit,
            include_air_quality=include_air_quality
        )

        if response_data is None:
            raise HTTPException(status_code=404, detail=f"Données météo non trouvées pour {location}")

        # Renvoie simplement le résultat du service
        return response_data

    except HTTPException:
        # Renvoyer les exceptions HTTP sans les logger ici (FastAPI le gère)
        raise
    except Exception as e:
        print(f"ERROR: Une erreur s'est produite lors du traitement de la requête: {e}")
        # Renvoyer une erreur 500 générique
        raise HTTPException(status_code=500, detail="Erreur interne du serveur lors de la récupération des données.")
