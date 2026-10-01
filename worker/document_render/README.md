# Worker `document_render`

Remplit un **modèle ODT** avec des valeurs, puis produit un **PDF** avec LibreOffice (issue #146, parent #107 : document de fin d'instruction).

- **Remplissage** : moteur maison (`app/odt_template.py`, lxml + Jinja en bac à sable). LibreOffice n'intervient pas ici.
- **PDF** : `soffice --headless` (`app/pdf.py`), uniquement pour l'aperçu et l'export.
- **Pas d'édition en ligne** (WOPI/Collabora écartés) : on édite les valeurs dans le formulaire, l'aperçu est le PDF.

## Tâches Celery (file `document_render`)

| Tâche | Rôle |
| --- | --- |
| `extract_template_fields(template_key)` | Liste les champs du modèle (triés, variables de boucle exclues). |
| `render_document(template_key, values, output_prefix, with_pdf=True)` | Dépose `<prefix>.odt` (et `<prefix>.pdf`) dans S3, renvoie les clés. |
| `render_preview(template_key, values, output_key)` | Dépose seulement le PDF. |

Un champ sans valeur est une **erreur** (`MissingValueError` nommant le champ) : on ne génère jamais un document à trous. Rien n'est déposé en cas d'échec.

## Écrire un modèle (dans LibreOffice Writer)

- Champ : `{{ nom }}`, ou `{{ dossier.adresse }}` pour un objet. Fonctionne dans le corps, les tableaux et les en-têtes/pieds de page.
- LibreOffice coupe parfois un champ en plusieurs morceaux de style (`{{ pre` + `nom }}`) : c'est recollé automatiquement ; le champ prend le style du premier morceau.
- Répéter des **lignes de tableau** : une ligne ne contenant que `{%tr for e in entites %}`, la ligne modèle avec `{{ e.nom }}`, une ligne `{%tr endfor %}`. Les lignes de contrôle disparaissent.
- Répéter des **paragraphes** : `{%p for … %}` / `{%p endfor %}` ; des **puces** : `{%li for … %}` / `{%li endfor %}` — chacun seul dans son paragraphe.
- Dans un même paragraphe : `{% if … %}…{% endif %}` et `{% for … %}…{% endfor %}` classiques.
- Les balises de bloc (`{%tr`, `{%p`, `{%li`) doivent être **seules** dans leur ligne/paragraphe/puce ; sinon erreur explicite.
- Les valeurs sont échappées (`& < >`), les retours à la ligne, tabulations et espaces multiples sont conservés.
- Expressions dangereuses (`''.__class__`) refusées par le bac à sable.

## Décisions et mesures du spike

| Sujet | Résultat |
| --- | --- |
| Bibliothèque de remplissage | `secretary` écartée : incompatible avec Jinja2 ≥ 3.1 et échoue sur les champs fragmentés. Moteur maison (~300 lignes, testé). |
| Conversion PDF | `soffice --headless --convert-to pdf` : ~0,9 s par document à chaud ; ~1,1 s tâche Celery + S3 de bout en bout. |
| UNO (processus LibreOffice persistant) | Écarté : image plus lourde (759 Mo, 2ᵉ interpréteur Python) pour un gain inutile à ce volume. |
| Image | ~800 Mo (`libreoffice-writer-nogui` + polices). |
| Concurrence | Un profil LibreOffice temporaire par conversion : 3 conversions simultanées OK. |
| Sécurité | Macros désactivées, délai maximal (groupe de processus tué), entrée vérifiée avant LibreOffice (qui convertirait sinon n'importe quel texte en PDF). |

## Limites connues (à traiter dans les issues suivantes)

- **Fidélité** : celle des polices installées dans l'image. Une police propriétaire absente est remplacée sans erreur ; à vérifier avec les vrais modèles de la DDT (non disponibles pour ce spike). Penser à un contrôle des polices du modèle.
- Seuls `content.xml` et `styles.xml` sont rendus : pas de champ dans les métadonnées ni dans les en-têtes d'objets/cadres hors flux non testés.
- Les champs de formulaire LibreOffice natifs (champs utilisateur, variables) ne sont pas supportés : uniquement la syntaxe `{{ … }}`.
- Images dynamiques (signature, logo variable) : non traité.
- Déploiement (images CD, Helm/KEDA, release-please) : non fait, voir l'issue de suivi.

## Développement

```bash
cd worker/document_render
uv sync --group dev
uv run pytest                 # les tests marqués `libreoffice` sont ignorés sans soffice
```

Tests avec LibreOffice réel, dans l'image :

```bash
docker build -t dd-render worker/document_render
docker run --rm -v "$PWD/worker/document_render":/src:ro -e HOME=/tmp --entrypoint sh dd-render -c \
  'cp -r /src /tmp/w && cd /tmp/w && rm -rf .venv && pip install -q --target /tmp/pt pytest && \
   PYTHONPATH=/tmp/pt:/tmp/w /app/.venv/bin/python -m pytest -q -p no:cacheprovider'
```
