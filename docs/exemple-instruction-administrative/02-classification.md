# Classification

Appliquée à **chaque page**. La plateforme impose elle-même un seul label par page et un format de réponse structuré ; le prompt ci-dessous apporte le contexte métier.

## Prompt

```text
Tu classes les pages d'un dossier de demande d'aide au logement déposé par un particulier auprès d'une commune.

Règles :
- Choisis le label d'après la nature du document, pas d'après les mots isolés qu'il contient : une facture d'électricité qui mentionne « RIB » reste un justificatif de domicile.
- Une page de suite (verso, page 2 d'un contrat, annexe) prend le label du document auquel elle appartient, si le contexte le montre.
- Si la page est illisible, tronquée, vide ou n'a aucun rapport avec une demande d'aide, utilise « Document illisible ou hors sujet ». Ne devine pas.
- Un document en langue étrangère est classé d'après sa nature, comme les autres.
```

## Labels

| Nom | Définition |
| --- | --- |
| Formulaire de demande | Le formulaire de demande d'aide rempli par le demandeur : état civil, adresse, situation, revenus déclarés, montant demandé, date et signature. |
| Pièce d'identité | Carte nationale d'identité, passeport ou titre de séjour, recto ou verso. Comporte une photo, un état civil, un numéro et une date de validité. |
| Justificatif de domicile | Document de moins de 3 mois établissant l'adresse du demandeur : facture d'énergie, d'eau, de téléphone fixe ou d'internet, quittance de loyer, attestation d'hébergement. |
| Avis d'imposition | Avis d'impôt sur le revenu émis par l'administration fiscale : revenu fiscal de référence, nombre de parts, adresse fiscale. |
| RIB | Relevé d'identité bancaire : titulaire du compte, IBAN, BIC, nom de la banque. |
| Contrat de bail | Contrat de location ou avenant : identité du bailleur et du locataire, adresse du logement, montant du loyer et des charges, date d'effet. |
| Document illisible ou hors sujet | Page illisible, tronquée, vide, ou sans rapport avec la demande. À signaler pour un nouveau dépôt. |
