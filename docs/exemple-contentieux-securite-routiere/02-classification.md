# Classification

Appliquée **à chaque page**. Un seul label par page ; le format de réponse est imposé par la plateforme.

## Prompt

```text
Tu classes les pages d'un dossier contentieux de sécurité routière devant un tribunal administratif : un conducteur, représenté par son avocat, conteste l'arrêté préfectoral qui a suspendu son permis de conduire après un contrôle d'alcoolémie. Tu travailles pour le service du contentieux de la préfecture.

Règles :
- Classe d'après la nature et la fonction du document, pas d'après les mots isolés. Une requête qui cite le procès-verbal reste une requête.
- Une page de suite (page 2, annexe, signature) prend le label du document auquel elle appartient, si le contexte le montre.
- Distingue l'arrêté préfectoral attaqué (émis par la préfecture), le procès-verbal du contrôle (établi par les forces de l'ordre) et la requête (écrite par l'avocat).
- Un certificat de vérification d'un appareil de mesure n'est ni un procès-verbal ni une pièce du requérant : il a son propre label.
- Si la page est illisible, vide ou sans rapport avec le litige, utilise « Document illisible ou hors sujet ». Ne devine pas.
```

## Labels

| Nom | Définition |
| --- | --- |
| Requête introductive d'instance | Acte par lequel l'avocat du requérant saisit le tribunal : juridiction, parties, faits, moyens, conclusions, signature de l'avocat. |
| Arrêté de suspension | Arrêté du préfet suspendant le permis de conduire : motifs, durée, date d'effet, voies et délais de recours. |
| Procès-verbal de contrôle | Procès-verbal établi par les forces de l'ordre lors du contrôle : date, heure, lieu, identité du conducteur, véhicule, mesure, appareil utilisé, informations données au conducteur. |
| Attestation de vérification de l'appareil | Certificat de vérification périodique d'un appareil de mesure (éthylomètre) : numéro de l'appareil, date de vérification, durée de validité. |
| Preuve de notification | Procès-verbal de notification, avis de réception ou tout document établissant la date de remise de l'arrêté. |
| Pièce justificative du requérant | Document produit par le requérant à l'appui de ses moyens : attestation de son employeur, justificatif de besoin professionnel. |
| Courrier du greffe | Courrier ou avis du greffe : communication de la requête, date limite de production, clôture d'instruction, avis d'audience. |
| Mémoire | Écriture produite dans l'instance : mémoire en défense, réplique, duplique. |
| Document illisible ou hors sujet | Page illisible, vide, ou sans rapport avec le litige. |
