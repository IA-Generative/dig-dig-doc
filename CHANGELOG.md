# Changelog

## [0.3.0](https://github.com/IA-Generative/dig-dig-doc/compare/v0.2.0...v0.3.0) (2026-09-23)


### Features

* **backend,frontend:** choix du modèle LLM ([fe9a6a1](https://github.com/IA-Generative/dig-dig-doc/commit/fe9a6a1c42ea1eb1ca99d48823e569a9dadbeb38))
* **backend,frontend:** choix du modèle LLM pour conversations et agents ([8b0ebe7](https://github.com/IA-Generative/dig-dig-doc/commit/8b0ebe78aefbdeda4a54ce0c48b85d180b97bc60))
* **backend,frontend:** pagination des listes + système de jetons d'application ([364c499](https://github.com/IA-Generative/dig-dig-doc/commit/364c4992e28b9bef48da30923c6a045260bd5574))
* **backend,worker,frontend:** chat task with streaming + sources, markdown rendering, analyse description ([a1b11d9](https://github.com/IA-Generative/dig-dig-doc/commit/a1b11d90b50289e54977e72aee42f5cd9428b217))
* **backend:** authentification Keycloak du BFF, comme Muffin ([bc48367](https://github.com/IA-Generative/dig-dig-doc/commit/bc483678aa54967bc415fdc72a47cbd2237a52b9))
* **backend:** health check étendu à postgres et s3, sortie pydantic typée ([603bde0](https://github.com/IA-Generative/dig-dig-doc/commit/603bde0337c054cf1c2d48ef170d28516dacbe40))
* **backend:** logs d'exécution, prédictions par page, partage d'analyse, SSE, CI GitLab ([f338578](https://github.com/IA-Generative/dig-dig-doc/commit/f3385782f18871607496844b786002a3311b12c5))
* **backend:** modèle de données et endpoints analyses/dossiers ([b656d48](https://github.com/IA-Generative/dig-dig-doc/commit/b656d48520e359ecfefe5c29e27adc035a7da72e))
* **backend:** prédictions et sources de message comme ensembles de pages/bbox ([f05b445](https://github.com/IA-Generative/dig-dig-doc/commit/f05b445ff564810afd716be50f60f880806b30fc))
* connecte le frontend au backend, ajoute conversations et métadonnées de document ([687c0b1](https://github.com/IA-Generative/dig-dig-doc/commit/687c0b157e0fec64dd71fcdc3be754ee166ae198))
* extraction de texte du worker, écran d'accueil DSFR, conversations en sidebar ([5a39556](https://github.com/IA-Generative/dig-dig-doc/commit/5a3955618c5a1ce39f361869224518fe6e1398d5))
* **helm:** add Helm chart with redis/postgres deps and migration job ([f2b0044](https://github.com/IA-Generative/dig-dig-doc/commit/f2b00446b6d3895ba7b199d3b06d1fda5f77362d))
* page d'accueil ([fcedcc2](https://github.com/IA-Generative/dig-dig-doc/commit/fcedcc277a8ee3f7330e9af88873ca6b63373402))
* **report:** add reporting ([a5e8241](https://github.com/IA-Generative/dig-dig-doc/commit/a5e82412d96b52413379335f65087e431e07727c))
* **worker,backend:** classification & entity extraction tasks ([3f3e7f6](https://github.com/IA-Generative/dig-dig-doc/commit/3f3e7f684eb3eb05b820e13affa688f7714ff409))
* **worker,backend:** extraction de texte (issue [#4](https://github.com/IA-Generative/dig-dig-doc/issues/4)) + captures de page relayées par le backend ([6d7d564](https://github.com/IA-Generative/dig-dig-doc/commit/6d7d564b4a69db8f884b8edc81f801d9d6618237))
* **worker:** client HTTP authentifié par jeton vers le BFF ([7a792ff](https://github.com/IA-Generative/dig-dig-doc/commit/7a792ff38f30d88bc3b4e09b99a1537840b4d938))
* **worker:** extrait aussi les bbox des blocs de mise en page ([64f753b](https://github.com/IA-Generative/dig-dig-doc/commit/64f753b2a5e28b4433e5bbadb9b13c0190da40c4))


### Bug Fixes

* **backend:** bounding_boxes devient sa propre table, rattachée à une page ([f561bca](https://github.com/IA-Generative/dig-dig-doc/commit/f561bcae098f27c4c0e70e7cb4be71b376e5cda4))
* remove duplicate migration file with same revision ID ([e04c5eb](https://github.com/IA-Generative/dig-dig-doc/commit/e04c5ebb4e853aa8130ab4f00b77ffc440858c55))
* unittest ([2c6a549](https://github.com/IA-Generative/dig-dig-doc/commit/2c6a54955a4f272f55168311b52427aec31e99fd))

## [0.3.0-rc.3](https://github.com/IA-Generative/dig-dig-doc/compare/v0.3.0-rc.2...v0.3.0-rc.3) (2026-09-23)


### Features

* **helm:** add Helm chart with redis/postgres deps and migration job ([5e3ca80](https://github.com/IA-Generative/dig-dig-doc/commit/5e3ca800274726e44f1d75b21806e795745da701))
* page d'accueil ([ba872f8](https://github.com/IA-Generative/dig-dig-doc/commit/ba872f846f26c829dd1f37134e80f4c023aa34e6))


### Bug Fixes

* remove duplicate migration file with same revision ID ([7eb72e8](https://github.com/IA-Generative/dig-dig-doc/commit/7eb72e81bbbb46ab79d374da3545a80d0d674747))

## [0.3.0-rc.2](https://github.com/IA-Generative/dig-dig-doc/compare/v0.3.0-rc.1...v0.3.0-rc.2) (2026-09-23)


### Features

* **backend,worker,frontend:** chat task with streaming + sources, markdown rendering, analyse description ([49fd177](https://github.com/IA-Generative/dig-dig-doc/commit/49fd17747e71900304a64a5b88742e23bfd260f2))
* **worker,backend:** classification & entity extraction tasks ([c1602b5](https://github.com/IA-Generative/dig-dig-doc/commit/c1602b55020fe744fa30f48d09f66cf457bb50c8))

## [0.3.0-rc.1](https://github.com/IA-Generative/dig-dig-doc/compare/v0.3.0-rc...v0.3.0-rc.1) (2026-09-23)


### Features

* **backend,frontend:** choix du modèle LLM ([613cb7b](https://github.com/IA-Generative/dig-dig-doc/commit/613cb7b7a57547a7f59c44183cfd35482a81d890))
* **backend,frontend:** choix du modèle LLM pour conversations et agents ([37bad13](https://github.com/IA-Generative/dig-dig-doc/commit/37bad13a103c3655421f43c41d7f32c87b1dd903))
* **backend,frontend:** pagination des listes + système de jetons d'application ([7923b08](https://github.com/IA-Generative/dig-dig-doc/commit/7923b0870b0c3736772306ef94a98755410d1d46))
* **backend:** health check étendu à postgres et s3, sortie pydantic typée ([c42cf64](https://github.com/IA-Generative/dig-dig-doc/commit/c42cf645347b67de45444f6bf064795e5fbafb6d))
* **backend:** logs d'exécution, prédictions par page, partage d'analyse, SSE, CI GitLab ([03cd7d9](https://github.com/IA-Generative/dig-dig-doc/commit/03cd7d9dfe3bf1d590f3451bb1e59140315ecc9f))
* **backend:** modèle de données et endpoints analyses/dossiers ([479c4d1](https://github.com/IA-Generative/dig-dig-doc/commit/479c4d1fd837abffd33dbedbe67b655e1a674ab6))
* **backend:** prédictions et sources de message comme ensembles de pages/bbox ([9654a92](https://github.com/IA-Generative/dig-dig-doc/commit/9654a922a9cc699087bd3022bbfb731c64e65f3c))
* connecte le frontend au backend, ajoute conversations et métadonnées de document ([a8cb97c](https://github.com/IA-Generative/dig-dig-doc/commit/a8cb97c467ff9bac2252e2b2d120d399a5ebf146))
* extraction de texte du worker, écran d'accueil DSFR, conversations en sidebar ([9ed9607](https://github.com/IA-Generative/dig-dig-doc/commit/9ed9607307d97d9fee3c721e90cb005389501a25))
* **report:** add reporting ([f0996e7](https://github.com/IA-Generative/dig-dig-doc/commit/f0996e74549d720edc9c2f489f38c5c1c191b688))
* **worker,backend:** extraction de texte (issue [#4](https://github.com/IA-Generative/dig-dig-doc/issues/4)) + captures de page relayées par le backend ([a705bb2](https://github.com/IA-Generative/dig-dig-doc/commit/a705bb21be914eb7b365a814461600117f9d2bd0))
* **worker:** client HTTP authentifié par jeton vers le BFF ([b448a76](https://github.com/IA-Generative/dig-dig-doc/commit/b448a7677921243a0bd913a814d9759e4395f6d0))
* **worker:** extrait aussi les bbox des blocs de mise en page ([6eea40a](https://github.com/IA-Generative/dig-dig-doc/commit/6eea40a7568d59f6bfa773b9974c3389028027b3))


### Bug Fixes

* **backend:** bounding_boxes devient sa propre table, rattachée à une page ([83013c6](https://github.com/IA-Generative/dig-dig-doc/commit/83013c6cf201a5dfb86e25b6dab76bb78b1a2d8a))
* unittest ([66c9c4c](https://github.com/IA-Generative/dig-dig-doc/commit/66c9c4c2860fedf0578db899f5597b838e8294f6))

## [0.3.0-rc](https://github.com/IA-Generative/dig-dig-doc/compare/v0.2.0...v0.3.0-rc) (2026-09-22)


### Features

* **backend:** authentification Keycloak du BFF, comme Muffin ([87bba53](https://github.com/IA-Generative/dig-dig-doc/commit/87bba53a09533295e0a35226d2fa674553904385))

## [0.2.0](https://github.com/IA-Generative/dig-dig-doc/compare/v0.1.0...v0.2.0) (2026-09-22)


### Features

* **frontend:** bandeau avec profil connexion/déconnexion et sidebar collapsable ([a686991](https://github.com/IA-Generative/dig-dig-doc/commit/a6869917ff8ebc13ecdc8d44fe16a56bd37c4c74))
* **frontend:** définition directe des outils (tools) d'un agent ([3c77f07](https://github.com/IA-Generative/dig-dig-doc/commit/3c77f07d5ae72a21610bbc88a923e5c15998c5e6))
* **frontend:** modernise l'aide LLM et ajoute pagination + aide par élément ([01e9f78](https://github.com/IA-Generative/dig-dig-doc/commit/01e9f7828b68bce09e789b82afea7462d05a645c))
* **frontend:** onglets pour les trois sections d'une analyse ([9c50b33](https://github.com/IA-Generative/dig-dig-doc/commit/9c50b33157390a1d0a44eda16efc59f7f73eb40c))
* **frontend:** page Analyses (liste, recherche, pagination) et gestion d'une analyse ([e51ef82](https://github.com/IA-Generative/dig-dig-doc/commit/e51ef82ea1f6b07ab31be092578d4ee6e484cd29))
* **frontend:** page de résultat d'un dossier, sortie activable par agent ([5ba6310](https://github.com/IA-Generative/dig-dig-doc/commit/5ba63108c26d0ff85ea67c014ee4193340b1d662))
* **frontend:** page dossier façon ChatGPT, versionne tools et output ([ac3b24e](https://github.com/IA-Generative/dig-dig-doc/commit/ac3b24e23306de6076d767194e99ff1a604210be))
* **frontend:** page Dossiers (liste, exécution, documents) ([dcc0f7a](https://github.com/IA-Generative/dig-dig-doc/commit/dcc0f7aa09240644bd3c3fc000281386ddbd0950))
* **frontend:** pagination du tableau des dossiers ([eeed952](https://github.com/IA-Generative/dig-dig-doc/commit/eeed952a226795913af1aa628dcb189aafbbbd8b))
* **frontend:** remet Dossiers avec le même style que Analyses ([372a6da](https://github.com/IA-Generative/dig-dig-doc/commit/372a6da3e382c5d70d2801a4b995849ecce62bd5))
* **frontend:** résultats du dossier en carrousel de cartes cliquables ([38a9e55](https://github.com/IA-Generative/dig-dig-doc/commit/38a9e5503992757b794eb30c9615f81f1b79c6a5))
* **frontend:** résultats du dossier visibles directement, jauge de confiance ([55e7ca0](https://github.com/IA-Generative/dig-dig-doc/commit/55e7ca0cd03a5e306f4aee6dadfc6f8db9218439))
* **frontend:** retire Tableau de bord/Dossiers, connexion en bas de sidebar ([13b531d](https://github.com/IA-Generative/dig-dig-doc/commit/13b531d49359e218f4fdebd66f227122782fce0b))
* **frontend:** socle DSFR avec sidebar (Vue + vue-dsfr) ([fa5cad9](https://github.com/IA-Generative/dig-dig-doc/commit/fa5cad92c53bda8cb32efea4785609727f5cdb80))
* **frontend:** versionning des labels et des entités, comme le prompt ([512f9b0](https://github.com/IA-Generative/dig-dig-doc/commit/512f9b0be6013b6a635745175b8d58b7fbeeda1c))


### Bug Fixes

* **frontend:** copie .dsfr.yml avant l'install pnpm dans le Dockerfile ([1d56867](https://github.com/IA-Generative/dig-dig-doc/commit/1d568675327585ab942371afff21fd29d16d9976))
* **frontend:** réserve les outils (tools) aux vrais agents ([ae8f20a](https://github.com/IA-Generative/dig-dig-doc/commit/ae8f20aedec2838fa80af34bead9b90e4c8e8218))


### Code Refactoring

* **frontend:** découpe les composants d'analyse, ajoute labels et entités ([b8ede37](https://github.com/IA-Generative/dig-dig-doc/commit/b8ede3774a0cb2b63ab22c260aafd8766731c3ec))
* **frontend:** la classification et l'extraction ne sont plus des agents ([a464c16](https://github.com/IA-Generative/dig-dig-doc/commit/a464c167c15166fcf5e4afa9fb6f719c9f45eb37))
