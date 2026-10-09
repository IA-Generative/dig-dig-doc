# Statuts de dossier

Le circuit d'un dossier, dans l'ordre. Règles de la plateforme : **exactement un statut initial**, au moins un statut final, un statut n'est pas à la fois initial et final, noms uniques ([statuts-de-dossier.md](../backend/statuts-de-dossier.md)).

| Position | Nom | Couleur | Initial | Final | Quand l'utiliser |
| --- | --- | --- | --- | --- | --- |
| 1 | À instruire | `#6a6af4` | oui | non | Dossier déposé, pas encore ouvert. |
| 2 | Pièces manquantes | `#b34000` | non | non | Des pièces ont été redemandées au demandeur. |
| 3 | En instruction | `#0063cb` | non | non | Le dossier est complet et en cours d'examen. |
| 4 | Vérification approfondie | `#ce0500` | non | non | Un signal d'anomalie justifie un contrôle (revenus, titulaire du compte…). |
| 5 | Accordé | `#18753c` | non | oui | Aide accordée : le dossier est clos. |
| 6 | Refusé | `#8a0000` | non | oui | Aide refusée : le dossier est clos. |

Les deux statuts finaux alimentent les indicateurs du tableau de bord (dossiers clôturés, délai moyen).

## Si tu supprimes un statut utilisé

Un statut porté par des dossiers ne se supprime pas sans remplaçant : la plateforme répond « statut utilisé » et demande vers quel statut les déplacer.
