# Extraction

Appliquée **par document**, par groupes de 8 définitions (voir [extraction-par-document.md](../backend/extraction-par-document.md)). Les 18 entités ci-dessous forment donc 3 groupes (8, 8 et 2), dans l'ordre de la liste : je les ai rangées par thème, donc par pièce, pour que chaque groupe lise surtout les mêmes documents.

Le format de réponse (entité, valeur, pages) est imposé par la plateforme.

## Prompt

```text
Tu extrais des informations de pièces d'un dossier de demande d'aide au logement.

Règles :
- Recopie la valeur telle qu'elle figure dans le document, sans la corriger ni la reformuler. Exception : normalise les dates au format AAAA-MM-JJ et les montants en nombre (sans symbole ni espace : « 18 400 € » devient 18400).
- N'invente rien. Si une information n'est pas dans le texte, n'inclus pas l'entité.
- Si une même information apparaît plusieurs fois avec des valeurs différentes dans le même document, renvoie chaque valeur.
- Ne déduis pas une information d'une autre : la ville ne se déduit pas du code postal, le prénom ne se déduit pas de l'adresse e-mail.
- Distingue l'adresse du demandeur de celle du bailleur, de l'employeur ou de l'organisme émetteur.
```

## Entités

Le **type** est celui de la liste déroulante de l'interface (`texte`, `date`, `nombre`, `booléen`, `identifiant`).

### Identité (formulaire et pièce d'identité)

| Nom | Type | Définition |
| --- | --- | --- |
| Nom de famille | texte | Nom de famille du demandeur, en majuscules comme sur le document. |
| Prénom | texte | Premier prénom du demandeur. |
| Date de naissance | date | Date de naissance du demandeur. |
| Numéro de la pièce d'identité | identifiant | Numéro de la carte d'identité, du passeport ou du titre de séjour. |
| Date de fin de validité de la pièce d'identité | date | Date jusqu'à laquelle la pièce d'identité est valable. |

### Adresse et domicile

| Nom | Type | Définition |
| --- | --- | --- |
| Adresse déclarée | texte | Adresse de résidence du demandeur indiquée dans le formulaire (numéro, voie, code postal, ville). |
| Adresse du justificatif de domicile | texte | Adresse du demandeur figurant sur le justificatif de domicile (pas l'adresse de l'émetteur). |
| Date d'émission du justificatif de domicile | date | Date d'émission de la facture ou de la quittance. |
| Adresse fiscale | texte | Adresse du demandeur indiquée sur l'avis d'imposition. |

### Ressources

| Nom | Type | Définition |
| --- | --- | --- |
| Revenu fiscal de référence déclaré | nombre | Revenu fiscal de référence indiqué par le demandeur dans le formulaire, en euros. |
| Revenu fiscal de référence de l'avis | nombre | Revenu fiscal de référence figurant sur l'avis d'imposition, en euros. |
| Nombre de parts fiscales | nombre | Nombre de parts du foyer fiscal sur l'avis d'imposition. |
| Année des revenus | nombre | Année des revenus à laquelle se rapporte l'avis d'imposition. |

### Logement et aide demandée

| Nom | Type | Définition |
| --- | --- | --- |
| Loyer mensuel hors charges | nombre | Montant du loyer mensuel hors charges, en euros (bail, ou formulaire si le bail est absent). |
| Montant de l'aide demandée | nombre | Montant total de l'aide demandé par le demandeur dans le formulaire, en euros. |

### Paiement et recevabilité

| Nom | Type | Définition |
| --- | --- | --- |
| Titulaire du compte | texte | Nom du ou des titulaires du compte bancaire sur le RIB. |
| IBAN | identifiant | IBAN du compte sur le RIB, sans espaces. |
| Formulaire signé | booléen | Vrai si le formulaire porte une signature ou une mention de signature du demandeur, faux s'il est visiblement non signé. |
