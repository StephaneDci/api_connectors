# Guide de Test - API Weather Connector

## 📁 Structure des Fichiers de Test

```
tests/openweather/
├── test_data/
│   ├── current_weather_Rome.json
│   ├── forecast_Rome.json
│   ├── air_pollution_Rome.json
│   ├── current_weather_Paris.json
│   ├── forecast_Paris.json           
│   └── air_pollution_Paris.json 
├── test_api_integration_2.py
├── conftest.py
└── generate_test_data.py
```

## 🚀 Ajouter une Nouvelle Ville aux Tests

### Méthode 1: Génération Automatique (Recommandé)

```bash
# Avec une vraie API key (données réelles)
export OPENWEATHER_API_KEY="votre_clé"
python tests/openweather/generate_test_data.py Paris FR 48.8566 2.3522

# Sans API key (données template)
python tests/openweather/generate_test_data.py Paris FR 48.8566 2.3522
```

Cela crée automatiquement les 3 fichiers JSON nécessaires.

### Méthode 2: Copie Manuelle

1. **Dupliquez les fichiers existants** :
   ```bash
   cd tests/openweather/test_data
   cp current_weather_Rome.json current_weather_Paris.json
   cp forecast_Rome.json forecast_Paris.json
   cp air_pollution_Rome.json air_pollution_Paris.json
   ```

2. **Modifiez les coordonnées** dans chaque fichier JSON

3. **Ajoutez la configuration** dans `test_api_integration_2.py`

### Étape 3: Configuration dans les Tests

Ouvrez `test_api_integration_2.py` et ajoutez dans le dictionnaire `TEST_LOCATIONS` :

```python
TEST_LOCATIONS = {
    "Rome": LocationTestData.from_json_files(city="Rome", country="IT"),
    "Paris": LocationTestData.from_json_files(city="Paris", country="FR"),
}
```

## ✅ Lancer les Tests

```bash
# Tous les tests
pytest tests/openweather/test_api_integration_2.py -v

# Un test spécifique pour une ville
pytest tests/openweather/test_api_integration_2.py::test_get_weather_report_success[Rome] -v

# Avec couverture
pytest tests/openweather/test_api_integration_2.py --cov=api_connectors -v

# Mode verbose avec détails
pytest tests/openweather/test_api_integration_2.py -vv -s
```

## 🎯 Avantages de Cette Architecture

### ✨ Extensibilité
- **Un seul endroit pour ajouter des villes** : le dictionnaire `TEST_LOCATIONS`
- **Tests automatiquement dupliqués** : `pytest.mark.parametrize` exécute tous les tests pour chaque ville
- **Aucune duplication de code** : les tests sont génériques

### 🧪 Tests Paramétrés
Chaque test est exécuté pour **chaque ville** définie dans `TEST_LOCATIONS`.

Exemple de sortie :
```
test_get_weather_report_success[Rome] PASSED
test_get_weather_report_success[Paris] PASSED
test_fetch_and_save_weather_report_success[Rome] PASSED
test_fetch_and_save_weather_report_success[Paris] PASSED
```

### 📊 Clarté
- **Dataclass `LocationTestData`** : structure claire et typée
- **Mock centralisé** : une seule fixture pour toutes les villes
- **Séparation des responsabilités** : configuration vs logique de test

## 🔧 Personnalisation

### Ajouter des Vérifications Spécifiques

Si une ville nécessite des vérifications particulières :

```python
@pytest.mark.asyncio
async def test_paris_specific_check(client, mock_http_client_get):
    """Test spécifique pour Paris."""
    location_data = TEST_LOCATIONS["Paris"]
    response = client.get(f"/weather/?location={location_data.location_name}")
    
    data = response.json()
    
    # Vérification spécifique à Paris
    assert "Tour Eiffel" in data.get("landmarks", [])
```

### Modifier la Structure des Données de Test

Si vous voulez ajouter des métadonnées :

```python
@dataclass
class LocationTestData:
    # ... champs existants ...
    timezone: str = "Europe/Paris"
    population: int = 0
    landmarks: list = None
```

## 📝 Bonnes Pratiques

1. **Nommage cohérent** : Toujours `{type}_{City}.json`
2. **Coordonnées précises** : Utilisez au moins 4 décimales
3. **Validation des données** : Vérifiez que les JSON sont valides
4. **Documentation** : Commentez les valeurs `expected_*` si elles sont non-évidentes
5. **Versionning** : Committez les fichiers JSON dans Git

## 🐛 Debugging

### Les tests échouent pour une ville spécifique

```bash
# Test uniquement cette ville
pytest tests/openweather/test_api_integration_2.py::test_get_weather_report_success[Paris] -vv -s

# Vérifiez le contenu du JSON
cat tests/openweather/test_data/current_weather_Paris.json | jq
```

### Le mock ne fonctionne pas

Vérifiez que :
- Les coordonnées dans le JSON correspondent exactement à celles dans `TEST_LOCATIONS`
- Le nom de la ville est cohérent partout (sensible à la casse)

### Erreur "FileNotFoundError"

```bash
# Vérifiez que les fichiers existent
ls -la tests/openweather/test_data/
```

## 📚 Ressources

- [Pytest Parametrize](https://docs.pytest.org/en/stable/how-to/parametrize.html)
- [Python Dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [OpenWeather API Documentation](https://openweathermap.org/api)