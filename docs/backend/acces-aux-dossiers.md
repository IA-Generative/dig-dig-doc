# Accès aux dossiers par groupe (backend)

Issue #177 (partie 1 : modèle, règle, création, modification, affectation), parent #144. Avoir accès à une **analyse** ne donne plus accès à tous ses **dossiers** : un dossier peut être **restreint** à certains groupes Keycloak.

> **État : partie 1.** La règle est appliquée à la **liste**, au **détail**, à la **création**, à l'**accès** et à l'**affectation** des dossiers. Les autres routes qui portent un identifiant de dossier (documents, chat, analyse de dossier, documents générés, notes, recherche), le tableau de suivi, le tableau de bord et les notifications **ne la filtrent pas encore** : c'est la partie 2. Tant qu'elle n'est pas livrée, ne pas considérer un dossier restreint comme protégé hors de la liste et du détail.

## Règle

Une seule règle, partagée (`app/services/dossier_access.py`) : aucune route ne réécrit la sienne.

| Qui | Voit un dossier… |
| --- | --- |
| **Administrateur** | tous. |
| Membre d'un groupe associé | **restreint** : s'il est membre d'un des groupes du dossier (chemin **exact** : pas d'héritage vers un sous-groupe ni vers le groupe parent). |
| Toute personne qui a accès à l'analyse | **« selon l'analyse »** (aujourd'hui, toute personne connectée). |
| N'importe qui | un dossier **« à ranger »** (sans analyse) suit ses groupes associés : il n'a pas d'analyse dont hériter. |

- Le **créateur n'a aucun droit propre** : son accès vient de ses groupes. S'il quitte le groupe, il perd l'accès.
- Un dossier qu'on ne voit pas répond **404** (jamais 403), pour ne pas révéler son existence.
- L'**affectation** ne donne pas d'accès : on affecte quelqu'un qui a déjà accès.

## Modèle

- `dossiers.visibility` : `restricted` ou `analyse`. Les dossiers **existants** sont migrés en `analyse` : personne ne perd d'accès à la mise en production ; ils restent visibles comme avant, sans limite de temps ([#180](https://github.com/IA-Generative/dig-dig-doc/issues/180)). Seuls les dossiers créés ensuite par un utilisateur sont restreints par défaut.
- `dossier_group_access` (`dossier_id`, `keycloak_group`, `granted_by`, `created_at`) : les groupes associés, supprimés avec le dossier.
- `app_users.groups` et `app_users.is_admin` : les groupes et le rôle **vus à la dernière connexion** (annuaire, [affectation](affectation-des-dossiers.md)). Ils servent à savoir si une personne a accès à un dossier sans interroger Keycloak : copie d'un instant, mise à jour à la prochaine connexion ([#179](https://github.com/IA-Generative/dig-dig-doc/issues/179)).

Schéma : [`data-model.png`](data-model.png). Migration : `20261013_0900_d9e0f1a2b3c4_acces_aux_dossiers.py`.

## Création

`POST /api/dossiers` accepte `visibility` (`restricted` ou `analyse`) et `group_paths`.

- Sans `visibility` : **restreint**, aux groupes que la personne choisit, **à défaut tous les siens**.
- Les groupes proposés sont **ceux de la personne**, y compris pour un administrateur (422 `group_not_yours` sinon). Pas d'appel à l'API d'administration de Keycloak.
- Un dossier restreint a **au moins un groupe** (422 `groups_required`), sinon son créateur lui-même ne pourrait plus l'ouvrir.
- `analyse` n'a pas de groupe : ceux qu'on enverrait sont ignorés.
- Les créations **sans session utilisateur** (agent assistant MCP, runs éphémères, routes internes) restent « selon l'analyse », comme avant.

## API

| Route | Rôle |
| --- | --- |
| `GET /api/dossiers/{id}/access` | Visibilité, groupes (avec qui les a associés et quand), `can_edit` (administrateur), `available_groups` (les groupes de la personne). Lisible par ceux qui voient le dossier. |
| `PUT /api/dossiers/{id}/access` | Remplace visibilité et groupes. **Administrateurs seulement** (403 sinon). Un groupe **ajouté** doit faire partie des groupes de l'administrateur ; un groupe déjà associé se garde ou se retire librement. Un dossier restreint garde au moins un groupe. |
| `PUT /api/dossiers/{id}/assignee`, `PUT /api/dossiers/bulk-assignee` | 422 `assignee_has_no_access` si la personne n'a pas accès (tout ou rien en lot, avec la liste des dossiers concernés) ; 404 pour un dossier qu'on ne voit pas. |
| `GET /api/dossiers`, `GET /api/dossiers/{id}` | Ne renvoient que les dossiers visibles. |

Un changement d'accès est tracé dans le [journal](journal-du-dossier.md) (`access_changed` : visibilité avant et après, groupes ajoutés et retirés). Retirer un groupe **désaffecte** la personne qui perd ainsi l'accès (événement `assignee_changed` avec `reason: access_lost`) ; la réponse l'indique (`assignee_unassigned`). Changer la visibilité vers « selon l'analyse » ne désaffecte personne.

## Reste à faire (partie 2 et suivantes)

- Appliquer la règle à **toutes** les routes qui portent un dossier, au tableau de suivi (`GET /api/tracking`, compteurs, export), au tableau de bord, aux notifications (masquer le nom du dossier après un retrait d'accès) et aux créneaux.
- Tracer les **accès administrateur** à un dossier hors de ses groupes (événement distinct, [#182](https://github.com/IA-Generative/dig-dig-doc/issues/182)).
- Interface : section « Accès » du dossier, pastille « Restreint », choix des groupes à la création, filtre et action en lot du suivi.
- Un lien de partage par e-mail ne doit jamais donner plus de droits que ceux du destinataire.
- Rôles (lecture, instructeur…) : [#178](https://github.com/IA-Generative/dig-dig-doc/issues/178).
