# Extraction

Appliquée **par document**, par groupes de 8 définitions ([extraction-par-document.md](../backend/extraction-par-document.md)). Les 24 entités ci-dessous forment exactement 3 groupes de 8, dans l'ordre de la liste.

Le format de réponse (entité, valeur, pages) est imposé par la plateforme.

## Prompt

```text
Tu extrais des informations de pièces d'un dossier contentieux de sécurité routière devant un tribunal administratif.

Règles :
- Recopie la valeur telle qu'elle figure dans le document, sans la corriger ni l'interpréter. Exception : normalise les dates au format AAAA-MM-JJ et les montants et mesures en nombre (le taux d'alcool en mg/L avec un point décimal : « 0,62 » devient 0.62).
- Recopie les immatriculations et numéros d'appareil caractère par caractère.
- N'invente rien. Si une information n'est pas dans le texte, n'inclus pas l'entité.
- Si une même information apparaît plusieurs fois avec des valeurs différentes dans le même document, renvoie chaque valeur. Cela vaut surtout pour l'heure de l'infraction : relève-la chaque fois qu'elle apparaît, avec sa source.
- Une information « alléguée » par la requête et une information « constatée » par le procès-verbal ou l'arrêté sont des entités distinctes : n'attribue pas à l'une la valeur de l'autre.
```

## Entités

### Juridiction et parties

| Nom | Type | Définition |
| --- | --- | --- |
| Juridiction | texte | Tribunal saisi. |
| Numéro de la requête | identifiant | Numéro d'enregistrement de la requête au greffe. |
| Date d'enregistrement de la requête | date | Date à laquelle le greffe a enregistré la requête. |
| Nom du requérant | texte | Nom et prénom du conducteur qui saisit le tribunal. |
| Date de naissance du requérant | date | Date de naissance indiquée. |
| Nom de l'avocat du requérant | texte | Avocat qui signe la requête. |
| Barreau de l'avocat | texte | Barreau auquel il est inscrit. |
| Autorité défenderesse | texte | Autorité dont l'arrêté est contesté. |

### Arrêté et faits constatés

| Nom | Type | Définition |
| --- | --- | --- |
| Objet de la décision attaquée | texte | Ce que décide l'arrêté, en quelques mots. |
| Date de l'arrêté | date | Date portée sur l'arrêté de suspension. |
| Durée de la suspension | nombre | Durée de la suspension, en mois. |
| Date de fin de la suspension | date | Date à laquelle la suspension prend fin, d'après l'arrêté. |
| Date de notification prouvée | date | Date de remise de l'arrêté établie par une pièce. |
| Mention des voies et délais de recours | booléen | Vrai si l'arrêté indique les voies et délais de recours. |
| Date de l'infraction | date | Date du contrôle, chaque fois qu'elle apparaît. |
| Heure de l'infraction | texte | Heure du contrôle ou de l'infraction, telle qu'écrite, avec la pièce d'où elle vient. |

### Mesure, appareil et suites

| Nom | Type | Définition |
| --- | --- | --- |
| Taux d'alcool relevé | nombre | Taux d'alcool dans l'air expiré, en mg/L. |
| Immatriculation du véhicule | identifiant | Immatriculation du véhicule contrôlé. |
| Numéro de l'éthylomètre | identifiant | Numéro d'identification de l'appareil de mesure. |
| Date de la dernière vérification de l'appareil | date | Date de vérification périodique indiquée sur le certificat de l'appareil. |
| Information sur le second contrôle | booléen | Vrai si le procès-verbal indique que le conducteur a été informé de son droit de demander un second contrôle, faux si le procès-verbal ne le dit pas. |
| Date limite de production du mémoire en défense | date | Date avant laquelle l'administration doit produire son mémoire, d'après le greffe. |
| Date de clôture d'instruction | date | Date de clôture fixée par le greffe. |
| Frais irrépétibles demandés | nombre | Somme demandée au titre des frais de procédure, en euros. |
