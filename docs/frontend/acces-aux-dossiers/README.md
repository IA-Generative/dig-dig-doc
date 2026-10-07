# Accès aux dossiers par groupe

Issue : [#177](https://github.com/IA-Generative/dig-dig-doc/issues/177) (parent [#167](https://github.com/IA-Generative/dig-dig-doc/issues/167)). Questions associées : [#178](https://github.com/IA-Generative/dig-dig-doc/issues/178) (rôles et permissions), [#179](https://github.com/IA-Generative/dig-dig-doc/issues/179) (prise en compte des changements de groupes), [#180](https://github.com/IA-Generative/dig-dig-doc/issues/180) (dossiers existants), [#181](https://github.com/IA-Generative/dig-dig-doc/issues/181) (dossier sans groupe actif), [#182](https://github.com/IA-Generative/dig-dig-doc/issues/182) (traces d'accès administrateur).

Avoir accès à une **analyse** ne doit pas donner accès à **tous ses dossiers** : un dossier peut être **restreint** à certains **groupes Keycloak**. Cette page décrit l'interface ; elle suit le tableau de bord et le [tableau de suivi](../tableau-de-suivi/README.md).

> **Partie interface seulement.** Les accès sont simulés dans le navigateur en attendant le backend, qui devra appliquer **un seul filtre de visibilité** à toutes les routes : voir « Choix et limites ». Aujourd'hui, côté serveur, tout dossier reste visible de tout utilisateur connecté.

## Les règles

| Règle | Effet |
| --- | --- |
| **Restreint par défaut** | Un nouveau dossier n'est vu que des membres des groupes choisis et des administrateurs. |
| **Selon l'analyse** | Comportement actuel, conservé pour les dossiers existants : tout utilisateur ayant accès à l'analyse le voit. |
| **Mes groupes seulement** | On n'associe à un dossier que **ses propres groupes**, y compris un administrateur. |
| **Pas d'héritage** | Un groupe n'ouvre pas l'accès à ses sous-groupes ni à son groupe parent (le chemin exact est comparé). |
| **Les administrateurs** | Ils voient tout et sont **seuls à modifier** l'accès d'un dossier existant ; leur accès hors de leurs groupes sera tracé. |
| **Le créateur** | Il n'a **aucun droit propre** : son accès passe par ses groupes. Un dossier restreint a donc **au moins un groupe**. |
| **Affectation** | On n'affecte qu'une personne qui a accès au dossier ; si elle le perd, l'affectation est annulée. |

## Repérer un dossier restreint

![Pastille « Restreint » dans la liste des dossiers](01-pastille-restreint.png)

La pastille **« Restreint »** (icône cadenas **et** libellé) figure à côté du nom du dossier dans la liste des dossiers, dans l'en-tête du dossier et dans le tableau de suivi. Rien n'est affiché pour un dossier « Selon l'analyse ».

## À la création

![Création d'un dossier restreint](02-creation-d-un-dossier-restreint.png)

Dans « Créer un dossier », l'interrupteur **« Dossier restreint »** est activé par défaut. On coche parmi **ses** groupes ceux qui auront accès ; **au moins un** est obligatoire (le bouton « Créer » reste inactif et un message l'explique). Si l'on n'a qu'un seul groupe, il est présélectionné ; sans aucun groupe, l'interface invite à en demander un à un administrateur.

## La fenêtre « Accès au dossier »

![Accès au dossier](03-acces-au-dossier.png)

Le **cadenas** de l'en-tête d'un dossier l'ouvre. Elle donne la **visibilité** (« Restreint » ou « Selon l'analyse », chacune avec son explication) et les **groupes ayant accès**. Un groupe associé dont on n'est pas membre reste affiché (« vous n'en êtes pas membre ») et peut être retiré par un administrateur. Les **changements d'accès récents** sont listés en bas.

### Perdre l'accès : la confirmation

![Confirmation des pertes d'accès](04-confirmation-des-pertes-d-acces.png)

Quand un changement fait perdre l'accès à des personnes, un encadré **les nomme**, rappelle que leurs **affectations seront annulées et tracées** et que l'**historique du dossier et ses documents générés restent en place**. Il faut cocher « J'ai compris » pour enregistrer. Un dossier restreint sans groupe ne s'enregistre pas.

### Pour un non-administrateur

![Accès en lecture seule](08-lecture-seule-pour-un-non-administrateur.png)

Les personnes qui ont accès au dossier voient ses règles, mais **ne peuvent rien modifier** : « Seuls les administrateurs modifient l'accès à un dossier ».

## Dans le tableau de suivi

![Filtre « Accès » du suivi](05-suivi-dossiers-restreints.png)

- Le filtre **Accès** (restreints, selon l'analyse) et la pastille permettent de repérer les dossiers restreints.
- Un dossier **inaccessible** n'apparaît ni dans le tableau, ni dans les compteurs, ni dans l'export ; seul un administrateur le voit.
- La liste d'affectation d'un dossier ne propose que des personnes **qui y ont accès**.

![Définir l'accès en lot](06-definir-l-acces-en-lot.png)

Pour les administrateurs, « **Définir l'accès** » dans la barre de sélection applique une visibilité et des groupes à plusieurs dossiers ; les affectations des personnes qui perdent l'accès sont annulées et l'opération est notée comme tracée.

## Notifications d'un dossier devenu inaccessible

![Notification d'un dossier non accessible](07-notification-d-un-dossier-non-accessible.png)

Quand l'accès est retiré, les notifications passées de la personne restent dans sa liste, mais **sans lien ni nom de dossier** (« Dossier non accessible »), pour ne rien révéler.

## Choix et limites

- **Simulation** : les accès sont gardés en mémoire (ils disparaissent au rechargement). Les groupes sont ceux du profil de connexion (`groups`) ; à défaut, deux groupes de démonstration (« Service culture » et « Service sport »). Quelques dossiers simulés sont restreints, dont un réservé à un groupe dont l'utilisateur ne fait pas partie (visible seulement d'un administrateur).
- **Le vrai contrôle est côté serveur** : l'interface masque et explique, mais seul **un filtre de visibilité unique** appliqué à toutes les routes (liste, détail, documents, chat, génération, recherche, suivi, tableau de bord, notifications) protège les données. Un dossier inaccessible devra répondre **404**, pas 403.
- **Rôles** : la première version n'a qu'un niveau d'accès (voir le dossier ou non). Lecture seule, instruction, administration… seront définis dans Keycloak ([#178](https://github.com/IA-Generative/dig-dig-doc/issues/178)).
- **Dossiers existants** : ils restent « Selon l'analyse » à la mise en production pour ne retirer l'accès à personne ; la bascule vers « Restreint » fait l'objet de [#180](https://github.com/IA-Generative/dig-dig-doc/issues/180).
- **Délai** : les groupes sont lus à la connexion, un retrait de groupe dans Keycloak n'est donc pas immédiat ([#179](https://github.com/IA-Generative/dig-dig-doc/issues/179)).
- Les captures sont prises par `frontend/scripts/doc-screenshots.mjs` avec l'API interceptée.
