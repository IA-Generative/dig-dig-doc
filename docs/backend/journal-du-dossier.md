# Journal d'événements du dossier (backend)

Issue #169, parent #167. Chaque dossier a un **journal horodaté** : qui a fait quoi, et quand. Il alimente l'onglet « Historique » (#171) et, plus tard, les notifications du tableau de bord (#174).

## Modèle

Table `dossier_events` : `id`, `dossier_id` (FK, **cascade** : le journal part avec son dossier, cf. #94), `type`, `actor_id`, `actor_name`, `created_at`, `seq`, `payload` (JSONB).

- **Append-only** : l'application n'expose **aucune route** de modification ni de suppression (`POST`, `PUT`, `PATCH` et `DELETE` sur `/events` répondent 404 ou 405), et le dépôt n'a que `add`, `record_consultation` et `list_paginated`. Les lignes ne disparaissent qu'avec leur dossier.
- `actor_id` : identifiant (`sub` Keycloak) de l'auteur ; **NULL pour une action du système** (fin d'analyse par un worker, historique antérieur au journal). `actor_name` est une **photographie** du nom affiché à ce moment-là (l'annuaire est dans Keycloak).
- `seq` : ordre d'écriture, strictement croissant. Plusieurs événements d'une même transaction ont le même `created_at` ; `seq` garde leur ordre réel.
- `type` est stocké en **texte**, pas en enum PostgreSQL : ajouter un type (échéance #172, affectation #173, accès #177…) ne demande pas de migration.
- Les événements sont écrits **dans la même transaction** que l'action qu'ils décrivent : si l'action échoue, rien n'est journalisé.

## Ce qui est enregistré

| Type | Quand | `payload` |
| --- | --- | --- |
| `created` | Création du dossier. | `analyse_id` (ou `null`). |
| `consulted` | Ouverture du dossier (`GET /dossiers/{id}`). **Dédoublonnée** : une par utilisateur dans une fenêtre (15 min, `CONSULTATION_DEDUP_MINUTES`). | — |
| `status_changed` | Changement de statut de dossier (#168), y compris les dossiers déplacés quand un statut supprimé est remplacé. | `from`, `to` (`id`, `name`), et `reason` (`status_removed`) dans le cas d'un remplacement. |
| `closed` / `reopened` | Le dossier entre dans un statut final (date de clôture posée) / en sort. Aussi quand un statut devient final ou cesse de l'être. | `status`, et `reason` (`status_removed`, `status_flag_changed`). |
| `due_date_changed` | Échéance fixée, modifiée ou supprimée (#172), y compris la valeur posée par la durée par défaut de l'analyse. | `from`, `to` (dates `AAAA-MM-JJ` ou `null`), et `reason` (`default_duration`) pour une échéance automatique. |
| `assignee_changed` | Dossier affecté, réaffecté ou désaffecté (#173). Rien n'est écrit si la personne ne change pas. | `from`, `to` : `{id, name}` ou `null`. |
| `analyse_assigned` | Rattachement d'un dossier « à ranger » à une analyse. | `analyse_id`, `analyse_name`. |
| `document_added` | Dépôt d'un document. | `document_id`, `mimetype`, `size`. **Pas le nom** du fichier. |
| `analysis_started` / `analysis_stopped` | Lancement et arrêt manuel de l'analyse. | `analyse_version`. |
| `analysis_finished` / `analysis_failed` | Fin de l'analyse (**système**, sans auteur). | — |
| `document_generated` | Génération d'un document de fin d'instruction. | `document_id`, `version_number`, `template_name`, `incomplete`. |
| `document_downloaded` | Téléchargement d'un document généré (l'**aperçu** dans le navigateur n'en est pas un). | `document_id`, `format`. |

Les changements d'accès (#177) et les accès administrateur (#182) s'ajouteront avec leurs fonctionnalités.

### Données d'usagers

Le journal ne contient **jamais le contenu du dossier** : ni valeurs de champs, ni texte des documents, ni **nom de fichier** déposé (il peut porter le nom d'un usager). Seuls des identifiants et les valeurs nécessaires à l'affichage (ancien et nouveau statut) y figurent. Les tests le vérifient.

## API

`GET /api/dossiers/{id}/events` — événements du dossier, **du plus récent au plus ancien**, paginés (`page`, `page_size` ≤ 100).

| Paramètre | Effet |
| --- | --- |
| `type` | Un ou plusieurs types (`?type=status_changed&type=closed`). Un type inconnu donne 422. |
| `actor_id` | Les événements d'un auteur. |

Chaque élément : `id`, `type`, `actor_id`, `actor_name`, `created_at`, `payload`. Lire le journal **ne compte pas** comme une consultation.

`GET /api/dossiers/{id}/events/actors` — les **auteurs** distincts du dossier (`actor_id`, dernier `actor_name`), par nom : il alimente le filtre « Auteur » de l'historique ([`historique-du-dossier`](../frontend/historique-du-dossier/README.md), #171). Les actions du système (sans auteur) n'en font pas partie.

## Choix et limites

- **Droits** : comme les autres routes du dossier, ouvert à tout utilisateur connecté. La lecture du journal suivra les règles d'accès par groupe (#177).
- **Conservation** : le journal est conservé tant que le dossier existe ; la durée de conservation, en particulier des accès administrateur, reste à décider ([#182](https://github.com/IA-Generative/dig-dig-doc/issues/182)).
- **Historique existant** : la migration donne à chaque dossier existant un événement `created` daté de sa création, sans auteur (`"imported": true`) ; rien d'autre n'est reconstitué.
- Pas de garantie de base de données contre un `UPDATE` ou un `DELETE` direct en SQL : l'immuabilité est celle de l'application.
