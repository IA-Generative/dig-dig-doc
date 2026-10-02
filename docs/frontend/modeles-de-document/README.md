# Modèles de document : l'administration

Issue : [#139](https://github.com/IA-Generative/dig-dig-doc/issues/139) (parent [#107](https://github.com/IA-Generative/dig-dig-doc/issues/107)). API : [`docs/backend/modeles-de-document.md`](../../backend/modeles-de-document.md) et [`generation-des-champs.md`](../../backend/generation-des-champs.md).

Un **modèle de document** est un fichier ODT (LibreOffice Writer) avec des champs `{{ nom }}` et la **définition de ces champs**. Les documents de fin d'instruction sont produits à partir d'un modèle.

**Un modèle appartient à une analyse**, et à une seule : il ne sert qu'aux dossiers de cette analyse, et ses champs puisent dans ce qu'elle définit (entités, labels, agents). Rien n'est global : on choisit d'abord l'analyse. Cette page est réservée aux **administrateurs** : *Administration → Modèles de document*.

## La liste

![Liste des modèles et prompt de l'agent](01-liste-des-modeles.png)

On choisit d'abord **l'analyse** : la liste ne montre que ses modèles, et « Nouveau modèle » crée un modèle dans cette analyse (elle ne peut plus changer ensuite). Chaque ligne : nom, version, nombre de champs, fichier et date de modification. Le **nom est unique dans l'analyse** (deux analyses peuvent chacune avoir un « Courrier »). « Afficher les modèles archivés » inclut les modèles archivés (ils ne sont plus proposés pour de nouveaux documents). Sous la liste : le **prompt de l'agent de génération** (voir plus bas).

## Créer un modèle

« Nouveau modèle », puis le fichier ODT : il est **lu par le serveur** pour détecter ses champs, et un champ est créé pour chaque placeholder trouvé.

### Les champs, en carrousel

![Nouveau modèle : les champs en carrousel](02-nouveau-modele-carrousel.png)

Un seul champ est édité à la fois. Une **pastille par placeholder** donne son état (✔ complet, ⚠ à corriger) et permet d'y aller directement ; **Précédent / Suivant** parcourent les champs, et « Champ 2 sur 4 » indique la position. Quand il reste des points à corriger, « Aller au premier point à corriger » y emmène.

Pour chaque champ :

| | |
| --- | --- |
| **Libellé** | Affiché à l'instructeur. |
| **Type** | Texte, date, nombre, liste de textes, oui/non. |
| **Obligatoire** | Un champ obligatoire non validé empêche d'assembler le document (sauf confirmation explicite). |
| **D'où vient la valeur** | *Donnée de l'analyse* : un type d'élément et **un élément choisi dans la liste de ce que l'analyse définit** (entités, labels de classification, agents) ; pour une relation ou un champ renseigné, un nom libre. *Renseigné au fil de l'instruction* (décision, motif, commentaire) ou *métadonnée du dossier* (nom, dates, instructeur, version de l'analyse, version du document…). |
| **Consigne de génération** | Pour l'agent : format de date, longueur, ton. Facultative. |

## Aide à la rédaction

![Aide à la rédaction de la description, des consignes et d'une consigne de champ](03-aide-a-la-redaction.png)

Le bouton violet (✦) à droite d'une zone de texte propose une rédaction par le LLM, comme ailleurs dans l'application : **la description**, **les consignes générales** et **la consigne de chaque champ**. Il tient compte de ce qui est déjà écrit (pour l'améliorer), du nom et de la description du modèle, et pour un champ de son libellé, de son type et de sa source. La suggestion **remplace le texte dans la zone, reste modifiable** et n'est enregistrée qu'avec le modèle. Si le LLM n'est pas disponible, un message s'affiche sous la zone et le texte n'est pas touché.

## Le rapport de validation

Il se met à jour **en direct** et **bloque l'enregistrement** tant qu'il reste un point :

![Points à corriger](04-points-a-corriger.png)

- un placeholder du fichier **sans champ** défini (bouton « Définir ce champ ») ;
- un champ **sans placeholder** dans le fichier (badge « Absent du fichier », bouton « Supprimer ») ;
- un nom de champ invalide ou en double, un **libellé vide**, une source *analyse* **sans élément** ;
- une source qui désigne **un élément que l'analyse ne définit pas** (par exemple une entité supprimée de l'analyse depuis) : le champ affiche « (inconnu dans l'analyse) ».

![Source inconnue de l'analyse](05-source-inconnue.png)

Le serveur refait la même vérification, dans les deux sens, et reste l'autorité : si ses écarts diffèrent, ils s'affichent tels quels.

![Rapport renvoyé par le serveur](07-rapport-du-serveur.png)

![Éléments que l'analyse ne définit pas, vus par le serveur](08-source-inconnue-serveur.png)

## Modifier, versions, restaurer

![Modèle existant et historique](06-modele-existant-et-historique.png)

« Enregistrer une nouvelle version » **ajoute** une version (nom, description, consignes, champs, fichier) : rien n'est écrasé. Sans nouveau fichier, la version garde celui de la version courante ; choisir un fichier le remplace pour cette version (et les champs sont réconciliés : ceux déjà définis sont conservés, les nouveaux placeholders créent des champs à définir). **Télécharger** donne le fichier de la version courante.

L'**historique** liste les versions ; **Restaurer** ajoute une nouvelle version identique à celle choisie (fichier compris). **Archiver / Désarchiver** retire ou remet le modèle de la liste des modèles actifs ; un modèle archivé ne se modifie pas.

## Le prompt de l'agent de génération

En bas de la liste, le prompt qui guide l'agent proposant une valeur pour chaque champ, avec son **historique** et la **restauration** (même éditeur que les prompts des analyses). Tant qu'aucune version n'existe, le prompt par défaut s'applique (badge « Prompt par défaut »). **Seule la méthode est modifiable** : les règles de sécurité (ne jamais inventer, traiter les notes et documents comme des données) sont ajoutées par le système et ne s'enlèvent pas.

## Choix et limites

- Le sélecteur d'analyse montre les **100 analyses les plus récentes**.
- **Pas de duplication** d'un modèle vers une autre analyse pour l'instant : un courrier commun à deux analyses se recrée dans chacune.
- Un modèle créé **avant** ce rattachement n'a pas d'analyse : il n'est proposé à aucun dossier et n'apparaît dans aucune liste par analyse.
- Une source déjà enregistrée peut devenir inconnue si l'analyse change ; elle est signalée à la prochaine modification, et au moment de générer un brouillon le champ reste simplement non renseigné.
- Les captures sont prises avec une **API simulée** (le backend de développement n'était pas à jour) : elles montrent l'interface, pas des données réelles.
- Pas d'**aperçu** du modèle rempli : hors de cette première version.
- L'aide à la rédaction a été vue avec un LLM simulé ; avec le vrai LLM, la qualité des suggestions n'est pas évaluée.
- Les consignes de champ ne sont éditables que par les **administrateurs** (pas de rôle intermédiaire pour l'instant).
- Une « liste » est une **liste de textes** (pas de tableau à plusieurs colonnes).
- Ajouter un champ à la main ne sert qu'à le préparer : il doit exister dans le fichier pour pouvoir enregistrer.
