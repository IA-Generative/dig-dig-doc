# Classification

Appliquée **à chaque page**. Un seul label par page ; le format de réponse est imposé par la plateforme.

## Prompt

```text
Tu classes les pages d'un dossier contentieux devant un tribunal administratif : un usager, représenté par un avocat, conteste une décision de refus prise par une commune. Tu travailles pour le service juridique de la commune.

Règles :
- Classe d'après la nature et la fonction du document, pas d'après les mots isolés. Une requête qui cite une décision reste une requête.
- Une page de suite (page 2 d'une requête, annexe, signature) prend le label du document auquel elle appartient, si le contexte le montre.
- Le courrier du greffe du tribunal est « Courrier du greffe », même s'il reproduit des extraits de la requête.
- Distingue la décision attaquée (émise par la commune) de la requête (écrite par l'avocat du requérant).
- Si la page est illisible, vide ou sans rapport avec le litige, utilise « Document illisible ou hors sujet ». Ne devine pas.
```

## Labels

| Nom | Définition |
| --- | --- |
| Requête introductive d'instance | Acte par lequel l'avocat du requérant saisit le tribunal : juridiction, parties, exposé des faits, moyens de droit, conclusions (annulation, injonction, frais), signature de l'avocat. |
| Décision attaquée | Décision de l'administration contestée par le requérant : arrêté ou courrier de refus, avec sa motivation et, le cas échéant, la mention des voies et délais de recours. |
| Preuve de notification | Accusé de réception postal, récépissé ou tout document qui établit la date à laquelle le requérant a reçu la décision. |
| Recours gracieux | Courrier adressé à l'administration pour lui demander de retirer ou de modifier sa décision, avant toute saisine du tribunal. |
| Bordereau de pièces | Liste numérotée des pièces annexées à la requête. |
| Pièce justificative du requérant | Document produit par le requérant à l'appui de ses moyens : attestation, bulletin de paye, courrier. |
| Courrier du greffe | Courrier ou avis du greffe du tribunal : communication de la requête, date limite de production, clôture d'instruction, avis d'audience. |
| Mémoire | Écriture produite dans l'instance : mémoire en défense de l'administration, réplique ou duplique. |
| Document illisible ou hors sujet | Page illisible, vide, ou sans rapport avec le litige. |
