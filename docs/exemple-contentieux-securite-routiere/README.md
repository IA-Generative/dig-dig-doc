# Exemple : contentieux de la sécurité routière (suspension du permis de conduire)

Un jeu de réglages pour **tester la plateforme sur un contentieux de sécurité routière** : un conducteur, représenté par son avocat, conteste devant le tribunal administratif l'arrêté préfectoral qui a suspendu son permis de conduire après un contrôle d'alcoolémie. Le dossier est vu par le **service du contentieux de la préfecture**.

Même organisation que [l'exemple de contentieux administratif](../exemple-contentieux-administratif/README.md) : un fichier par élément à recopier dans l'interface, et des pièces fictives à déposer.

> Toutes les données sont **fictives** : personnes, avocat, préfecture (« Préfecture de Valmont »), immatriculation, numéros de procès-verbal, d'appareil et de requête.

> **Les règles de droit et de métrologie des prompts sont celles d'un exemple de test**, simplifiées, écrites pour que les agents les appliquent sans se fier à leur mémoire. Elles doivent être validées par un juriste avant tout usage réel. Cet exemple ne donne aucun conseil juridique.

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
| [dossier-exemple/](dossier-exemple/) | Les 6 pièces (Markdown et PDF) et le scénario |

## Marche à suivre

1. Crée l'analyse (`01`), puis renseigne dans l'ordre : classification, extraction, agents, statuts, échéance, colonnes.
2. Crée un dossier rattaché à cette analyse et dépose les PDF de `dossier-exemple/pdf/`.
3. Lance l'analyse, puis compare à [dossier-exemple/00-scenario.md](dossier-exemple/00-scenario.md).

## Ce qui est particulier ici

- **Ici le délai est respecté.** Contrairement aux deux autres contentieux, il n'y a pas de piège de recevabilité : l'agent doit conclure qu'il n'y a **aucun signal**, sans en inventer.
- **Les faiblesses sont du côté de l'administration.** Le dossier révèle deux points qui jouent contre la préfecture : une heure d'infraction différente entre le procès-verbal et l'arrêté, et un appareil de mesure dont la vérification périodique était périmée au moment du contrôle. Les agents doivent les **signaler honnêtement**, même s'ils desservent la défense.
- **Allégué contre établi.** La requête affirme que le conducteur n'a pas été informé de son droit à un second contrôle ; le procès-verbal, signé, dit le contraire.
- **Une suspension qui court.** La suspension se termine le 9 septembre 2026 : à partir de cette date, la question de l'intérêt à poursuivre pourrait se poser. L'exemple ne tranche pas.
- **Aucun agent ne décide.** Ils signalent et préparent ; le service du contentieux et le juge décident.
