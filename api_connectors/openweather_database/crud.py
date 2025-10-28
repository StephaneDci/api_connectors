from sqlalchemy.ext.asyncio import AsyncSession
from .models import WeatherRecord, AirPollutionRecord
from api_connectors.openweather.schema import WeatherRecordModel


async def create_weather_record(session: AsyncSession, record_data: WeatherRecordModel) -> WeatherRecord:
    """
    Crée et sauvegarde un nouvel enregistrement météo et son enregistrement
    de pollution de l'air associé, en utilisant les schémas Pydantic.

    Accepte :
        session (AsyncSession): La session de base de données.
        record_data (WeatherRecordModel): Le schéma Pydantic contenant
                                           les données validées.
    Retourne :
        WeatherRecordDb: L'objet ORM WeatherRecord qui a été créé.
    """

    # 1. Préparer les données AirPollution (si elles existent)
    db_air_pollution = None
    if record_data.air_pollution:
        # Pydantic v2 .model_dump() / v1 .dict()
        # Récupère le dictionnaire des composants
        components_data = record_data.air_pollution.components.model_dump()

        db_air_pollution = AirPollutionRecord(
            aqi=record_data.air_pollution.aqi,
            **components_data
        )
        # Note: Nous n'ajoutons pas à la session ici, la relation 'cascade'
        # (configurée dans models.py) devrait s'en charger lors de
        # l'ajout du 'db_weather_record'.

    # 2. Préparer les données WeatherRecord
    # On exclut 'air_pollution' car ce n'est pas un champ direct du modèle WeatherRecord,
    # mais un objet de relation que nous traiterons séparément.
    weather_data_dict = record_data.model_dump(exclude={"air_pollution"})

    db_weather_record = WeatherRecord(
        **weather_data_dict
    )

    # 3. Lier la relation (si elle existe)
    if db_air_pollution:
        db_weather_record.air_pollution = db_air_pollution
        # SQLAlchemy gère l'assignation de la clé étrangère (weather_record_id)
        # automatiquement grâce à la relation 'back_populates' définie dans models.py.

    # 4. Ajouter à la session et sauvegarder
    session.add(db_weather_record)

    # L'appelant (service ou endpoint) est responsable du 'commit'.
    # Nous 'flush' ici pour que l'objet db_weather_record obtienne son ID
    # et que la relation soit correctement établie avant de le retourner.
    await session.flush()
    await session.refresh(db_weather_record)

    return db_weather_record

