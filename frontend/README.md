# Front-end

Interfaces de la solution, construites à l'étape 3 :

- **interface utilisateur** : envoi d'un fichier `.mp4` ou `.wav`, choix du format de sortie,
  suivi du traitement, téléchargement et aperçu du résultat ;
- **tableau de bord administrateur** : statistiques d'usage, traitements par utilisateur,
  accès au contenu avec autorisation légale.

Le front-end ne parle au back-end que par son API HTTP (voir `backend/`), avec une clé d'API
dans l'en-tête `X-API-Key`. La documentation de l'API est sur `http://127.0.0.1:8000/docs`
quand le back-end tourne en local.
