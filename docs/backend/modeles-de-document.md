# Modèles de document (backend)

Issue #138, parent #107. Le modèle est un fichier **ODT** à placeholders `{{ nom }}` (syntaxe : [worker/document_render/README.md](../../worker/document_render/README.md)) et la **définition de ses champs**. Tout est réservé aux **administrateurs** (`/api/admin/document-templates`).

## Versions

Tout ce qui s'édite (nom, description, consignes de génération, champs, fichier) est porté par la **version**, jamais modifiée : modifier ou restaurer **ajoute** une version. Seul l'archivage est un état du modèle (un modèle archivé ne se modifie pas). Les versions qui ne changent pas le fichier le partagent dans S3 (`document-templates/<id>/v<n>.odt`). Le nom est unique, casse ignorée.

## Définition d'un champ

| Propriété | Sens |
| --- | --- |
| `name` | Nom stable = nom du placeholder (identifiant ; `loop`, `true`… réservés). |
| `label`, `type` | Libellé affiché ; `text`, `date`, `number`, `list`, `boolean`. |
| `required` | Obligatoire ou non. |
| `instruction` | Consigne propre au champ pour l'agent de génération (#141). |
| `source` | D'où vient la valeur (ci-dessous). |

Sources :
- `{"kind": "analysis", "element_kind": "classification|entity|relation|synthesis|field", "definition_name": "…", "selection": "retained_or_predicted"}` : donnée de l'analyse, valeur retenue sinon prédite. Un champ de type `list` reprend toutes les occurrences, les autres la première. **À valider avec les métiers** (quelle occurrence d'une entité répétée).
- `{"kind": "instruction"}` : renseigné au fil de l'instruction (décision, motif, commentaire).
- `{"kind": "dossier_metadata", "key": "dossier_name|dossier_id|dossier_created_at|dossier_started_at|dossier_ended_at|instructor_name|instructor_email|generated_at"}`.

## Validation à l'import

Les placeholders sont lus par le worker `document_render` (tâche `extract_template_fields`, résultat attendu 30 s). Ils sont comparés aux champs définis **dans les deux sens** : un placeholder sans champ, ou un champ absent du fichier, **refuse la version** (422) avec un rapport :

```json
{"detail": {"message": "…", "unknown_placeholders": ["adresse"], "unused_fields": ["motif"]}}
```

Fichier illisible pour le worker : 422 avec son message. Worker injoignable : 503. Le backend vérifie avant tout que le fichier est un ODT (zip + type), 10 Mo maximum.

## Routes

| Route | Rôle |
| --- | --- |
| `POST /inspect` | Lit un fichier sans rien enregistrer : renvoie ses placeholders (il faut les connaître pour définir les champs). |
| `GET /`, `GET /{id}` | Liste (`include_archived`) et lecture, version courante. |
| `POST /` | Crée (multipart : `name`, `description`, `generation_instructions`, `fields` en JSON, `file`). |
| `POST /{id}/versions` | Ajoute une version avec l'état complet ; sans `file`, garde le fichier courant. |
| `GET /{id}/versions`, `GET /{id}/versions/{n}/file` | Historique ; téléchargement du fichier d'une version. |
| `POST /{id}/restore` | `{version_id}` : ajoute une version qui reprend tout, fichier compris. |
| `POST /{id}/archive`, `/unarchive` | Archivage. |

## Décisions prises (à confirmer)

Les quatre points ouverts de l'issue ont été tranchés par défaut : administrateurs seuls ; une définition de champs **par modèle** (pas de bibliothèque partagée) ; un écart de placeholder **bloque** ; une seule règle de sélection pour l'instant.
