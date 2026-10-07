# Échéance des dossiers (backend)

Issue #172, parent #167. Un dossier peut avoir une **date d'échéance**. Le serveur calcule sa **situation** (loin, proche, dépassée, clos) et sa **couleur** à partir des **seuils de l'analyse** : l'interface, le tableau de suivi et le tableau de bord n'ont aucun seuil codé en dur.

## Modèle

| Table | Champs |
| --- | --- |
| `dossiers` (ajout) | `due_at` : une **date** (jour du calendrier, pas un instant), `NULL` = pas d'échéance. Indexée. |
| `analyses` (ajouts) | `default_due_days` : durée par défaut en jours depuis la création (`NULL` = pas d'échéance automatique) ; `due_thresholds` : seuils de couleur (JSONB). |

Le fuseau de référence est **Europe/Paris** : « aujourd'hui » et le jour de clôture sont des jours parisiens.

### Seuils

```json
{
  "far_color": "#18753c",
  "steps": [{ "days": 30, "color": "#b34000" }, { "days": 7, "color": "#ce0500" }],
  "overdue_color": "#8a0000"
}
```

- Un seuil `{days, color}` signifie « **N jours restants ou moins** ». La couleur est celle du seuil **le plus serré** qui contient le nombre de jours restants ; au-delà du premier seuil, `far_color` ; une échéance dépassée prend `overdue_color`.
- Au plus **5 seuils**, de 1 à 3 650 jours, **sans doublon** ; couleurs au format `#RRGGBB`. Le serveur les range du plus large au plus serré.
- Valeurs données à toute analyse : vert au-delà de 30 jours, orange jusqu'à 8, rouge à 7 jours ou moins, rouge foncé si dépassée.

## Situation d'un dossier (`due`)

`DossierOut` expose `due_at`, `due` et `closed_before_due` :

| Champ | Contenu |
| --- | --- |
| `due.level` | `ok` (loin), `soon` (dans un seuil), `overdue` (dépassée), `closed` (dossier clos : plus à surveiller). |
| `due.days_left` | Jours restants ; **négatif** si l'échéance est dépassée ; `0` le jour même. |
| `due.color` | Couleur du niveau selon les seuils ; `null` pour un dossier clos. |
| `closed_before_due` | Pour un dossier **clos** avec une échéance : clos au plus tard le jour de l'échéance ? Sinon `null`. Sert à la part de dossiers clôturés dans les temps (#174). |

`due` est `null` sans échéance. La logique est **pure** (`app/services/due_date.py`) : « aujourd'hui » est un paramètre, ce qui la rend testable avec une date fixe.

## API

| Route | Rôle |
| --- | --- |
| `PUT /api/dossiers/{id}/due-at` | Corps `{"due_at": "2026-10-28"}` ; `null` supprime l'échéance. Le changement est tracé dans le [journal](journal-du-dossier.md) (`due_date_changed`). |
| `GET /api/dossiers?due=…&sort=due` | Filtre `overdue` (dépassée), `7` / `30` (dans 7 / 30 jours ou moins), `none` (sans échéance) : **dossiers non clos uniquement**. `sort=due` : l'échéance la plus proche d'abord, les dossiers sans échéance en dernier. |
| `GET /api/analyses/{id}/due-settings` | Durée par défaut et seuils. |
| `PUT /api/analyses/{id}/due-settings` | Les remplace ; l'ancien état entre dans l'**historique**. Sans changement, rien n'est versionné. |
| `POST /api/analyses/{id}/due-settings/restore/{version_id}` | Restaure une version ; l'état courant devient lui-même une version. |

Le réglage est **versionné** comme les autres champs d'une analyse (`FieldVersion`, champ `due_settings`) et renvoyé avec l'analyse (`due_settings`, `due_settings_versions`).

## Durée par défaut

À la **création** d'un dossier rattaché à une analyse, et au **rattachement** d'un dossier « à ranger », l'échéance est posée à `création + default_due_days`, si l'analyse en définit une et si le dossier n'en a pas déjà une. L'événement de journal porte alors `reason: default_duration`. Changer la durée par défaut n'affecte **pas** les dossiers existants.

## Choix et limites

- Seuils **par analyse**, pas par utilisateur (question ouverte de #172 tranchée ainsi : une échéance est une règle de traitement, pas une préférence).
- Aucune **action à l'échéance** (archivage, suppression, notification) : hors périmètre.
- Le tableau de suivi (#173) et le tableau de bord (#174) utilisent encore des données simulées ; ils consommeront `due` quand ils seront branchés sur l'API.
- Migration : `20261008_0900_e4f5a6b7c8d9_echeance_des_dossiers.py` (ajoute la valeur `DUE_SETTINGS` à l'énumération des champs versionnés, les deux colonnes de l'analyse avec leurs valeurs par défaut, et `dossiers.due_at`). Schéma : [`data-model.png`](data-model.png).
