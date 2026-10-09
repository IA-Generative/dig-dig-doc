# Colonnes personnalisées du suivi

Colonnes du tableau de suivi, avec filtres et tri ([colonnes-personnalisees.md](../backend/colonnes-personnalisees.md)). Réservé aux administrateurs. **20 champs au plus** ; nom unique, 80 caractères au plus. Les valeurs sont saisies, jamais calculées.

| Nom | Type | Définition (aide en en-tête) | Obligatoire | Valeur par défaut | Choix / devise |
| --- | --- | --- | --- | --- | --- |
| Numéro de la requête | text | Numéro d'enregistrement au greffe. | oui | — | — |
| Juridiction | choice | Tribunal saisi. | non | Tribunal administratif de Rouen | Tribunal administratif de Rouen, Tribunal administratif de Caen, Autre |
| Avocat du requérant | text | Nom de l'avocat qui a signé la requête. | non | — | — |
| Date d'enregistrement | date | Date d'enregistrement de la requête au greffe. | non | — | — |
| Fin de la suspension | date | Date de fin de la suspension du permis, d'après l'arrêté. | non | — | — |
| Vérification de l'appareil conforme | choice | L'appareil avait une vérification périodique valide à la date du contrôle. | non | À vérifier | À vérifier, Conforme, Non conforme |
| Date d'audience | date | Date de l'audience, quand elle est fixée. | non | — | — |
| Niveau de risque | choice | Appréciation du service du contentieux, après analyse. | non | À évaluer | À évaluer, Faible, Moyen, Élevé |

## Pour le dossier d'exemple

| Colonne | Valeur à saisir |
| --- | --- |
| Numéro de la requête | 2602345-1 |
| Juridiction | Tribunal administratif de Rouen |
| Avocat du requérant | Me Julien FABRE |
| Date d'enregistrement | 2026-06-30 |
| Fin de la suspension | 2026-09-09 |
| Vérification de l'appareil conforme | Non conforme |
| Niveau de risque | Élevé |
