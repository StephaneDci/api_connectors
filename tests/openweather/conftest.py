import pytest
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator
from pytest_asyncio import fixture as async_fixture
from fastapi.testclient import TestClient

# Imports pour les dépendances de FastAPI
from api_connectors.openweather.api_server import app, get_db_session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from api_connectors.openweather_database.database import Base

# Définition de la base de données de test en mémoire
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


# --- Fixture 'client' (Synchrone) et 'async_client' (Asynchrone) ---

@pytest.fixture
def client():
    """Crée un client synchrone pour tester l'application FastAPI."""
    return TestClient(app)


@async_fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Crée un client asynchrone pour l'application FastAPI."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# --- Fixtures de Base de Données ---

@async_fixture(scope="session")
async def async_engine():
    """Crée un moteur de base de données asynchrone pour la session de test."""
    engine = create_async_engine(TEST_DB_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@async_fixture
async def setup_db(async_engine):
    """Garantit que l'engine est prêt (Dépendance de session)."""
    yield


@pytest.fixture
def TestingSessionLocal(async_engine):
    """Retourne une factory de session configurée pour le moteur de test."""
    # La factory est retournée, pas une session
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


# --- NOUVELLE FIXTURE : OVERRIDE DE DEPENDANCE DB ---

@pytest.fixture
def override_db_dependency(TestingSessionLocal):
    """
    Fixture qui remplace la dépendance de session DB par une session utilisant
    le moteur de base de données de test en mémoire.
    """

    async def override_get_db_session():
        """Générateur qui fournit une session de test."""
        async with TestingSessionLocal() as session:
            try:
                yield session
            finally:
                # Dans un environnement de test, on ne fait pas de commit ici,
                # car le commit est géré par la route POST elle-même.
                # On s'assure juste de la fermer.
                await session.close()

                # Applique le remplacement

    app.dependency_overrides[get_db_session] = override_get_db_session

    # Exécute le test
    yield

    # Rétablit l'original
    app.dependency_overrides.pop(get_db_session)
