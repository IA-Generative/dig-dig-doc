# Tableau de suivi (backend)

Issue #173, parent #167. Une route unique, `GET /api/tracking`, sert le tableau de suivi : l'onglet **« Suivi »** d'une analyse (avec `analyse_id`) et la **vue transversale** (sans `analyse_id`, toutes les analyses). Filtres, recherche, tri et pagination se font **côté serveur**.

## Une ligne

| Champ | Contenu |
| --- | --- |
| `id`, `name` | Identifiant et nom du dossier. |
| `reference` | Référence lisible, **`DOS-<année de création>-<numéro sur 4 chiffres>`** (« DOS-2026-0042 »). Le numéro est attribué par la base (`dossiers.ref_number`, unique, croissant) ; les dossiers existants en ont reçu un à la migration. |
| `analyse` | `{id, name}`. |
| `status` | Statut de dossier (#168) : nom, couleur, position, initial, final. |
| `assignee` | Responsable `{id, name}` ou `null` (#173, [affectation](affectation-des-dossiers.md)). |
| `due_at`, `due` | Échéance et son niveau calculé selon les seuils **de l'analyse de la ligne** (#172, [échéance](echeance-du-dossier.md)). |
| `created_at`, `last_activity_at` | Création, et dernière action du journal **hors consultations** (à défaut, la création). |

Aucun contenu de dossier (valeurs, textes, noms de fichiers) n'est renvoyé. Les dossiers « à ranger » (sans analyse) n'y figurent pas : ils n'ont ni statut ni seuils.

## Paramètres

| Paramètre | Rôle |
| --- | --- |
| `analyse_id` (répétable) | Une ou plusieurs analyses ; aucune = toutes. |
| `status_id` | Un statut précis. |
| `status_category` | `initial`, `progress` (ni initial ni final), `final` : regroupement **commun à toutes les analyses**, pour filtrer la vue transversale (leurs statuts diffèrent). |
| `assignee` | `me`, `none` (non affectés) ou l'identifiant d'une personne. |
| `due` | `overdue`, `7`, `30` (jours restants au plus), `none` ; **dossiers non clos** uniquement. |
| `search` | Nom **ou référence**, sans casse (`%` et `_` sont des caractères ordinaires). |
| `sort`, `direction` | `reference`, `name`, `analyse`, `status` (ordre de l'analyse), `assignee`, `due`, `created_at`, `last_activity_at` ; `asc` ou `desc` (défaut : création, récents d'abord). |
| `page`, `page_size` | Pagination ; `page_size` ≤ 100. |

- Les valeurs **absentes** (sans échéance, non affecté, sans statut) restent **en dernier dans les deux sens** du tri.
- À égalité, l'ordre suit le numéro de référence : deux lectures successives donnent le même ordre.
- Un `sort` inconnu, un `due` invalide ou un `page_size` au-delà de 100 sont refusés (422) : le tri n'est jamais construit à partir d'un texte libre.

## Choix et limites

- **Accès** : seuls les dossiers **visibles** de la personne sont listés, comptés et exportés ([accès](acces-aux-dossiers.md)).
- **Pas encore** : recherche dans les colonnes personnalisées, filtres sur ces colonnes, vues enregistrées, préférences de colonnes, export CSV (étapes suivantes de #173).
- Migration : `20261010_0900_a6b7c8d9e0f1_reference_des_dossiers.py` (testée en montée, descente et remontée sur des données existantes). Schéma : [`data-model.png`](data-model.png).
