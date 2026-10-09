# Colonnes personnalisées du suivi

Colonnes du tableau de suivi, avec filtres et tri ([colonnes-personnalisees.md](../backend/colonnes-personnalisees.md)). Réservé aux administrateurs. **20 champs au plus** ; nom unique, 80 caractères au plus. Les valeurs sont saisies, jamais calculées.

Ne place **pas** de donnée sensible inutile dans ces colonnes (situation familiale, origine) : elles sont visibles dans le tableau de suivi et filtrables.

| Nom | Type | Définition (aide en en-tête) | Obligatoire | Valeur par défaut | Choix / devise |
| --- | --- | --- | --- | --- | --- |
| Numéro de la requête | text | Numéro d'enregistrement au greffe. | oui | — | — |
| Juridiction | choice | Tribunal saisi. | non | Tribunal administratif de Rouen | Tribunal administratif de Rouen, Tribunal administratif de Caen, Autre |
| Avocat du requérant | text | Nom de l'avocat qui a signé la requête. | non | — | — |
| Date d'enregistrement | date | Date d'enregistrement de la requête au greffe. | non | — | — |
| Aide juridictionnelle | boolean | Le requérant a demandé ou obtenu l'aide juridictionnelle (elle interrompt le délai). | non | non | — |
| Date d'audience | date | Date de l'audience, quand elle est fixée. | non | — | — |
| Identité à vérifier | boolean | Une divergence d'identité entre pièces demande une vérification. | non | non | — |
| Niveau de risque | choice | Appréciation du service du contentieux, après analyse. | non | À évaluer | À évaluer, Faible, Moyen, Élevé |

## Pour le dossier d'exemple

| Colonne | Valeur à saisir |
| --- | --- |
| Numéro de la requête | 2601789-4 |
| Juridiction | Tribunal administratif de Rouen |
| Avocat du requérant | Me Sophie LAMBERT |
| Date d'enregistrement | 2026-04-09 |
| Aide juridictionnelle | oui |
| Identité à vérifier | oui (numéro d'étranger) |
