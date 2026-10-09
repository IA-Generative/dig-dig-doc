# Classification

Appliquée **à chaque page**. Un seul label par page ; le format de réponse est imposé par la plateforme.

## Prompt

```text
Tu classes les pages d'un dossier contentieux des étrangers devant un tribunal administratif : une personne étrangère, représentée par son avocate, conteste un refus de titre de séjour assorti d'une obligation de quitter le territoire français. Tu travailles pour le service du contentieux de la préfecture.

Règles :
- Classe d'après la nature et la fonction du document, pas d'après les mots isolés. Une requête qui cite l'arrêté reste une requête.
- Une page de suite (page 2, annexe, signature) prend le label du document auquel elle appartient, si le contexte le montre.
- Distingue l'arrêté préfectoral attaqué (émis par la préfecture) de la requête (écrite par l'avocate).
- Une décision du bureau d'aide juridictionnelle n'est ni une décision attaquée ni un courrier du greffe du tribunal : elle a son propre label.
- Si la page est illisible, vide ou sans rapport avec le litige, utilise « Document illisible ou hors sujet ». Ne devine pas.
```

## Labels

| Nom | Définition |
| --- | --- |
| Requête introductive d'instance | Acte par lequel l'avocat du requérant saisit le tribunal : juridiction, parties, faits, moyens, conclusions, signature de l'avocat. |
| Arrêté attaqué | Décision de la préfecture contestée : refus de titre de séjour et obligation de quitter le territoire, avec motivation et mention des voies et délais de recours. |
| Preuve de notification | Procès-verbal de notification, avis de réception ou tout document établissant la date à laquelle l'intéressé a reçu l'arrêté. |
| Demande d'aide juridictionnelle | Récépissé ou accusé de dépôt d'une demande d'aide juridictionnelle auprès du bureau compétent. |
| Décision d'aide juridictionnelle | Décision du bureau d'aide juridictionnelle (admission, rejet) et sa notification. |
| Bordereau de pièces | Liste numérotée des pièces annexées à la requête. |
| Pièce justificative du requérant | Document produit par le requérant à l'appui de ses moyens : justificatif de présence, contrat de travail, attestation. |
| Courrier du greffe | Courrier ou avis du greffe du tribunal : communication de la requête, date limite de production, clôture d'instruction, avis d'audience. |
| Mémoire | Écriture produite dans l'instance : mémoire en défense, réplique, duplique. |
| Document illisible ou hors sujet | Page illisible, vide, ou sans rapport avec le litige. |
