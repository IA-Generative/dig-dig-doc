# Tableau de bord personnel (backend)

Issue #174, parent #167. `GET /api/dashboard` donne à chaque personne ce qui l'attend : ses indicateurs, ses urgences, où en sont ses dossiers, les dossiers sans responsable et l'activité récente. Tout se calcule **à la demande** à partir des dossiers, du journal et des seuils d'échéance : aucune table nouvelle, aucune migration.

Le périmètre « mes dossiers » est celui des dossiers **affectés à la personne** ([affectation](affectation-des-dossiers.md)) et rangés dans une analyse. Les [créneaux planifiés](creneaux-de-traitement.md) ont leurs propres routes (chaque urgence porte le sien) ; les [notifications](notifications.md) ont les leurs.

## Contenu

| Champ | Contenu |
| --- | --- |
| `stats` | `total_dossiers`, `closed_dossiers` ; `completed_this_week` et `completed_prev_week` (clôturés par **semaine civile de Paris**, du lundi 00 h au dimanche) ; `weekly_closed` (4 dernières semaines, la plus ancienne d'abord) ; `avg_processing_days` (délai moyen création → clôture) ; `on_time_rate` (part des dossiers clos **au plus tard le jour de leur échéance**, entre 0 et 1). Chaque valeur vaut 0 s'il n'y a rien à mesurer. |
| `urgencies` | Dossiers **ouverts** avec une échéance **proche ou dépassée selon les seuils de leur analyse** ([échéance](echeance-du-dossier.md)) : dossier, analyse, statut, `due_at`, `level` (`soon` ou `overdue`), `days_left`, `color`. Par échéance croissante, 200 au plus. |
| `status_counts` | Mes dossiers ouverts par statut, avec le nom de l'analyse (les statuts sont propres à chaque analyse). Les statuts finaux n'y figurent pas. |
| `unassigned` | Dossiers ouverts **sans responsable**, les plus anciens d'abord, 50 au plus. **`null`** si la personne n'a pas le droit de les voir : pour l'instant, les administrateurs seulement. |
| `activity` | Ce qui s'est passé sur mes dossiers **ces 7 derniers jours**, par **d'autres personnes** ou le système : statut modifié, document ajouté, analyse terminée ou en échec. 20 au plus, du plus récent au plus ancien. |

- Les semaines suivent l'heure de Paris, changement d'heure compris : une clôture le dimanche à 23 h 30 appartient à la semaine qui se termine, pas à la suivante.
- Un **niveau d'échéance « loin »** n'est pas une urgence : avec des seuils serrés (7 jours seulement), un dossier à 20 jours n'apparaît pas.
- **Pas d'auto-notification** : mes propres actions ne figurent pas dans l'activité.
- Le message d'activité est écrit par le serveur (« Statut : À instruire → En instruction, par Camille Durand »). Il ne contient jamais le contenu du dossier ni le nom d'un fichier déposé.

## Choix et limites

- **Accès** (#177) : le tableau de bord ne porte que sur des dossiers affectés à la personne, mais la règle d'accès par groupe ne s'y applique pas encore ; elle s'appliquera à la liste des non affectés et aux comptes.
- **Non affectés** : réservé aux administrateurs en attendant les rôles d'instruction (#178).
- **À venir** : rappels de créneau côté serveur.
- Le calcul se fait à chaque appel ; si le volume l'exige, des agrégats précalculés viendront plus tard.
