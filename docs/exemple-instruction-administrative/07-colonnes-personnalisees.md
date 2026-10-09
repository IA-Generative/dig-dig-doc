# Colonnes personnalisées du suivi

Colonnes ajoutées au tableau de suivi, avec filtres et tri ([colonnes-personnalisees.md](../backend/colonnes-personnalisees.md)). Réservé aux administrateurs. **20 champs au plus** par analyse ; le nom est unique, 80 caractères au plus.

Les valeurs sont **saisies** (ou prises par défaut) : la plateforme ne les calcule pas.

| Nom | Type | Définition (aide en en-tête) | Obligatoire | Valeur par défaut | Choix / devise |
| --- | --- | --- | --- | --- | --- |
| Référence de la demande | text | Numéro attribué par le guichet à la réception du dossier. | oui | — | — |
| Service instructeur | choice | Service chargé de l'instruction. | non | Action sociale | Action sociale, Logement, Finances |
| Date de dépôt | date | Date de dépôt indiquée sur le formulaire de demande. | oui | — | — |
| Montant demandé | amount | Montant de l'aide demandé par le demandeur (formulaire). | non | — | EUR |
| Montant accordé | amount | Montant finalement accordé, à renseigner à la décision. | non | — | EUR |
| Dossier complet | boolean | Toutes les pièces obligatoires ont été reçues et sont recevables. | non | non | — |
| Niveau de vigilance | choice | Reprend le niveau de l'agent « Signaux d'anomalie », confirmé ou corrigé par l'instructeur. | non | Faible | Faible, Moyen, Élevé |

## Pour le dossier d'exemple

| Colonne | Valeur à saisir |
| --- | --- |
| Référence de la demande | AL-2026-0001 |
| Service instructeur | Logement |
| Date de dépôt | 2026-10-02 |
| Montant demandé | 2 400 |
| Dossier complet | non (bail manquant) |
| Niveau de vigilance | Élevé |
