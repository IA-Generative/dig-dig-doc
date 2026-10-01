# Extraction par document, groupes de définitions et empreintes

Issue : [#126](https://github.com/IA-Generative/dig-dig-doc/issues/126) (parent [#113](https://github.com/IA-Generative/dig-dig-doc/issues/113)). Prépare la relance incrémentale ([#119](https://github.com/IA-Generative/dig-dig-doc/issues/119)).

## Pourquoi

Avant, l'extraction découpait **toutes les pages du dossier** en lots de 5, tous documents confondus, avec **toutes les définitions dans un seul appel**. Conséquences :
- ajouter ou retirer une page décalait tous les lots suivants : tout aurait été recalculé à la moindre modification ;
- une entité qui s'étend sur deux lots était tronquée (ses pages sont filtrées sur celles du lot) ;
- les numéros de page sont propres à chaque document, mais la correspondance numéro → page était commune à tout le dossier : avec deux documents ayant chacun une page 1, une entité trouvée dans le second pouvait être rattachée à la page 1 du premier.

## Le nouveau découpage

Pour chaque **document**, chaque **groupe de définitions** et chaque **lot de pages**, un appel au LLM = une **unité de calcul** (voir #112).

1. **Par document** : aucun lot ne chevauche deux documents.
2. **Lots définis par un budget de jetons**, pas par un nombre de pages. Le budget compte ensemble le texte du lot, les définitions du groupe, le prompt, l'instruction fixe et la réponse attendue. Un document qui tient dans le budget donne un seul lot ; une page plus grande que le budget forme son propre lot (elle n'est pas coupée).
3. **Recouvrement** d'une page entre deux lots consécutifs d'un même document, pour ne pas couper une entité. Les doublons qui en résultent (même définition, même valeur, casse et espaces ignorés) sont fusionnés.
4. **Groupes de définitions de taille fixe**, dans l'ordre de la liste de l'analyse. Ajouter une définition **à la fin** ne change que le dernier groupe ; en insérer une **au milieu** décale les suivants (ils seront recalculés).

Les jetons sont **estimés** (un jeton ≈ 4 caractères), sans dépendance à un tokenizer : c'est une approximation.

## Les empreintes

Chaque unité est déclarée au backend avec l'**empreinte de ses entrées** (`input_fingerprint`, sha256) :

| Unité | Entrées hachées |
|---|---|
| Classification (une page) | texte de la page, capture (clé S3), labels, prompt, modèle LLM et modèle VLM |
| Extraction (lot × groupe) | texte de chaque page du lot (dans l'ordre), définitions du groupe, prompt, modèle |
| Agent (une étape) | prompt, outils, modèle de l'agent **et** empreintes des unités de classification et d'extraction qu'il lit |

Toutes incluent une **version du pipeline** (`PIPELINE_VERSION` côté worker, `AGENT_PIPELINE_VERSION` côté backend) à incrémenter quand la logique d'une étape change de façon à modifier ses résultats.

Une empreinte ne dépend **ni de la valeur du résultat, ni des identifiants** de page ou d'exécution : deux exécutions aux entrées identiques donnent les mêmes empreintes. Elles servent à la **relance incrémentale** (#119) : une unité dont l'empreinte est inchangée est reprise de l'analyse précédente au lieu d'être recalculée (voir `relance-incrementale.md`).

## Réglages (worker)

| Variable | Défaut | Rôle |
|---|---|---|
| `EXTRACTION_MODE` | `by_document` | `legacy` restaure l'ancien comportement (lots de `EXTRACTION_BATCH_SIZE` pages sur tout le dossier, toutes les définitions en un appel) |
| `EXTRACTION_MAX_TOKENS` | `8000` | budget total d'un appel |
| `EXTRACTION_RESERVED_OUTPUT_TOKENS` | `1500` | part réservée à la réponse |
| `EXTRACTION_OVERLAP_PAGES` | `1` | pages communes entre lots consécutifs |
| `EXTRACTION_DEFINITIONS_PER_GROUP` | `8` | taille des groupes (`0` : un seul groupe) |
| `EXTRACTION_BATCH_SIZE` | `5` | mode `legacy` uniquement |

**Ces valeurs sont des points de départ, pas des valeurs mesurées.** Elles doivent être ajustées sur de vrais dossiers, avec la fenêtre de contexte du modèle utilisé (`LLM_MODEL`).

## Ce qui n'est pas mesuré

- **La qualité d'extraction** : le nouveau découpage change ce que voit le LLM à chaque appel (moins de contexte par appel, mais plus d'appels). À comparer avant/après sur de vrais dossiers : entités trouvées, entités manquantes ou en trop, confiance.
- **Le coût** : plusieurs groupes de définitions renvoient le même texte au LLM.
- **La fusion des doublons** écarte aussi une valeur légitimement répétée (même définition, même valeur) à plusieurs endroits d'un même document.

Pour revenir en arrière le temps de la validation : `EXTRACTION_MODE=legacy` sur le worker `agent_execution` (les empreintes sont alors calculées aussi, sur l'ancien découpage). Ce mode garde l'ancien défaut de correspondance des numéros de page entre documents.

## Code

- `worker/agent_execution/app/extraction_planner.py` : groupes, budget, lots, doublons (fonctions pures).
- `worker/agent_execution/app/fingerprint.py` : empreintes.
- `worker/agent_execution/app/tasks/extraction.py`, `classification.py` : unités déclarées avec leur empreinte.
- `backend/app/services/analysis_builder.py` : empreinte des unités d'agent.
- Tests : `worker/agent_execution/tests/test_extraction_planner.py`, `test_tasks.py` ; `backend/tests/test_analysis_generation.py`.
