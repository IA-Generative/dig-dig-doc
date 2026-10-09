# Extraction

Appliquée **par document**, par groupes de 8 définitions (voir [extraction-par-document.md](../backend/extraction-par-document.md)). Les 20 entités ci-dessous forment 3 groupes (8, 8 et 4), dans l'ordre de la liste.

Le format de réponse (entité, valeur, pages) est imposé par la plateforme.

## Prompt

```text
Tu extrais des informations de pièces d'un dossier contentieux devant un tribunal administratif.

Règles :
- Recopie la valeur telle qu'elle figure dans le document, sans la corriger ni l'interpréter. Exception : normalise les dates au format AAAA-MM-JJ et les montants en nombre (sans symbole ni espace : « 2 400 € » devient 2400).
- N'invente rien. Si une information n'est pas dans le texte, n'inclus pas l'entité.
- Une date « alléguée » par la requête (ce que l'avocat affirme) et une date « prouvée » par une pièce (accusé de réception, tampon) sont deux entités distinctes : n'attribue pas à l'une la valeur de l'autre.
- Si une même information apparaît plusieurs fois avec des valeurs différentes dans le même document, renvoie chaque valeur.
- Distingue le requérant (l'usager), son avocat, l'administration défenderesse et la juridiction.
```

## Entités

### Juridiction et parties

| Nom | Type | Définition |
| --- | --- | --- |
| Juridiction | texte | Tribunal saisi (par exemple « Tribunal administratif de Rouen »). |
| Numéro de la requête | identifiant | Numéro d'enregistrement de la requête au greffe. |
| Date d'enregistrement de la requête | date | Date à laquelle le greffe a enregistré la requête (cachet ou mention du greffe). |
| Nom du requérant | texte | Nom et prénom de l'usager qui saisit le tribunal. |
| Nom de l'avocat du requérant | texte | Nom de l'avocat qui signe la requête. |
| Barreau de l'avocat | texte | Barreau auquel l'avocat est inscrit. |
| Administration défenderesse | texte | Autorité dont la décision est contestée. |
| Objet de la décision attaquée | texte | Ce que décide l'acte attaqué, en quelques mots (par exemple « refus d'aide exceptionnelle au logement »). |

### Dates de la décision et du recours préalable

| Nom | Type | Définition |
| --- | --- | --- |
| Date de la décision attaquée | date | Date portée sur la décision contestée. |
| Date de notification prouvée | date | Date de réception de la décision établie par une pièce (date de signature de l'accusé de réception, tampon). |
| Mention des voies et délais de recours | booléen | Vrai si la décision attaquée indique les voies et délais de recours, faux si elle n'en dit rien. |
| Date d'envoi du recours gracieux | date | Date à laquelle le recours gracieux a été envoyé à l'administration. |
| Date de réception du recours gracieux | date | Date de réception du recours gracieux par l'administration, établie par un tampon ou un accusé de réception. |
| Date de rejet implicite alléguée | date | Date à laquelle la requête affirme qu'une décision implicite de rejet est née du silence de l'administration. |
| Date limite de production du mémoire en défense | date | Date avant laquelle l'administration doit produire son mémoire, d'après le greffe. |
| Date de clôture d'instruction | date | Date de clôture de l'instruction fixée par le greffe. |

### Demandes et moyens

| Nom | Type | Définition |
| --- | --- | --- |
| Montant de l'aide demandée | nombre | Montant réclamé par le requérant au titre de l'aide, en euros. |
| Frais irrépétibles demandés | nombre | Somme demandée au titre des frais de procédure, en euros. |
| Conclusions du requérant | texte | Ce que le requérant demande au tribunal (annulation, injonction, paiement, frais), en une phrase par demande. |
| Moyens invoqués | texte | Moyens de droit et de fait soulevés par la requête, séparés par un point-virgule. |

### Pièces

Aucune entité de plus : les pièces annexées sont contrôlées par l'agent « Pièces et chronologie » à partir des labels et du bordereau.
