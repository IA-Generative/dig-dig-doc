# Exemple : instruction d'une demande d'aide au logement

Un jeu complet de réglages pour **tester la plateforme sur un dossier administratif** : une analyse (classification, extraction, agents, statuts, échéance, colonnes de suivi) et un dossier fictif à déposer pour la faire tourner.

Chaque élément de l'analyse est dans **son propre fichier**, à recopier dans l'écran correspondant de l'interface.

> Toutes les données (personnes, adresses, IBAN, numéros) sont **fictives**. Le dossier contient des anomalies **volontaires** pour que les agents aient quelque chose à trouver.

## Contenu

| Fichier | À recopier dans |
| --- | --- |
| [01-analyse.md](01-analyse.md) | Création de l'analyse (nom, description) |
| [02-classification.md](02-classification.md) | Classification : prompt + labels |
| [03-extraction.md](03-extraction.md) | Extraction : prompt + entités (nom, définition, type) |
| [agents/](agents/) | Un fichier par agent : nom, outils, sortie, prompt |
| [05-statuts.md](05-statuts.md) | Statuts de dossier |
| [06-echeance.md](06-echeance.md) | Échéance : durée par défaut et seuils de couleur |
| [07-colonnes-personnalisees.md](07-colonnes-personnalisees.md) | Colonnes du tableau de suivi |
| [dossier-exemple/](dossier-exemple/) | Les pièces du dossier à déposer, et le scénario attendu |

## Marche à suivre

1. Crée l'analyse (`01`), puis renseigne dans l'ordre : classification (`02`), extraction (`03`), agents, statuts, échéance, colonnes.
2. Crée un dossier rattaché à cette analyse et dépose les pièces de `dossier-exemple/`. Dépose les PDF de `dossier-exemple/pdf/` (les sources Markdown sont à côté).
3. Lance l'analyse, puis compare le résultat à [dossier-exemple/00-scenario.md](dossier-exemple/00-scenario.md), qui liste ce que chaque agent doit trouver.

## Comment la plateforme enchaîne les étapes

D'après le code du worker (`worker/agent_execution`) :

- La **classification** s'applique page par page ; l'**extraction** document par document, par groupes de 8 définitions ([extraction-par-document.md](../backend/extraction-par-document.md)). Les prompts que tu écris sont donc ajoutés au début d'une consigne fixe : ne répète pas le format de réponse JSON, il est imposé.
- Les **agents** attendent la fin de la classification et de l'extraction, puis lisent le dossier avec quatre outils : recherche dans les documents, lecture d'une page, classifications, entités. Leur réponse est du texte libre (Markdown), limitée à environ 2 000 jetons : les prompts demandent donc des sorties courtes.
- Je n'ai pas trouvé de mécanisme par lequel un agent lit la réponse d'un autre : chaque agent de cet exemple part des classifications et des entités, pas des autres agents.
- Les outils cochés dans l'interface (`lecture_document`, `verification_coherence`…) sont déclaratifs d'après le code actuel : le worker expose toujours les mêmes outils de lecture.

## Pourquoi ces choix

- **Classification fine** (7 labels) : elle sert de base à la complétude (quelles pièces sont présentes) et guide les agents.
- **Entités typées** : `nombre` et `date` permettent des comparaisons fiables (revenu, dates de validité) ; `identifiant` pour l'IBAN et le numéro de pièce.
- **Quatre agents indépendants**, un par question de l'instructeur : *le dossier est-il complet ? est-il cohérent ? y a-t-il des signaux d'anomalie ? que dois-je décider ?* Ils peuvent donc être relancés séparément.
