---
source: https://github.com/zhanymkanov/fastapi-best-practices
tags: [fastapi, python, architecture, fil-rouge]
---

# FastAPI Best Practices : résumé

## 1. Structure du projet
- **Organiser par domaine métier, pas par type de fichier.** Tout le code sous `src/`,
  avec `src/main.py` qui crée l'application.
- Chaque domaine (`src/<domaine>/`) contient :
  - `router.py` : les routes
  - `schemas.py` : les modèles Pydantic
  - `models.py` : les modèles de base de données
  - `service.py` : la logique métier
  - `dependencies.py` : les dépendances des routes
  - `constants.py` : constantes et codes d'erreur
  - `config.py` : la configuration du domaine (variables d'environnement)
  - `exceptions.py` : les exceptions du domaine (`PostNotFound`…)
  - `utils.py` : les fonctions utilitaires sans logique métier
- Fichiers globaux dans `src/` : `config.py`, `models.py`, `exceptions.py`, `database.py`,
  `pagination.py`, `main.py`.
- À la racine : `tests/` (qui reprend les domaines), `alembic/`, `requirements/`
  (`base.txt`, `dev.txt`, `prod.txt`), `.env`, `logging.ini`.
- Entre domaines, importer avec un alias explicite :
  `from src.auth import constants as auth_constants`.

## 2. Routes async ou sync
- Une route `async def` tourne sur la boucle d'événements : **elle ne doit jamais bloquer**
  (pas de `time.sleep`, pas d'I/O bloquante).
- Une route `def` tourne dans un pool de threads : à utiliser pour les I/O bloquantes,
  mais le pool est limité.
- Pour du **calcul lourd** (CPU/GPU), ni `await` ni les threads n'aident (GIL) :
  utiliser un autre processus ou une **file de tâches** (Celery, RQ, Arq).
- Appeler un SDK bloquant depuis une route async : `run_in_threadpool`.

## 3. Pydantic
- Exploiter la validation intégrée : `Field(min_length, max_length, pattern, ge…)`,
  `Enum`, `EmailStr`, `AnyUrl`, champs optionnels `| None`.
- Un **`CustomModel`** commun à tous les schémas (format des dates, `populate_by_name`…).
- **Découper la configuration** : une classe `BaseSettings` par domaine plus une classe
  globale, instanciées au niveau du module (`settings`, `auth_settings`).
- Un `ValueError` levé dans un `@field_validator` donne une réponse d'erreur détaillée au client.

## 4. Dépendances
- Les utiliser pour la **validation qui demande une donnée** (l'objet existe-t-il ?
  l'utilisateur en est-il propriétaire ?) plutôt que de la répéter dans chaque route.
- Les **chaîner** : `valid_owned_post` dépend de `valid_post_id` et de `parse_jwt_data`.
- FastAPI **met en cache** le résultat d'une dépendance pendant une requête.
- Les préférer en `async def` quand elles ne bloquent pas.

## 5. Divers
- **REST** : chemins de ressources (`/courses/{course_id}/chapters/{chapter_id}`) et noms
  de variables de chemin cohérents, pour pouvoir réutiliser les dépendances.
- **Documentation** : la masquer hors des environnements autorisés (`openapi_url=None`).
  Documenter chaque route : `response_model`, `status_code`, `tags`, `summary`,
  `description`, `responses`.
- **Tâches de fond** : `BackgroundTasks` seulement pour du court et perdable (un e-mail).
  Pour du long, du lourd, des reprises ou de la planification : une vraie file de tâches.
  *Si perdre la tâche réveillerait quelqu'un la nuit, pas de `BackgroundTasks`.*
- **Base de données** :
  - convention de nommage explicite des index et contraintes (`MetaData(naming_convention=…)`) ;
  - tables en `snake_case` au singulier (`post`, `post_like`), préfixe par module ;
  - suffixe `_at` pour les dates-heures, `_date` pour les dates ;
  - **SQL d'abord** : jointures, filtres et agrégats faits par la base ;
  - SQLAlchemy 2.0 en async pour un nouveau projet.
- **Migrations Alembic** : statiques et réversibles, avec un nom descriptif
  (`2022-08-24_post_content_idx.py`).
- **Tests** : client async dès le départ (`httpx.AsyncClient` + `ASGITransport`,
  `@pytest.mark.asyncio`), dépendances externes remplacées par `app.dependency_overrides`.
- **Lint et formatage** : **Ruff** (remplace black, isort, autoflake) :
  `ruff check --fix src` et `ruff format src`.

## Application au projet fil rouge
| Recommandation | Appliquée |
|---|---|
| Code sous `src/`, organisé par domaine | `src/transcription/` (pipeline) et `src/jobs/` (API des traitements) |
| router / schemas / service / dependencies / exceptions / constants | Oui, dans `src/jobs/` |
| Configuration découpée avec `BaseSettings` | `src/config.py` (global) et `src/transcription/config.py` |
| `CustomModel` et `response_model` | `src/schemas.py`, réponses typées |
| Validation par dépendances chaînées | `valid_job_id` → `valid_job_file`, `valid_upload` |
| Routes async sans blocage | Écriture des fichiers via `run_in_threadpool` |
| Calcul lourd hors de la boucle d'événements | Thread dédié pour l'instant, vraie file de tâches à l'étape 2c |
| Documentation masquée hors local/staging, routes documentées | Oui |
| Tests async avec `dependency_overrides` | Oui |
| `requirements/` base et dev, Ruff | Oui |
| Base de données, Alembic, convention de nommage | À l'étape 2b |
