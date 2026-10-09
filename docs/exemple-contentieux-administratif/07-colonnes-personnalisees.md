# Colonnes personnalisées du suivi

Colonnes du tableau de suivi, avec filtres et tri ([colonnes-personnalisees.md](../backend/colonnes-personnalisees.md)). Réservé aux administrateurs. **20 champs au plus** ; nom unique, 80 caractères au plus.

Les valeurs sont **saisies** (ou prises par défaut), jamais calculées par la plateforme.

| Nom | Type | Définition (aide en en-tête) | Obligatoire | Valeur par défaut | Choix / devise |
| --- | --- | --- | --- | --- | --- |
| Numéro de la requête | text | Numéro d'enregistrement au greffe. | oui | — | — |
| Juridiction | choice | Tribunal saisi. | non | Tribunal administratif de Rouen | Tribunal administratif de Rouen, Tribunal administratif de Caen, Autre |
| Avocat du requérant | text | Nom de l'avocat qui a signé la requête. | non | — | — |
| Date d'enregistrement | date | Date d'enregistrement de la requête au greffe. | non | — | — |
| Date d'audience | date | Date de l'audience, quand elle est fixée. | non | — | — |
| Montant en litige | amount | Total des sommes demandées par le requérant (aide et frais). | non | — | EUR |
| Recevabilité contestée | boolean | Le service juridique envisage de soulever l'irrecevabilité. | non | non | — |
| Niveau de risque | choice | Appréciation du service juridique, après analyse. | non | À évaluer | À évaluer, Faible, Moyen, Élevé |

## Pour le dossier d'exemple

| Colonne | Valeur à saisir |
| --- | --- |
| Numéro de la requête | 2603456-9 |
| Juridiction | Tribunal administratif de Rouen |
| Avocat du requérant | Me Hélène MARCHAND |
| Date d'enregistrement | 2026-09-18 |
| Montant en litige | 3 900 (2 400 + 1 500) |
| Recevabilité contestée | à décider par le service juridique |
