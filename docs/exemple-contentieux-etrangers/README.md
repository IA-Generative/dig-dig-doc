# Exemple : contentieux des étrangers (refus de titre de séjour et OQTF)

Un jeu de réglages pour **tester la plateforme sur un contentieux des étrangers** : une personne étrangère, représentée par son avocate et bénéficiaire de l'aide juridictionnelle, conteste devant le tribunal administratif un refus de titre de séjour assorti d'une obligation de quitter le territoire français (OQTF). Le dossier est vu par le **service du contentieux de la préfecture**, qui doit préparer sa défense.

Même organisation que [l'exemple de contentieux administratif](../exemple-contentieux-administratif/README.md) : un fichier par élément à recopier dans l'interface, et des pièces fictives à déposer.

> Toutes les données sont **fictives** : personnes, avocate, préfecture (« Préfecture de Valmont »), numéros d'étranger, numéros de requête. La **nationalité « valdorienne » est inventée** pour ne rattacher le cas à aucun pays réel.

> **Les règles de droit des prompts sont celles d'un exemple de test**, simplifiées, écrites pour que les agents les appliquent sans se fier à leur mémoire. Elles doivent être validées par un juriste avant tout usage réel. Cet exemple ne donne aucun conseil juridique, et ne préjuge d'aucune décision.

## Contenu

| Fichier | À recopier dans |
| --- | --- |
| [01-analyse.md](01-analyse.md) | Création de l'analyse |
| [02-classification.md](02-classification.md) | Classification : prompt + labels |
| [03-extraction.md](03-extraction.md) | Extraction : prompt + entités |
| [agents/](agents/) | Un fichier par agent |
| [05-statuts.md](05-statuts.md) | Statuts de dossier |
| [06-echeance.md](06-echeance.md) | Échéance |
| [07-colonnes-personnalisees.md](07-colonnes-personnalisees.md) | Colonnes du tableau de suivi |
| [dossier-exemple/](dossier-exemple/) | Les 7 pièces (Markdown et PDF) et le scénario |

## Marche à suivre

1. Crée l'analyse (`01`), puis renseigne dans l'ordre : classification, extraction, agents, statuts, échéance, colonnes.
2. Crée un dossier rattaché à cette analyse et dépose les PDF de `dossier-exemple/pdf/`.
3. Lance l'analyse, puis compare à [dossier-exemple/00-scenario.md](dossier-exemple/00-scenario.md).

## Ce qui est particulier ici

- **Un délai court, et une interruption.** Le délai de recours est de 30 jours, mais une demande d'aide juridictionnelle déposée à temps l'interrompt. La requête paraît tardive au premier calcul et ne l'est pas : c'est le piège principal, et il teste l'absence de **faux positif**.
- **L'identité compte.** Un numéro d'étranger transposé entre deux pièces est un signal à vérifier, pas une erreur à corriger en silence.
- **Ce que le requérant dit de sa vie en France.** Une durée de présence affirmée par la requête doit être confrontée à ce que la décision a retenu et à ce que les pièces établissent.
- **Données sensibles.** Le dossier concerne la situation personnelle et familiale d'une personne : les prompts demandent de s'en tenir aux faits des pièces, sans déduction sur la personne.
- **Aucun agent ne décide.** Ils signalent et préparent ; le service du contentieux et le juge décident.
