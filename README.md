# Api Connectors

## Usage

Simple wrapper of API Openweather
- https://home.openweathermap.org/api_keys


API wrapper for :
- https://openweathermap.org/current
- https://openweathermap.org/forecast5
- https://openweathermap.org/api/air-pollution

Features
- Simple API server and client
- Persistance
- Rapport generation
- (...)


## Lancement de l'API

```
# manuel
 uvicorn api_connectors.weather.api_server:app --reload --host 0.0.0.0 --port 8000

# fichier Python
 run_api_server.py
```

## Accès et Usage 

### Configuration

l'environnement doit contenir la clé d'API: 
- OPENWEATHER_API_KEY

### API

```commandline
# Swager et doc
http://127.0.0.1:8000/docs

# Récupération d'un rapport météo (exemple): 
http://127.0.0.1:8000/weather/?location=Paris,FR
```

## Modèle de données

### Base de données

```commandline
# Vérification en base avec le client sqlite: 
sqlite3 api_connectors/openweather_database/weather_data.db

# Affichage des tables et des schemas
sqlite> .tables
sqlite> .schema

# Exemple requête sql de SELECT
SELECT * FROM weather_records;
```

### Schémas

Vérification des schémas via Pydantic.