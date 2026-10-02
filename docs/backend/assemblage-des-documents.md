# Assemblage des documents générés

Issue #143, parent #107. Le document est assemblé de façon **déterministe**, jamais par le LLM : le modèle ODT ([#138](modeles-de-document.md)) est rempli par les valeurs **validées** du [brouillon](brouillons-de-document.md), par le worker `document_render` (#146), qui produit un **ODT** et un **PDF**.

## Routes

| Route | Effet |
| --- | --- |
| `POST /api/dossiers/{id}/document-drafts/{draft}/documents` `{confirm_incomplete?}` | Assemble le document. Chaque appel ajoute une version (201). |
| `GET /api/dossiers/{id}/generated-documents?draft_id=` | Documents du dossier, le plus récent d'abord. |
| `GET …/generated-documents/{doc}` | Détail : valeurs écrites, révision source, champs incomplets. |
| `GET …/generated-documents/{doc}/file?format=odt\|pdf&inline=` | Téléchargement. L'ODT est toujours téléchargé (à retoucher hors de l'application) ; le PDF peut s'afficher (`inline=true`, aperçu). |

Authentification requise ; **aucune route usager** : le document est interne (`visibility = "interne"`, prévu dès la première version pour #105). Pas d'envoi à l'usager.

## Quelles valeurs

Seules les valeurs **validées** entrent dans le document ; une valeur seulement proposée n'y entre pas. Mise en forme :

| Type | Écrit |
| --- | --- |
| texte | tel quel |
| date | `AAAA-MM-JJ` → `JJ/MM/AAAA` (autre texte inchangé) |
| nombre | virgule décimale (`1250,5`) |
| booléen | `oui` / `non` |
| liste | liste de textes, pour une boucle `{%p for a in adresses %}` ; hors boucle (`{{ adresses }}`), `a, b` |

Champ facultatif non validé : vide. `generated_at` (date du jour) et `document_version` sont posés à l'assemblage ; `analysis_revision` vient du brouillon : un modèle qui les définit comme champs peut écrire « analyse version N, document version M ».

**Champ obligatoire non validé** : la génération est **refusée** (409, avec `incomplete_fields`), sauf `confirm_incomplete: true` : il est alors écrit « [non renseigné] » (une liste : un élément « [non renseigné] ») et consigné dans `incomplete_fields` du document.

## Ce qui est conservé

`generated_documents` : version (par brouillon, en ajout seul), version du modèle, **révision de l'analyse source** (id et numéro), clés S3 de l'ODT et du PDF (`generated-documents/{dossier}/{brouillon}/v{n}.odt|pdf`), tailles, **valeurs écrites** (le contenu est figé et traçable), champs incomplets, auteur, date. Régénérer ajoute une version, l'ancienne reste intacte (valeurs et fichiers). Le brouillon n'est pas figé : on peut le corriger puis régénérer.

Le document est lié au dossier : ses lignes partent avec lui (cascade) et ses fichiers S3 sont supprimés par `DossierRepository.delete_dossier`. Un échec du rendu ou de l'enregistrement ne laisse aucun fichier partiel ; un worker muet donne un 503 et ne consomme pas de numéro de version. Les générations d'un même brouillon sont sérialisées.

## Décisions prises par défaut (à confirmer)

- **Contenu figé** à la génération, traçable ; régénérer crée une version liée à la révision du brouillon.
- **Retéléversement d'une version retouchée à la main** : non prévu ici.
- **Mise en forme officielle** (en-têtes, logos, signature) : portée par le modèle, pas ajoutée.
- **Champ obligatoire non validé** : bloque, avec confirmation explicite pour passer outre.

## Limites connues

- Une liste est une **liste de textes** : pas de tableau à plusieurs colonnes (liste d'objets) avec les types de champs actuels.
- Le numéro de version de l'analyse est écrit **dans le document** via un champ de modèle ; il n'est pas ajouté aux métadonnées du fichier ODT.
- Les dates sont écrites `JJ/MM/AAAA` seulement quand la valeur est au format ISO ; une date saisie autrement est reprise telle quelle.
- La génération est synchrone (le backend attend le worker, 180 s au plus) : adapté à un rendu d'une à quelques secondes, à revoir pour de gros documents.
