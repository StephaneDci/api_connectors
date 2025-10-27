import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase

# --- Configuration de la connexion ---

# L'URL de connexion sera lue à partir des variables d'environnement.
# Exemple : 'postgresql+asyncpg://user:password@host:port/dbname'
# Pour un démarrage simple et asynchrone : 'sqlite+aiosqlite:///openweather_database/weather_data.db'
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///api_connectors/openweather_database/weather_data.db")

# Création du moteur de base de données asynchrone
# 'echo=False' pour ne pas afficher les requêtes SQL en production (à mettre à True en dev)
engine = create_async_engine(DATABASE_URL, echo=False)

# Création d'un constructeur de session asynchrone
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

# --- Base de Déclaration des Modèles ---

# Classe de base pour tous les modèles de table.
class Base(AsyncAttrs, DeclarativeBase):
    pass

# Fonction utilitaire pour créer la structure de la base de données
# Elle doit être appelée au démarrage de l'application FastAPI
async def init_db():
    async with engine.begin() as conn:
        # Créer toutes les tables qui héritent de Base
        # Note: Les modèles doivent être importés avant cet appel pour être reconnus.
        await conn.run_sync(Base.metadata.create_all)

# Fonction utilitaire de dépendance pour FastAPI (Dependency Injection)
# Elle fournit une nouvelle session pour chaque requête d'API
async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session
