# Analyse de dossier : la vue de l'instructeur

Issue : [#116](https://github.com/IA-Generative/dig-dig-doc/issues/116) (parent [#106](https://github.com/IA-Generative/dig-dig-doc/issues/106)).

L'analyse de dossier est le document de travail d'un dossier : **une analyse par exécution**, faite d'éléments (classifications, entités, relations, synthèses, champs) qui ont chacun plusieurs versions. Cette page permet à l'instructeur de la **consulter**, de voir d'où vient chaque valeur, de **l'enrichir**, de **revenir à une version antérieure** et de traiter les **propositions de modification**. Elle est interne : elle n'est jamais montrée aux usagers.

## Y accéder

Dans l'en-tête d'un dossier, l'icône « liste » (à gauche de l'icône assistant) ouvre `/dossiers/<id>/analyse`.

![Icône d'accès à l'analyse dans l'en-tête du dossier](lien-depuis-le-dossier.png)

## La vue

![Vue de l'analyse de dossier](analyse-dossier.png)

- **Exécution :** le sélecteur en haut à droite permet de consulter les exécutions précédentes. Seule l'analyse la plus récente est modifiable ; les autres sont en lecture seule, et une analyse **figée** ne se modifie plus.
- **Éléments** groupés par type. Chaque élément indique sa **provenance** : *Modèle*, *Instructeur* (avec l'auteur) ou *Reprise*, la page, la confiance du modèle, et la **valeur du modèle** quand un instructeur l'a remplacée (elle n'est jamais écrasée).
- **« À revoir »** : signale un élément validé dont les entrées ont changé (relance de l'analyse), avec le motif.
- **Modifier** apporte une nouvelle valeur ; le **motif est obligatoire**. Les relations ne s'éditent pas en texte (restauration seulement).
- **Ajouter un élément à la main** en bas de page.

## Propositions en attente

![Une proposition en cours de modification](modifier-une-proposition.png)

Une proposition (par exemple issue du chat ou d'une note) n'applique **rien** tant que l'utilisateur ne l'a pas traitée :
- **Accepter** : crée une version avec la valeur proposée ;
- **Modifier** : accepte avec une autre valeur ;
- **Rejeter** : n'applique rien.

La valeur actuelle et la valeur proposée sont comparées mot à mot. Si l'élément a été modifié entre-temps, le serveur refuse d'appliquer la proposition (elle peut être rejetée). Chaque décision est journalisée côté serveur (#114).

## Historique et restauration

![Historique d'un élément avec les différences entre versions](historique-et-differences.png)

Le bouton **Historique** liste toutes les versions d'un élément, avec ce qui a changé de l'une à l'autre. **Restaurer** une version en **ajoute** une nouvelle (rien n'est supprimé ni modifié).

## Code

- `frontend/src/pages/DossierAnalysisPage.vue` : la page ; route `dossier-analysis` dans `router/index.ts`.
- `frontend/src/composables/useDossierAnalysis.ts` : chargement et actions (modifier, restaurer, accepter, modifier ou rejeter une proposition).
- `frontend/src/components/analysis/ProposalCard.vue` : carte de proposition, **réutilisable** dans le chat du dossier (#115).
- `frontend/src/components/analysis/ElementHistoryModal.vue` : historique et restauration.
- `frontend/src/types/dossierAnalysis.ts`, `frontend/src/utils/textDiff.ts` : types, textes de valeurs, différence mot à mot.
- API utilisée : routes `/api/dossiers/{id}/analyses-dossier/...` (#112, #114).

## À propos des captures

Les images montrent l'interface réelle sur la stack de dev, mais **les données de l'analyse sont simulées** (réponses de l'API interceptées par le script de capture) : le backend en cours d'exécution sur cette stack tournait sur une image antérieure, sans ces routes. Le comportement avec un vrai backend n'a donc pas été vu dans le navigateur. Le script de capture n'est pas versionné ; pour les régénérer, lancer la stack à jour, créer une analyse via l'API, puis capturer `/dossiers/<id>/analyse`.
