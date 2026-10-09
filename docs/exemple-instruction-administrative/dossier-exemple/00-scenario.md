# Scénario du dossier d'exemple

Demande d'aide au logement de **Camille DURAND**, déposée le **2026-10-02** auprès de la commune fictive de Valmont-sur-Orne. Les pièces sont dans ce dossier, à déposer sur la plateforme :

| Fichier | Pièce |
| --- | --- |
| [01-formulaire-demande.md](01-formulaire-demande.md) | Formulaire de demande |
| [02-carte-identite.md](02-carte-identite.md) | Carte nationale d'identité (recto et verso) |
| [03-justificatif-domicile.md](03-justificatif-domicile.md) | Facture d'électricité |
| [04-avis-imposition.md](04-avis-imposition.md) | Avis d'impôt sur le revenu 2026 |
| [05-rib.md](05-rib.md) | RIB |

Les mêmes pièces existent en **PDF** (texte sélectionnable) dans [pdf/](pdf/) : ce sont elles qu'il faut déposer sur la plateforme.

Données **fictives** : personnes, adresses, numéros et IBAN n'existent pas.

## Ce que le dossier contient volontairement

| # | Anomalie | Où | Agent qui doit la trouver |
| --- | --- | --- | --- |
| 1 | **Pas de contrat de bail**, alors que le formulaire le coche comme joint | absent du dossier, `01` | Complétude |
| 2 | **Justificatif de domicile trop ancien** : émis le 2026-05-18, soit plus de 3 mois avant le dépôt (2026-10-02) | `03` | Complétude, Signaux |
| 3 | **Revenu fiscal de référence différent** : 11 200 € déclarés, 14 820 € sur l'avis (écart de 3 620 €, le déclaré étant le plus bas) | `01` et `04` | Cohérence, Signaux |
| 4 | **Titulaire du RIB différent du demandeur** : Julien DURAND | `05` | Cohérence, Signaux |
| 5 | **Montant demandé supérieur au plafond** : 2 400 € demandés, plafond de 3 mois de loyer = 1 920 € (loyer déclaré 640 €) | `01` | Signaux, Synthèse |
| 6 | **Adresse fiscale ancienne** : « 3 rue des Lilas » sur l'avis, « 14 avenue des Tilleuls » ailleurs | `04` | Cohérence (à vérifier) |

## Ce qui ne doit **pas** être signalé

| Élément | Pourquoi |
| --- | --- |
| « 14 av. des Tilleuls » sur la facture, « 14 avenue des Tilleuls » sur le formulaire | Abréviation : tolérance de l'agent de cohérence. |
| « Camille DURAND » (formulaire) et « DURAND Camille Marie » (carte d'identité) | Prénom complémentaire : même personne. |
| Carte d'identité émise en 2020 avec valide jusqu'en 2030 | En cours de validité. |
| Adresse de la carte d'identité (3 rue des Lilas) | Elle date de 2020 : même ancienne adresse que l'avis d'imposition, donc cohérente avec lui. À l'agent de cohérence de la mentionner au plus comme information. |

Un agent qui signale l'un de ces points comme une anomalie produit un **faux positif** : c'est un défaut du prompt à corriger.

## Résultat attendu, agent par agent

- **Complétude :** « Incomplet » : bail manquant, justificatif de domicile à vérifier (trop ancien). À redemander : bail, justificatif de domicile récent.
- **Cohérence croisée :** « Incohérence détectée » : revenu fiscal de référence (11 200 / 14 820) et titulaire du RIB. Adresse fiscale « À vérifier ». Adresses formulaire / facture « Écart toléré ».
- **Signaux d'anomalie :** niveau « Élevé » (revenu déclaré inférieur à l'avis, titulaire du RIB, montant au-dessus du plafond), signaux « à vérifier » pour la facture trop ancienne.
- **Synthèse :** recommandation « Demander des pièces ou des précisions » ou « Vérification approfondie nécessaire », avec le plafond calculé (1 920 €) et la mention que la décision revient à l'instructeur.

## Classification attendue

| Fichier | Label |
| --- | --- |
| `01` | Formulaire de demande |
| `02` (2 pages) | Pièce d'identité |
| `03` | Justificatif de domicile |
| `04` | Avis d'imposition |
| `05` | RIB |

## Entités attendues (extraction)

Nom de famille : DURAND · Prénom : Camille · Date de naissance : 1991-03-14 · Numéro de la pièce d'identité : 20AB12345 · Fin de validité : 2030-06-11 · Adresse déclarée : 14 avenue des Tilleuls, 76000 Valmont-sur-Orne · Adresse du justificatif : 14 av. des Tilleuls, 76000 Valmont-sur-Orne · Date d'émission du justificatif : 2026-05-18 · Adresse fiscale : 3 rue des Lilas, 76000 Valmont-sur-Orne · Revenu déclaré : 11200 · Revenu de l'avis : 14820 · Parts : 1 · Année des revenus : 2025 · Loyer : 640 · Aide demandée : 2400 · Titulaire du compte : M. Julien DURAND · IBAN : FR7600000000000000000000000 · Formulaire signé : oui.

Sert à vérifier l'extraction : un écart ici pointe un défaut des définitions d'entités ou de la qualité du texte lu, pas des agents.
