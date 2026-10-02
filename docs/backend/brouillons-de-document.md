# Brouillons de document (backend)

Issue #140, parent #107. Un **brouillon** lie un modèle (une version précise, [#138](modeles-de-document.md)) à un dossier et à une **révision précise de l'analyse** (`AnalysisRevision` : une version retenue par élément). Interne : aucune route usager (#96).

## Création

`POST /api/dossiers/{id}/document-drafts` `{template_id, revision_id?}`. Sans `revision_id`, un instantané de l'analyse courante est pris ; avec, la révision donnée (d'une analyse du dossier). L'analyse peut ensuite évoluer : le brouillon garde les valeurs de sa révision. Un modèle archivé ou un dossier sans analyse est refusé (409).

Valeur de départ de chaque champ, selon sa source :

| Source | Valeur de départ |
| --- | --- |
| `analysis` | Valeur retenue de l'élément de même type et même nom dans la révision : **proposée**. Un champ `list` reprend toutes les occurrences, les autres la première (page la plus basse). Rien trouvé : non renseigné. |
| `instruction` | Si l'analyse a déjà un élément `field` de même nom (renseigné par un autre document du dossier), sa valeur est reprise, **proposée** ; sinon non renseigné. Les valeurs « renseignées » sont donc partagées par nom entre les modèles d'un même dossier. |
| `dossier_metadata` | Un fait du dossier : **validé** d'office. `analysis_revision` (numéro de la révision de l'analyse) est posée à la création ; `generated_at` et `document_version` sont posées à l'assemblage (#143) et ne comptent pas dans la complétude. |

## Valeurs de champs

En **ajout seul** : modifier, valider, rejeter, restaurer ou proposer ajoute une version ; la dernière est l'état courant. Statut : `non_renseigné`, `proposé`, `validé`. Origine : `analysis`, `agent`, `instructor`. Chaque version porte ses `sources` (éléments de l'analyse, pages, métadonnée), son auteur et, pour l'agent, la version du prompt et le modèle.

| Route | Effet |
| --- | --- |
| `PUT /{draft}/fields/{nom}` | Saisie à la main, validée d'office. Même valeur que la proposition : « accepté ». |
| `POST …/fields/{nom}/validate` | Accepte la valeur proposée telle quelle. |
| `POST …/fields/{nom}/reject` | Écarte la proposition : le champ redevient non renseigné. |
| `POST /{draft}/validate` `{names?}` | Accepte d'un coup (toutes les propositions, ou celles données) ; tout ou rien. |
| `GET …/fields/{nom}/versions`, `POST …/restore` | Historique ; reprise d'une version (validée d'office). |
| `GET /{draft}/completeness` | Champs obligatoires non renseignés (`missing`) ou seulement proposés (`proposed`). |
| `GET /{draft}/events?field=` | Journal des décisions. |
| `POST /{draft}/archive` | Brouillon archivé : consultable, plus modifiable. |

Types : texte et date (non vide), nombre (accepte `"1 250,5"`), booléen (oui/non), liste de textes. Une valeur de l'analyse, toujours du texte, est typée si possible sinon laissée telle quelle (c'est une proposition).

### Une valeur validée n'est jamais réécrite automatiquement

`DocumentDraftRepository.propose` (utilisé par l'agent de génération, #141) refuse (`ValidatedFieldError`) tout champ `validé`, y compris une métadonnée du dossier. Seule une personne change une valeur validée. Une proposition non validée peut être régénérée.

### Recopie dans l'analyse

À la validation (saisie, acceptation ou restauration) d'un champ « renseigné au fil de l'instruction », la valeur est écrite dans l'analyse comme élément `field` (nom du champ = `definition_name`) : nouvel élément la première fois, nouvelle version ensuite (rien si la valeur est identique). Il hérite des versions, propositions, notes, du verrou et de la reprise à la relance. Les champs tirés de l'analyse ne sont **pas** recopiés. Si l'analyse est figée, la valeur est validée dans le brouillon mais pas recopiée (le journal le précise).

## Journal

`document_field_events`, en ajout seul : `proposed`, `accepted`, `modified`, `rejected`, `regenerated`, `restored`, avec auteur, **durée** entre la proposition et la décision (vide si rien n'était proposé), version du prompt, modèle, sources et précision (consigne de régénération, motif de rejet, recopie dans l'analyse). Pour les métriques de qualité (#145).

## Décisions prises par défaut (à confirmer)

- **Valeurs « renseignées » partagées par nom** entre les modèles d'un dossier, via l'élément `field` de l'analyse (pas d'espace de noms par modèle).
- **Champ obligatoire non validé** : exposé par la complétude ; c'est l'assemblage (#143) qui bloque, avec confirmation explicite pour passer outre.
- **Mise à jour depuis une analyse plus récente** : non faite, le brouillon reste lié à sa révision.
- **Verrou par champ** : non fait ; la saisie la plus récente gagne et chaque version est conservée. À traiter avec l'écran de revue (#142).
- **Fichier figé à la génération** : le contenu est figé dans le *document généré* ([assemblage](assemblage-des-documents.md)), pas dans le brouillon, qui reste modifiable pour régénérer une nouvelle version.
