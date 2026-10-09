# Colonnes personnalisées du suivi (backend)

Issue #173, parent #167. Un administrateur définit, **par analyse**, les informations propres à son métier à suivre pour chaque dossier (montant demandé, service instructeur, date de dépôt…). Elles apparaissent comme **colonnes du [tableau de suivi](tableau-de-suivi.md)**, avec leurs valeurs, leurs filtres et leur tri.

## Modèle

- `analyses.custom_fields` (JSONB) : la liste des **définitions**, versionnée (`FieldVersion`, champ `custom_fields`) avec historique et restauration, comme les autres champs d'une analyse.
- `dossiers.custom_values` (JSONB) : les **valeurs**, `{identifiant du champ: valeur}`.
- Le journal du dossier a un type `custom_value_changed`. Schéma : [`data-model.png`](data-model.png). Migration : `20261014_0900_e0f1a2b3c4d5_colonnes_personnalisees.py`.

### Une définition

| Champ | Règle |
| --- | --- |
| `id` | Identifiant **stable** (`f_…`), donné par le serveur à un nouveau champ : les valeurs des dossiers s'y rattachent, renommer un champ ne perd rien. |
| `name` | De 1 à 80 caractères, **unique** dans l'analyse (sans tenir compte de la casse). |
| `definition` | Jusqu'à 500 caractères : affichée en aide dans l'en-tête de la colonne. |
| `type` | `text`, `number`, `amount`, `date`, `boolean` ou `choice`. |
| `required` | Interdit de **vider** la valeur (un oui/non n'est jamais vide). |
| `default_value` | Valeur donnée à un **nouveau** dossier ; doit convenir au type. |
| `choices` | Pour `choice` : de 1 à 50 choix, uniques, de 80 caractères au plus (nettoyés des espaces et des lignes vides). |
| `currency` | Pour `amount` : `EUR`, `USD` ou `GBP`. |

**Au plus 20 champs par analyse.**

### Les valeurs, par type

| Type | Valeur acceptée | Message en cas d'erreur |
| --- | --- | --- |
| `text` | Texte de 1 000 caractères au plus. | « Saisissez du texte. » |
| `number` | Nombre fini (pas un oui/non, au plus 10¹⁵). | « Saisissez un nombre. » |
| `amount` | Nombre **positif ou nul**. | « Saisissez un montant positif. » |
| `date` | `AAAA-MM-JJ`, date réelle. | « Saisissez une date valide. » |
| `boolean` | `true` ou `false`. | « Valeur invalide. » |
| `choice` | Un des choix du champ. | « Choisissez une valeur de la liste. » |

Une valeur **vide** (`null` ou chaîne vide) efface la valeur, sauf champ obligatoire (« Ce champ est obligatoire. »). Ce sont les règles de l'interface, avec les mêmes messages : le serveur refuse ce que l'interface refuse.

## API

| Route | Rôle |
| --- | --- |
| `GET /api/analyses/{id}/custom-fields` | Les définitions. Aussi dans `GET /api/analyses/{id}` (`custom_fields`, `custom_fields_versions`). |
| `PUT /api/analyses/{id}/custom-fields` | Remplace les définitions : `{"fields": [...], "purge_removed": false}`. **Administrateurs seulement** (403). Un champ **sans `id`** est nouveau. L'état précédent entre dans l'historique ; un enregistrement sans changement n'en crée pas. |
| `POST /api/analyses/{id}/custom-fields/restore/{version_id}` | Restaure une version (administrateurs) ; l'état courant devient lui-même une version. |
| `PUT /api/dossiers/{id}/custom-values/{champ}` | Pose la valeur : `{"value": …}`. Validée selon le type (422 `{code: "invalid_value", message}`, le message à afficher dans la cellule), tracée dans le journal (ancienne et nouvelle valeur, auteur ; rien si la valeur ne change pas). 404 pour un champ qui n'est pas celui de l'analyse du dossier, ou un dossier « à ranger ». Soumise à la règle d'[accès](acces-aux-dossiers.md) comme toute route du dossier. |

### Supprimer ou changer un champ

- Un champ **supprimé garde ses valeurs** en base : elles ne sont plus affichées, mais **reviennent** si on restaure une version qui contient le champ.
- Avec `purge_removed: true`, ses valeurs sont **supprimées définitivement** de tous les dossiers de l'analyse.
- Un champ dont le **type change** perd ses valeurs (elles n'auraient plus de sens) : l'interface prévient avant d'enregistrer.

### Valeurs par défaut

À la **création** d'un dossier, et au **rattachement** d'un dossier « à ranger » à l'analyse, chaque champ qui a une valeur par défaut la reçoit (sans écraser une valeur déjà saisie). Un champ ajouté plus tard ne remplit pas les dossiers existants.

## Dans le suivi

`GET /api/tracking` renvoie `values` pour chaque ligne (les champs **actuels** de l'analyse). Les colonnes personnalisées dépendent de l'analyse : leurs filtres et leur tri exigent **une seule `analyse_id`** (422 `single_analyse_required`).

| Paramètre | Rôle |
| --- | --- |
| `field_filters` | Un objet JSON `{identifiant du champ: filtre}` (4 000 caractères au plus). Texte : contenu, sans tenir compte de la casse (`%` et `_` sont ordinaires). Liste de choix : égalité. Oui/non : `"true"` ou `"false"` (« non » inclut les dossiers sans valeur, comme l'interface). Nombre, montant, date : `{"min": …, "max": …}`, bornes **incluses**, l'une ou l'autre facultative (virgule française acceptée). Les filtres se combinent entre eux et avec les autres. 422 `invalid_field_filter` si le JSON, un champ ou une borne est invalide. |
| `sort=field` + `sort_field` | Trie sur une colonne ; les nombres et montants **numériquement** (5 avant 15), les textes sans casse ; les dossiers **sans valeur restent en dernier** dans les deux sens. 422 `unknown_field` sinon. |
| `search` | Cherche aussi dans les **valeurs** des colonnes (en plus du nom et de la référence). |

Les valeurs d'un dossier qu'on ne voit pas ne sont ni listées, ni filtrables, ni trouvées par la recherche.

## Choix et limites

- **Qui définit les colonnes** : les administrateurs. Il n'existe pas encore de notion d'« administrateur d'une analyse » ; les rôles ([#178](https://github.com/IA-Generative/mille-feuille/issues/178)) pourront préciser. **Qui saisit une valeur** : toute personne qui voit le dossier.
- **Valeurs internes** : elles ne sont pas visibles de l'usager (hors périmètre, [#105](https://github.com/IA-Generative/mille-feuille/issues/105)). Le journal contient pourtant l'ancienne et la nouvelle valeur d'une colonne, comme le demande #173 ; à garder en tête pour la durée de conservation du journal ([#182](https://github.com/IA-Generative/mille-feuille/issues/182)).
- **Version de l'analyse** : comme les statuts et l'échéance, un changement de colonnes compte dans le numéro de version de l'analyse.
- **Pré-remplissage par l'IA** : hors périmètre ; la définition de chaque champ est prête à le guider (suite possible).
- **Pas de contrainte d'unicité ni de formule** : un champ est une valeur saisie, rien de calculé.
