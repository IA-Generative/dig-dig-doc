# Migration des validations de prédiction vers l'analyse de dossier

Issue : [#120](https://github.com/IA-Generative/mille-feuille/issues/120) (parent [#106](https://github.com/IA-Generative/mille-feuille/issues/106)). Migration `3c4d5e6f7a8b`.

## Avant / après

- **Avant :** une décision de l'instructeur sur une prédiction (validé, corrigé, rejeté) était une ligne de `prediction_validations`.
- **Après :** c'est une **version d'instructeur** de l'élément de l'analyse de dossier qui porte la prédiction (`analysis_element_versions`), avec la valeur retenue, l'auteur, la date et la zone corrigée. L'historique de l'élément, la restauration et les propositions (#112, #114) s'appliquent donc aussi aux validations.

La route `PUT /api/dossiers/{id}/documents/{doc}/pages/{page}/predictions/{prediction}/validations` **garde son contrat** (mêmes entrées et sorties, mêmes `validations` sur les prédictions). Elle écrit désormais dans l'analyse de dossier, et `prediction_validations` n'est **plus alimentée** (sa suppression viendra dans une migration ultérieure).

## Correspondance

| Ancien | Nouveau |
|---|---|
| ligne `prediction_validations` | version d'élément, provenance `instructor`, `validation_status` = `validé` / `corrigé` / `rejeté` |
| `corrected_value` | valeur de la version (`label` d'une classification, `value` d'une entité) |
| zone corrigée (`bounding_box_id`) | `bounding_box_id` de la version (nouvelle colonne) |
| validé | la valeur retenue est confirmée |
| rejeté | la valeur est conservée et l'élément est marqué **« à revoir »** (le modèle d'analyse n'a pas d'état « rejeté ») |
| `validator_user_id`, `created_at` | `author_id`, `created_at` |

Chaque version migrée porte `source_type = prediction_validation` et `source_id` = l'identifiant de la validation d'origine : c'est ce qui rend la migration **idempotente** et vérifiable.

## Ce que fait la migration

1. Ajoute `validation_status` et `bounding_box_id` sur `analysis_element_versions`.
2. Pour chaque prédiction qui n'a pas encore d'élément, crée l'élément (version « modèle ») dans une **analyse de rattrapage** par dossier : les exécutions passées ne sont pas reconstituables, tout est donc regroupé. Cette analyse est repérée par `analyse_version = "rattrapage (migration #120)"`.
   - Elle n'est **jamais l'analyse courante** : si le dossier a déjà des analyses, elle reçoit un numéro d'exécution plus ancien que la plus ancienne (donc `0` si celle-ci est la n° 1).
3. Pour toutes les prédictions ayant des validations non migrées (y compris celles qui ont déjà un élément, créé depuis #125), ajoute une version d'instructeur par validation, dans l'ordre chronologique. La dernière devient la version retenue.
4. **Vérifie le comptage** : nombre de validations migrées = nombre attendu, et nombre de versions migrées = nombre de validations en base. En cas d'écart, la migration échoue et **rien n'est appliqué** (DDL transactionnel).

Les prédictions sans aucune page (page supprimée) n'appartiennent plus à un dossier : elles et leurs validations sont ignorées, et exclues du comptage.

## Retour arrière

`alembic downgrade -1` supprime les analyses de rattrapage (avec leurs éléments et versions) et les versions migrées d'analyses existantes, puis retire les deux colonnes. `prediction_validations` n'ayant jamais été modifiée, l'ancien comportement est retrouvé.

> **Attention :** les validations faites **après** la migration (via la route) ne sont écrites que dans l'analyse de dossier. Si elles sont portées par une analyse de rattrapage ou par une version migrée, elles sont perdues au retour arrière ; les autres restent dans l'analyse mais ne sont plus lues. Faire une sauvegarde avant de migrer une base réelle.

## Avant de migrer une base réelle

- Sauvegarder la base.
- Compter `SELECT count(*) FROM prediction_validations` avant, et après : `SELECT count(*) FROM analysis_element_versions WHERE source_type = 'prediction_validation'` doit être égal (hors validations de prédictions sans page).
- Les analyses de rattrapage apparaissent dans la vue de l'analyse du dossier comme une exécution antérieure.

## Code

- `backend/migrations/versions/*_3c4d5e6f7a8b_*.py` : migration, fonction `backfill` testée telle quelle.
- `backend/app/services/prediction_validation.py` : écriture d'une validation dans l'analyse de dossier.
- `backend/app/models/document_page.py` : `DocumentPrediction.validations` est maintenant calculé à partir des versions d'élément.
- `backend/tests/test_prediction_validations.py` : route et migration (16 tests).
