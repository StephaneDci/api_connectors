# Fichier: api_connectors/openweather/api_server.py

from fastapi import FastAPI, Depends, HTTPException, Query, status   # Import de la partie API
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession                      # Import de la persistance
# Imports de la logique de l'application et des modèles (ORM / API)
from api_connectors.openweather_database.database import init_db, get_db_session
from api_connectors.openweather.service import WeatherService
from api_connectors.openweather.schema import WeatherReportModel, WeatherRecordDBModel

from api_connectors.core.logger import get_logger
log = get_logger(__name__)



# --- Gestion des Événements de l'Application ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gère les événements de démarrage et d'arrêt de l'application (remplace on_event).
    """
    # Événement de Démarrage (Startup)
    await init_db()
    log.info("Initialisation de la base de données terminée.")

    yield # L'application démarre ici

    # Événement d'Arrêt (Shutdown - placez le code ici si nécessaire)
    log.info("L'application s'arrête.")


# --- Initialisation de l'application FastAPI ---

app = FastAPI(
    title="API Connectors - Weather Service",
    description="Service pour récupérer les données météo et qualité de l'air.",
    version="0.2.0",
    lifespan=lifespan
)

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

@app.post("/weather/",
          response_model=WeatherRecordDBModel,
          summary="Enregistre un rapport météo en base.",
          status_code=status.HTTP_201_CREATED)

async def post_weather_record(
    weather_report: WeatherReportModel,                  # Rapport à presister
    session: AsyncSession = Depends(get_db_session)      # Injection de la dépendance de session DB
):
    try:
        log.info(f"Rapport a enregistrer: {weather_report}")

        # Délègue la logique métier (validation schéma, persistance) au service
        weather_record = await WeatherService.save_weather_report(
            session=session,
            weather_report=weather_report
        )

        # 3 - appel du commit explicite pour enregistrement en Base
        if weather_record is not None:
            await session.commit()
        else:
            raise HTTPException(status_code=500, detail=f"Echec de la persistance")

        return weather_record

    except HTTPException:
        raise                   # Renvoyer les exceptions HTTP sans les logger ici (FastAPI le gère)
    except Exception as e:
        log.error(f"Une erreur s'est produite lors du traitement de la requête: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur lors de la persistence des données.")


# --- Endpoint POST pour automatiser la récupération puis l'enregistrement ---

@app.post(
    "/weather/fetch-and-save",
    response_model=WeatherReportModel,  # On retourne le rapport créé
    summary="Récupère le dernier rapport météo pour une localisation et l'enregistre en base.",
    status_code=status.HTTP_201_CREATED)

async def fetch_and_save_weather_report(
        location: str = Query(..., description="format attendu: 'Ville,CodePays' (ex: 'Paris,FR')"),
        session: AsyncSession = Depends(get_db_session)  # Injection de la dépendance de session DB
):
    """
    Ce point d'API automatise la récupération des données de l'API externe
    (OpenWeather) et leur persistance immédiate dans la base de données.
    """
    try:
        # 1. Récupération des données (réutilise la logique du service)
        log.info(f"Récupération et enregistrement automatique du rapport pour: {location}")

        # Le service doit d'abord récupérer le rapport complet
        weather_report = await WeatherService.get_weather_report(location_name=location)

        # 2. Persistance des données (réutilise la logique du service)
        # On passe le rapport complet récupéré à la méthode de sauvegarde
        await WeatherService.save_weather_report(
            session=session,
            weather_report=weather_report  # Utilise le modèle WeatherReportModel
        )

        # 3 - appel du commit explicite pour enregistrement en Base
        if weather_report is not None:
            await session.commit()
        else:
            raise HTTPException(status_code=500, detail=f"Echec de la persistance")

        # 3. Retourne le rapport complet
        return weather_report

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Erreur lors de l'automatisation de l'enregistrement pour {location}: {e}", exc_info=True)
        raise HTTPException(status_code=500,
                            detail="Erreur interne du serveur lors de l'automatisation de la persistance.")