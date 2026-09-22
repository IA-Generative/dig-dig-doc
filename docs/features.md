Il faut se rapprocher de ce que fait Démarche Simplifié.

mettre le code dans async API.



Grâce à des capacités d'analyse multimodale fournies par MIrAI API, les applications métiers doivent pouvoir fiabiliser et accélérer l'instruction des dossiers usagers. Il s'agit de doter l'écosystème d'outils standardisés pour automatiser le tri documentaire, l'extraction de données et la détection d'incohérences, tout en garantissant un traitement sécurisé sur une infrastructure souveraine.

Ces fonctionnalités de base pourront également être mise à profit pour lutter contre la fraude documentaire (usurpation d'identité).



# Feature 1 Classification Documentaire (Typage)

En tant que système d'instruction ou agent, je veux identifier automatiquement la nature d'un document téléversé (CNI, passeport, justificatif de domicile, avis d'imposition, etc.) afin de vérifier la complétude du dossier usager dès le dépôt.

Comportement attendu : L'outil prend en entrée un fichier (PDF, image) et retourne une catégorie normalisée accompagnée d'un score de confiance.

Gestion des anomalies : Détection des documents illisibles, tronqués ou corrompus avec renvoi d'un code d'erreur spécifique exigeant un nouveau dépôt immédiat.

# Feature 2 : Extraction d'Entités Nommées (NER)

En tant que système d'instruction, je veux extraire les informations clés des pièces justificatives (nom, prénom, date de naissance, adresse postale, numéros d'identification) afin de structurer la donnée sans saisie manuelle de la part de l'instructeur.

Comportement attendu : Utilisation de pipelines de parsing couplés à des modèles de langage pour extraire les paires clés-valeurs sous un format JSON strictement défini.

Contrainte de performance : Le traitement du document et l'inférence doivent s'exécuter avec une latence compatible avec un traitement quasi-synchrone ou asynchrone rapide.

# Feature 3 : Contrôles de Cohérence Croisée

En tant que système d'instruction, je veux comparer les entités extraites entre différentes pièces d'un même dossier afin de lever des alertes sur de potentielles fraudes, usurpations ou erreurs de saisie.

Comportement attendu : Le service croise les données (ex: l'adresse du justificatif de domicile correspond-elle à celle de l'avis d'imposition ? Le nom sur la CNI correspond-il à celui déclaré dans le formulaire ?).

Restitution : Génération d'un rapport de validation typé (valide, incohérence_détectée, vérification_manuelle_requise) avec la mise en évidence des champs divergents pour faciliter la prise de décision de l'agent.



### Critères d'Acceptation (DoD)

* [ ] Les services sont documentés et accessible via la gateway de MIrAI API.
* [ ] Le taux de précision sur la classification des 5 types de pièces les plus courants est supérieur à un seuil défini (ex: 95%).
* [ ] Le format de sortie du module NER respecte strictement le schéma JSON attendu, sans hallucination de champs ou de données.
* [ ] L'algorithme de cohérence croisée intègre une tolérance sémantique (ex: une modification mineure de type "Av" vs "Avenue" ne déclenche pas un faux positif).
* [ ] Les données transmises à l'API ne sont ni stockées de manière persistante après le traitement, ni réutilisées pour le réentraînement des modèles.
