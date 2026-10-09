# Exemple : contentieux administratif (requête déposée par un avocat)

Un second jeu de réglages pour **tester la plateforme sur un dossier contentieux** : un usager, représenté par son avocat, conteste devant le tribunal administratif le refus d'une aide au logement. Le dossier est vu par le **service juridique de l'administration** qui doit préparer sa défense.

Même organisation que [l'exemple d'instruction](../exemple-instruction-administrative/README.md) : un fichier par élément à recopier dans l'interface, et des pièces fictives à déposer.

> Toutes les données (personnes, avocats, numéros de requête, adresses) sont **fictives**. Le dossier contient des anomalies **volontaires**.

> **Les règles de droit utilisées dans les prompts sont celles d'un exemple de test**, écrites pour que les agents les appliquent sans se fier à leur mémoire. Elles sont simplifiées : fais-les valider par un juriste avant tout usage réel. Cet exemple ne donne aucun conseil juridique.

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
| [dossier-exemple/](dossier-exemple/) | Les 6 pièces du dossier (Markdown et PDF) et le scénario attendu |

## Marche à suivre

1. Crée l'analyse (`01`), puis renseigne dans l'ordre : classification (`02`), extraction (`03`), agents, statuts, échéance, colonnes.
2. Crée un dossier rattaché à cette analyse et dépose les PDF de `dossier-exemple/pdf/`.
3. Lance l'analyse, puis compare le résultat à [dossier-exemple/00-scenario.md](dossier-exemple/00-scenario.md).

## Ce qui change par rapport à l'instruction d'une demande

- **Les dates décident.** Recevabilité, délais, prorogation par un recours gracieux : les agents doivent calculer avec la calculatrice, et les entités `date` sont plus nombreuses.
- **Le dossier est adverse.** Les pièces viennent du requérant : un agent doit distinguer ce que *prétend* la requête de ce que *prouvent* les pièces.
- **La plateforme prépare, une personne décide.** Aucun agent ne conclut à l'irrecevabilité : il signale et explique ; le service juridique décide.
- **Les agents ne lisent pas les réponses des autres** (voir [l'autre README](../exemple-instruction-administrative/README.md#comment-la-plateforme-enchaîne-les-étapes)) : chacun repart des classifications et des entités.
