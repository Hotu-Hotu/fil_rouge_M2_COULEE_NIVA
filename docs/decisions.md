# Décisions validées avec le Product Owner

## Formats de sortie

| Entrée | `burned` | `track` | `subtitles` | `text` |
|---|---|---|---|---|
| Vidéo `.mp4` | oui | oui | oui | oui |
| Audio `.wav` | non | non | oui | oui |

- `burned` (« vidéo avec sous-titres embedded ») : sous-titres **dessinés sur l'image**.
- `track` (« vidéo + sous-titres à part ») : `.mp4` avec une piste de sous-titres activable
  (marquée par défaut), plus le `.srt` à côté.
- `subtitles` : `.srt`, plus `.vtt` pour l'aperçu dans le navigateur.
- `text` : `.txt` sans timestamp.

## Langue

Anglais uniquement pour l'instant. Le modèle se choisit dans la configuration,
ce qui permettra de passer à un modèle multilingue sans toucher au reste du code.

## Taille des fichiers

Pas de durée typique : c'est à nous de fixer une taille maximale, avec un avertissement
pour l'utilisateur au-delà d'un seuil. Valeurs provisoires dans `transcription/config.py`,
à ajuster après le test de charge.

## Charge

10 utilisateurs en parallèle au maximum. Le traitement doit durer moins longtemps
que le fichier fourni.

## Hébergement

Hébergeur français de préférence (OVHcloud, Scaleway), si le budget de 10 000 €/an
est respecté.

## Conservation des données

- Utilisateur : fichiers et résultats disponibles **dans la journée**, puis supprimés.
- Data scientists : données conservées **3 à 6 mois**, et utilisables pour améliorer
  les modèles. Durée exacte à justifier au regard du RGPD (finalité, base légale,
  information et consentement de l'utilisateur).

## Accès administrateur

- L'admin doit pouvoir identifier chaque utilisateur (nom, id) et voir son activité.
- Par défaut, l'admin voit les métadonnées des traitements, **pas leur contenu**.
- L'accès au contenu passe par un formulaire d'autorisation légale, qui laisse une trace.
