# Changelog

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
