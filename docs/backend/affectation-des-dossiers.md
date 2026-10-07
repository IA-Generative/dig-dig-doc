# Affectation des dossiers (backend)

Issue #173 (partie affectation), parent #167. Un dossier peut être **affecté à une personne** : celle qui s'en occupe. Une seule personne à la fois (un seul responsable par dossier).

## Annuaire local

L'identité vit dans Keycloak : l'application n'a pas de table d'utilisateurs maîtresse. Pour pouvoir **proposer** des personnes à l'affectation et afficher leur nom, une table `app_users` en garde une **copie minimale**.

| Champ | Contenu |
| --- | --- |
| `user_id` | `sub` Keycloak (clé primaire). |
| `name` | Prénom et nom ; à défaut l'e-mail, puis l'identifiant. |
| `email` | Sert à la recherche ; **jamais renvoyé** par l'API. |
| `last_seen_at` | Dernière connexion. |

- Elle est **alimentée à la connexion** : `GET /api/auth/me`, appelé à chaque ouverture de l'application, enregistre ou met à jour la personne. Rien ne s'écrit à la main.
- Une personne qui ne s'est **jamais connectée** n'y figure pas et **ne peut pas recevoir de dossier** (422 `unknown_user`).
- `GET /api/users?q=&limit=` liste les personnes (`{id, name}`), triées par nom ; `q` cherche dans le nom et l'e-mail sans tenir compte de la casse (`%` et `_` sont des caractères ordinaires). 50 résultats par défaut, 100 au plus.

## Modèle

`dossiers` gagne `assignee_id` (clé étrangère vers `app_users.user_id`, `SET NULL`, indexée) et `assigned_at`. `DossierOut` expose `assignee` (`{id, name}` ou `null`) et `assigned_at`. Un dossier est créé **non affecté**.

## API

| Route | Rôle |
| --- | --- |
| `PUT /api/dossiers/{id}/assignee` | Corps `{"assignee_id": "<sub>"}` ; `null` désaffecte. Renvoie le dossier. |
| `PUT /api/dossiers/bulk-assignee` | Corps `{"dossier_ids": [...], "assignee_id": "<sub>" \| null}` ; de 1 à 200 dossiers, **en une seule transaction**. Renvoie `{"updated": n, "unchanged": m}`. |
| `GET /api/dossiers?assignee=…` | `me` (moi), `none` (non affectés) ou l'identifiant d'une personne. |

- **Tout ou rien** : si un dossier d'un lot n'existe pas, aucun n'est modifié (404, `detail.dossier_ids` liste les identifiants introuvables). Les doublons du lot sont ignorés ; un dossier déjà affecté à cette personne compte dans `unchanged`.
- Chaque changement est tracé dans le [journal](journal-du-dossier.md) (`assignee_changed`, avec ancien et nouveau responsable), dans la même transaction. Affecter à la personne déjà responsable n'écrit rien.

## Choix et limites

- **Droits** : tout utilisateur connecté peut affecter. Les rôles (#178) préciseront qui. On n'affecte qu'une personne qui a **accès au dossier** (422 sinon), et `GET /api/users?dossier_id=…` ne propose qu'elles ; retirer un groupe désaffecte la personne qui perd l'accès ([accès](acces-aux-dossiers.md)).
- **Notification** au nouvel affecté : elle arrivera avec le tableau de bord (#174), à partir de l'événement `assignee_changed` (sans notifier l'auteur de l'action).
- L'annuaire est la **copie d'un instant** : un nom modifié dans Keycloak se met à jour à la prochaine connexion de la personne. Le journal garde le nom de l'époque.
- Migration : `20261009_0900_f5a6b7c8d9e0_affectation_des_dossiers.py` (testée en montée, descente et remontée). Schéma : [`data-model.png`](data-model.png).
