# Extraction

Appliquée **par document**, par groupes de 8 définitions ([extraction-par-document.md](../backend/extraction-par-document.md)). Les 22 entités ci-dessous forment 3 groupes (8, 8 et 6), dans l'ordre de la liste.

Le format de réponse (entité, valeur, pages) est imposé par la plateforme.

## Prompt

```text
Tu extrais des informations de pièces d'un dossier contentieux des étrangers devant un tribunal administratif.

Règles :
- Recopie la valeur telle qu'elle figure dans le document, sans la corriger ni l'interpréter. Exception : normalise les dates au format AAAA-MM-JJ et les montants en nombre (sans symbole ni espace).
- Recopie les numéros d'identification caractère par caractère, sans les corriger, même s'ils te semblent erronés.
- N'invente rien. Si une information n'est pas dans le texte, n'inclus pas l'entité.
- Une information « alléguée » par la requête (ce que l'avocate affirme) et une information « retenue » par l'arrêté ou « prouvée » par une pièce sont des entités distinctes : n'attribue pas à l'une la valeur de l'autre.
- Si une même information apparaît plusieurs fois avec des valeurs différentes dans le même document, renvoie chaque valeur.
- Tu ne déduis rien sur la personne (origine, situation familiale non écrite, intentions). Tu extrais ce qui est écrit.
```

## Entités

### Juridiction et parties

| Nom | Type | Définition |
| --- | --- | --- |
| Juridiction | texte | Tribunal saisi. |
| Numéro de la requête | identifiant | Numéro d'enregistrement de la requête au greffe. |
| Date d'enregistrement de la requête | date | Date à laquelle le greffe a enregistré la requête. |
| Nom du requérant | texte | Nom et prénom de la personne qui saisit le tribunal. |
| Date de naissance du requérant | date | Date de naissance indiquée. |
| Numéro d'étranger | identifiant | Numéro d'étranger du requérant (numéro attribué par l'administration), tel qu'écrit. |
| Nom de l'avocat du requérant | texte | Avocat qui signe la requête. |
| Barreau de l'avocat | texte | Barreau auquel il est inscrit. |

### Décision attaquée et notification

| Nom | Type | Définition |
| --- | --- | --- |
| Autorité défenderesse | texte | Autorité dont la décision est contestée. |
| Objet de la décision attaquée | texte | Ce que décide l'arrêté, en quelques mots. |
| Date de la décision attaquée | date | Date portée sur l'arrêté. |
| Délai de départ volontaire | nombre | Nombre de jours accordés pour quitter le territoire, s'il est indiqué. |
| Date de notification prouvée | date | Date de remise de l'arrêté établie par une pièce (procès-verbal de notification, accusé de réception). |
| Mention des voies et délais de recours | booléen | Vrai si l'arrêté indique les voies et délais de recours, faux sinon. |
| Date d'entrée en France retenue par l'arrêté | date | Date d'entrée en France que l'arrêté indique, d'après les déclarations de l'intéressé. |
| Date d'entrée en France alléguée par la requête | date | Date d'entrée ou de début de présence en France affirmée par la requête. |

### Aide juridictionnelle et suites

| Nom | Type | Définition |
| --- | --- | --- |
| Date de dépôt de la demande d'aide juridictionnelle | date | Date de dépôt établie par le récépissé. |
| Date de la décision d'aide juridictionnelle | date | Date de la décision du bureau d'aide juridictionnelle. |
| Date de notification de la décision d'aide juridictionnelle | date | Date à laquelle cette décision a été notifiée (au demandeur ou à son avocat). |
| Date limite de production du mémoire en défense | date | Date avant laquelle l'administration doit produire son mémoire, d'après le greffe. |
| Date de clôture d'instruction | date | Date de clôture fixée par le greffe. |
| Frais irrépétibles demandés | nombre | Somme demandée au titre des frais de procédure, en euros. |
