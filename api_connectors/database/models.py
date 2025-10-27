from sqlalchemy import Column, Integer, String, Float, DateTime, Index, ForeignKey
from sqlalchemy.orm import relationship  # Ajout de l'outil de relation
from datetime import datetime
from api_connectors.database.database import Base


class WeatherRecord(Base):
    """
    Modèle de base de données pour enregistrer les requêtes météo.
    Ce modèle reflète la structure des données 'CurrentWeather' de l'API
    et inclut les champs de localisation pour le tri et l'historique.
    """
    __tablename__ = "weather_records"

    # Définition de l'index composé pour l'optimisation des requêtes
    __table_args__ = (
        # Index optimisé pour la recherche par ville ET le tri par date (requis pour SQLAlchemy Asynchrone)
        Index('weather_record_idx', 'location_name', 'measure_timestamp'),
    )

    # Colonnes
    id = Column(Integer, primary_key=True, index=True)

    # ---------------------------
    # Données de Localisation (issues du modèle Location)
    # ---------------------------
    location_name = Column(String, index=True, nullable=False)  # Index unique sur ce champ pour une recherche rapide
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)

    # ---------------------------
    # Horodatage (pour le tri)
    # ---------------------------
    measure_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ---------------------------
    # Données Météo Actuelles (issues du modèle CurrentWeather)
    # ---------------------------
    current_temp = Column(Float, nullable=True)  # temp
    feels_like = Column(Float, nullable=True)  # temp
    humidity = Column(Integer, nullable=True)
    wind_speed = Column(Float, nullable=True)
    description = Column(String, nullable=True)  # description


    # ---------------------------
    # Relation un-à-un vers la qualité de l'air
    # ---------------------------
    # 'uselist=False' définit la relation comme un-à-un
    air_pollution = relationship("AirPollutionRecord", back_populates="weather_record", uselist=False, )

    def __repr__(self):
        return (
            f"<WeatherRecord("
            f"location='{self.location_name}', "
            f"temp={self.temp} °C, "
            f"date={self.measure_timestamp.strftime('%Y-%m-%d %H:%M')})"
            f">"
        )


class AirPollutionRecord(Base):
    """
    Modèle pour stocker les données détaillées de la qualité de l'air.
    Relation un-à-un avec WeatherRecord.
    """
    __tablename__ = "air_pollution_records"

    # Clé primaire et clé étrangère vers WeatherRecord
    id = Column(Integer, ForeignKey("weather_records.id"), primary_key=True)

    # ---------------------------
    # Données de Qualité de l'Air (issues du JSON AirPollution)
    # ---------------------------
    aqi = Column(Integer, nullable=True)  # Air Quality Index

    # Composants chimiques (tous en Float)
    co = Column(Float, nullable=True)
    no = Column(Float, nullable=True)
    no2 = Column(Float, nullable=True)
    o3 = Column(Float, nullable=True)
    so2 = Column(Float, nullable=True)
    pm2_5 = Column(Float, nullable=True)
    pm10 = Column(Float, nullable=True)
    nh3 = Column(Float, nullable=True)

    # ---------------------------
    # Relation
    # ---------------------------
    # 'back_populates' crée la connexion réciproque vers l'objet WeatherRecord
    weather_record = relationship("WeatherRecord", back_populates="air_pollution")

    def __repr__(self):
        return f"<AirPollutionRecord(aqi={self.aqi}, co={self.co})>"
