# Créneaux de traitement (backend)

Issue #174, parent #167. Une personne peut **réserver du temps pour traiter un dossier** : un créneau, éventuellement répété, avec des rappels. Il s'affiche dans l'agenda du [tableau de bord](tableau-de-bord.md).

## Principes

- **Privé** : un créneau n'appartient qu'à la personne qui l'a posé. Elle seule le lit, le modifie et le supprime ; aucune route ne renvoie le créneau d'une autre personne. Le **partage de l'agenda** viendra plus tard ; `user_id` en restera le propriétaire.
- **Toujours rattaché à un dossier** : pas de créneau libre.
- **Un seul créneau par personne et par dossier** : en poser un nouveau remplace le précédent.
- **Hors journal du dossier** : le journal ([#169](journal-du-dossier.md)) est lu par tous ceux qui ouvrent le dossier ; la planification de chacun reste personnelle, aucun événement n'y est écrit.

## Modèle

Table `work_slots` : `user_id` (sub Keycloak), `dossier_id` (`CASCADE` : le créneau disparaît avec le dossier), `start_at` et `end_at` (première occurrence, avec fuseau), `recurrence` (JSONB, `NULL` = créneau unique), `reminders` (JSONB, minutes avant chaque occurrence), `created_at`, `updated_at`. Unicité sur (`user_id`, `dossier_id`). Schéma : [`data-model.png`](data-model.png).

### Récurrence

```json
{ "unit": "week", "interval": 2, "weekdays": [0, 4], "end": { "type": "count", "count": 6 } }
```

| Champ | Règle |
| --- | --- |
| `unit` | `day`, `week`, `month` ou `year`. |
| `interval` | « Tous les N… », de 1 à 999. |
| `weekdays` | 0 = lundi … 6 = dimanche ; **réservé à `week`** ; rangés et dédoublonnés ; absent = le jour du créneau. |
| `end` | `{"type": "never"}`, `{"type": "until", "date": "AAAA-MM-JJ"}` (jusqu'à ce jour **inclus**, pas avant le premier créneau) ou `{"type": "count", "count": 1 à 1000}`. |

### Horaires et rappels

- `start` et `end` sont des **instants avec fuseau** (un horaire sans fuseau est refusé : l'heure d'été le rendrait ambigu). La fin suit le début, **24 heures au plus**.
- **3 rappels au plus**, de 0 (à l'heure) à 60 jours avant (86 400 minutes), rangés et sans doublon.

## API

| Route | Rôle |
| --- | --- |
| `GET /api/slots` | Mes créneaux, par début. |
| `PUT /api/dossiers/{id}/slot` | Pose ou remplace mon créneau sur ce dossier (404 si le dossier n'existe pas ; 422 si une règle ci-dessus n'est pas respectée). |
| `DELETE /api/dossiers/{id}/slot` | Retire mon créneau (204, même s'il n'y en avait pas). |

`GET /api/dashboard` joint **mon** créneau à chaque urgence (`slot`, `null` sinon).

## Choix et limites

- **Occurrences** : le serveur stocke la règle, il ne développe pas encore les occurrences ; l'interface les calcule pour l'agenda. Le calcul côté serveur viendra avec les **rappels** (notifications), qui en ont besoin pour savoir quand se déclencher.
- **Rappels** : toujours déclenchés par le navigateur, tant que la page est ouverte ; au chargement du tableau de bord ils sont reprogrammés à partir des créneaux du serveur.
- **Accès** ([#177](acces-aux-dossiers.md)) : un créneau ne se pose que sur un dossier visible (404 sinon) ; un créneau sur un dossier qu'on ne voit plus n'est plus listé.
- Migration : `20261011_0900_b7c8d9e0f1a2_creneaux_de_traitement.py` (testée en montée, descente et remontée).
