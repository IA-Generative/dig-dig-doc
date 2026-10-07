# Notifications (backend)

Issue #174, parent #167. Une personne est prévenue quand **on lui affecte un dossier**, quand **l'échéance d'un de ses dossiers approche ou est dépassée**, quand **un tiers change le statut** d'un de ses dossiers, ou quand **une analyse qu'elle a lancée se termine ou échoue**. Les rappels de [créneau](creneaux-de-traitement.md) viendront ensuite.

## Fabriquées à la lecture

Il n'y a **pas de tâche planifiée** : les notifications se fabriquent quand la personne les lit. Chaque lecture (`GET /api/notifications`, `GET /api/notifications/unread-count`, `POST /api/notifications/read-all`) commence par une **mise à jour** (`sync`) qui lit ce que le [journal du dossier](journal-du-dossier.md) a enregistré **depuis la dernière fois**, et l'état des échéances, puis écrit ce qui est nouveau. Une notification n'a d'utilité que lorsque l'application est ouverte (pas d'e-mail, pas de Web Push) : l'interrogation périodique de l'interface suffit donc à les faire apparaître.

- **Curseur** : `notification_cursors.last_seq` retient le dernier événement du journal lu pour la personne (`DossierEvent.seq`). Au tout premier passage, on remonte le journal de **7 jours** seulement.
- **Une seule notification par fait** : `dedup_key` est unique par personne. Deux lectures simultanées produisent la même ligne, une seule est écrite.
- **Jamais de notification de sa propre action** : les événements dont la personne est l'auteur sont ignorés.

| Type (`kind`) | Catégorie | Quand |
| --- | --- | --- |
| `assigned` | Affectations | Un autre que moi m'affecte un dossier (`assignee_changed`). |
| `status_changed` | Statuts | Un autre que moi change le statut d'un dossier **qui m'est affecté**. |
| `analysis_done`, `analysis_failed` | Analyses | Fin d'une analyse **que j'ai lancée** (l'auteur du dernier « analyse lancée » avant la fin). |
| `due_soon`, `overdue` | Échéances | Un dossier ouvert qui m'est affecté **entre** dans le niveau « proche » ou « dépassée » selon les seuils de son analyse ([échéance](echeance-du-dossier.md)) ; **une fois par niveau et par date d'échéance** (changer la date réarme). |
| `reminder` | Rappels | À venir. |

**Premier passage et échéances** : l'état existant (dossiers déjà proches ou dépassés) est enregistré **comme déjà lu** : l'agenda du tableau de bord l'affiche déjà, inutile d'en faire un déluge de notifications. Au plus 50 par passage.

## Modèle

`notifications` : `user_id` (destinataire), `kind`, `dossier_id` (`CASCADE`), `dossier_name` (le nom au moment de la notification), `message`, `dedup_key`, `read_at`, `created_at`. La notification d'un événement garde la **date de l'événement**. Elle ne contient que des noms et des valeurs d'affichage, jamais le contenu du dossier ni un nom de fichier. Schéma : [`data-model.png`](data-model.png).

## API

| Route | Rôle |
| --- | --- |
| `GET /api/notifications` | Mes notifications, de la plus récente à la plus ancienne ; `category` (`assignment`, `deadline`, `status`, `analysis`, `reminder`), `unread=true`, `limit` (≤ 200, 100 par défaut). |
| `GET /api/notifications/unread-count` | `{total, by_category}` : la pastille. |
| `POST /api/notifications/{id}/read` | Marque lue (204, même si elle l'était) ; 404 si elle n'existe pas **ou n'est pas à moi**. |
| `POST /api/notifications/read-all` | Marque toutes les miennes comme lues (ou celles d'une `category`) ; renvoie `{marked}`. |

Chaque requête est **bornée au destinataire** : aucune lecture ni modification ne touche la notification d'un autre.

## Conservation

Les notifications **lues** sont purgées après **90 jours** (à chaque lecture de leur destinataire). Les non lues restent. Pas de préférences par personne dans cette première version : toutes les catégories sont reçues.

## Choix et limites

- **Accès** (#177) : un retrait d'accès devra masquer le lien et le nom du dossier dans les notifications existantes ; ce n'est pas encore fait côté serveur.
- **Statut** : on notifie la personne **responsable au moment de la lecture** ; si le dossier a changé de main entre l'événement et la lecture, c'est le responsable actuel qui est prévenu.
- **Rappels de créneau** : encore déclenchés par le navigateur. Les déclencher côté serveur demande de développer les récurrences (même mécanique de lecture).
- **Alertes du navigateur** : l'interface les affiche pour les notifications nouvelles reçues pendant que l'application est ouverte.
- Migration : `20261012_0900_c8d9e0f1a2b3_notifications.py` (testée en montée, descente et remontée).
