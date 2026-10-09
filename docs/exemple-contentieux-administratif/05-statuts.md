# Statuts de dossier

Le circuit d'un dossier contentieux. Règles de la plateforme : **exactement un statut initial**, au moins un statut final, un statut n'est pas à la fois initial et final, noms uniques ([statuts-de-dossier.md](../backend/statuts-de-dossier.md)).

| Position | Nom | Couleur | Initial | Final | Quand l'utiliser |
| --- | --- | --- | --- | --- | --- |
| 1 | Requête reçue | `#6a6af4` | oui | non | La requête vient d'être communiquée par le greffe. |
| 2 | Recevabilité à examiner | `#b34000` | non | non | Le service juridique examine les délais et la forme. |
| 3 | Mémoire en préparation | `#0063cb` | non | non | Le mémoire en défense est en cours de rédaction. |
| 4 | Mémoire déposé | `#7b5ea7` | non | non | Le mémoire a été produit ; dans l'attente de la réplique ou de l'audience. |
| 5 | Audience fixée | `#ce0500` | non | non | Une date d'audience est connue. |
| 6 | Jugement rendu | `#18753c` | non | oui | Le tribunal a statué : le dossier est clos. |
| 7 | Désistement ou non-lieu | `#666666` | non | oui | Le requérant se désiste ou le litige disparaît : le dossier est clos. |

Les deux statuts finaux alimentent les indicateurs du tableau de bord.
