## ⚙️ Workflow Alembic : Gestion des Migrations BDD

Alembic est l'outil **unique** pour toutes les modifications structurelles de la base de données. Il assure une évolution du schéma sans interruption en production ($0$ downtime).

| Rôle | Outil | Usage |
| :--- | :--- | :--- |
| **Schéma** | `models.py` | Définit l'état **souhaité** de la BDD (la source de vérité). |
| **Migration** | Alembic | Génère le script de transition entre l'état actuel et l'état souhaité. |
| **Application**| `alembic upgrade` | Exécute la mise à jour sur la BDD. |

***

## 🚀 Procédure pour Ajouter ou Modifier une Colonne

### Étape 1 : Modifier le Modèle

Modifiez le fichier `api_connectors/openweather_database/models.py` pour refléter l'état final désiré.

**Exemple :** Ajout de la colonne `humidity`.

```python
# Fichier : api_connectors/openweather_database/models.py

class WeatherRecordDBModel(Base):
    # ... autres colonnes ...
    humidity: Mapped[Optional[int]] = mapped_column(nullable=True)
```

### Étape 2 : Générer la Migration

Alembic compare les modèles mis à jour avec le schéma actuel de la BDD et crée le script de migration.
1. Assurez-vous que $DATABASE_URL est définie dans votre environnement (ou  dans alembic/env.py).
2. Exécutez la commande d'auto-génération :

```commandline
alembic revision --autogenerate -m "Ajout de la colonne humidity au rapport meteo"
```
3. Vérification critique : Ouvrez le nouveau fichier créé dans alembic/versions/. Confirmez que :


- La fonction upgrade() contient l'opération correcte (ex: op.add_column).

- La fonction downgrade() contient l'opération inverse (ex: op.drop_column).

### Étape 3 : Appliquer la mise à jour

Appliquez la migration. En production, cette étape doit être effectuée avant le déploiement du nouveau code de l'application.

```commandline
# Applique la migration la plus récente (HEAD)
alembic upgrade head
```

### Étape 4 : Tests et vérification d'usage

1. Test de Reconstitution Complète du Schéma (Local)

Ceci vérifie que la séquence complète de migrations permet de créer un schéma valide à partir d'une BDD vide.

Détruisez la base de données locale (si SQLite) :

````
rm [CHEMIN_VERS_VOTRE_DB].db
````

Recréez le schéma complet :
````
alembic upgrade head
````

2. Vérification d'Annulation (Downgrade)

Valide la réversibilité en cas d'erreur de déploiement.

Annulez la dernière migration appliquée :
````
alembic downgrade -1
````

Remontez à l'état le plus récent :
````
alembic upgrade head
````


3. Consultation de l'État

Affiche quelle migration est actuellement appliquée à la BDD.
````
alembic current
````


### Important: Nettoyage Critique du Code Applicatif

Ces étapes sont obligatoires pour éviter que l'application ne tente de gérer le schéma, ce qui provoquerait des conflits avec Alembic et des problèmes d'intégrité en production.


- api_connectors/openweather_database/database.py

Retirer: await conn.run_sync(Base.metadata.create_all)

- api_connectors/api_server.py

Retirer L'appel à await init_db() dans le lifespan.