# Notifications (backend)

Issue #174, parent #167. Une personne est prévenue quand **on lui affecte un dossier**, quand **l'échéance d'un de ses dossiers approche ou est dépassée**, quand **un tiers change le statut** d'un de ses dossiers, ou quand **une analyse qu'elle a lancée se termine ou échoue**. Les **rappels de [créneau](creneaux-de-traitement.md)** en font partie (issue #219).

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
| `reminder` | Rappels | L'heure d'un rappel de **mon** créneau est passée (voir « Rappels de créneau »). |

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

## Rappels de créneau

Un [créneau de traitement](creneaux-de-traitement.md) peut demander jusqu'à 3 rappels, en minutes avant chaque occurrence (0 = à l'heure). Ils sont fabriqués **à la lecture**, comme les autres notifications, par `NotificationRepository._reminder_notifications`.

- Le serveur **développe la récurrence** (`app/services/slot_occurrences.py`, logique pure) : jour, semaine (jours choisis), mois, année ; fin jamais, à une date (incluse) ou après N occurrences (la première compte).
- **Heure de Paris** : une occurrence garde la même heure de l'horloge d'un jour à l'autre, **heure d'été et d'hiver comprises** (9 h reste 9 h, soit 7 h puis 8 h UTC). Un quantième qui n'existe pas (31, 29 février) est ramené au dernier jour du mois, **depuis le quantième d'origine** : mars retrouve le 31.
- Pour chaque occurrence et chaque décalage : une notification **quand l'heure du rappel est passée**, **une seule** (`dedup_key` = dossier, début d'occurrence, décalage), datée de l'heure du rappel.
- **Fenêtre de 6 heures** : un rappel dont l'heure est plus ancienne n'est pas rejoué (l'application n'était pas ouverte : « rappel à 9 h » reçu à 17 h n'a pas de sens).
- **Pas de rappel pour un instant antérieur à l'enregistrement** : poser à 8 h 55 un créneau de 9 h avec un rappel 15 minutes avant ne produit pas de rappel pour 8 h 45. Remplacer un créneau repart de zéro (`updated_at`).
- Propres au **propriétaire** du créneau (jamais pour quelqu'un d'autre qui voit le dossier), et seulement sur un dossier **visible** ; un créneau supprimé ne produit plus rien.
- Message : « Rappel : créneau de traitement à 09:00. » (heure de Paris de l'occurrence).
- Garde-fou : 5 000 occurrences au plus depuis le début d'une série (comme l'agenda).

L'interface n'a plus de déclenchement local : les rappels arrivent par l'interrogation périodique (60 s), comme les autres notifications, et déclenchent l'alerte du navigateur si elle est activée.

## Conservation

Les notifications **lues** sont purgées après **90 jours** (à chaque lecture de leur destinataire). Les non lues restent. Pas de préférences par personne dans cette première version : toutes les catégories sont reçues.

## Choix et limites

- **Accès** ([#177](acces-aux-dossiers.md)) : on ne notifie que pour un dossier visible ; après un retrait d'accès, les notifications existantes restent dans la liste **sans lien ni nom** (`accessible: false`).
- **Statut** : on notifie la personne **responsable au moment de la lecture** ; si le dossier a changé de main entre l'événement et la lecture, c'est le responsable actuel qui est prévenu.
- **Rappels de créneau** : encore déclenchés par le navigateur. Les déclencher côté serveur demande de développer les récurrences (même mécanique de lecture).
- **Alertes du navigateur** : l'interface les affiche pour les notifications nouvelles reçues pendant que l'application est ouverte.
- Migration : `20261012_0900_c8d9e0f1a2b3_notifications.py` (testée en montée, descente et remontée).
