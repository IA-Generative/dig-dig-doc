# Scénario du dossier d'exemple

M. **Marek ILIEV** (nationalité **valdorienne**, pays fictif), représenté par **Me Sophie LAMBERT** et bénéficiaire de l'aide juridictionnelle, conteste devant le **tribunal administratif de Rouen** un arrêté de la **préfecture de Valmont** : refus de titre de séjour et obligation de quitter le territoire dans un délai de 30 jours. Tu es le **service du contentieux de la préfecture** : la requête vient d'être communiquée.

Les pièces sont à déposer sur la plateforme, en PDF ([pdf/](pdf/)) :

| Fichier | Pièce |
| --- | --- |
| [01-requete.md](01-requete.md) | Requête introductive d'instance (2 pages) |
| [02-arrete-attaque.md](02-arrete-attaque.md) | Arrêté de refus de titre et OQTF, avec voies et délais |
| [03-pv-notification.md](03-pv-notification.md) | Procès-verbal de notification |
| [04-recepisse-aide-juridictionnelle.md](04-recepisse-aide-juridictionnelle.md) | Récépissé de dépôt de la demande d'aide juridictionnelle |
| [05-decision-aide-juridictionnelle.md](05-decision-aide-juridictionnelle.md) | Décision du bureau d'aide juridictionnelle |
| [06-bordereau-pieces.md](06-bordereau-pieces.md) | Bordereau de pièces annexées |
| [07-courrier-greffe.md](07-courrier-greffe.md) | Communication de la requête par le greffe |

Données **fictives** : personnes, avocate, pays, numéros d'étranger, numéros de requête. Les règles de délai sont celles de l'exemple de test, à faire valider par un juriste.

## La chronologie réelle

| Date | Événement | Source |
| --- | --- | --- |
| 2025-11-10 | Demande de titre de séjour | `02` |
| 2026-02-27 | Arrêté de refus et OQTF (30 jours) | `02` |
| 2026-03-03 | Notification, remise en main propre | `03` |
| 2026-03-25 | Dépôt de la demande d'aide juridictionnelle (**avant** la fin du délai) | `04` |
| 2026-04-01 | Décision d'aide juridictionnelle : admission | `05` |
| 2026-04-02 | Fin du premier délai de recours (03/03 + 30 jours) | calculé |
| 2026-04-03 | Décision d'aide juridictionnelle notifiée à l'avocate | `05` |
| 2026-04-09 | Requête enregistrée au greffe | `01` |
| 2026-04-14 | Communication de la requête | `07` |
| 2026-05-03 | Fin du nouveau délai (03/04 + 30 jours) | calculé |
| 2026-05-12 | Date limite du mémoire en défense (28 jours après le courrier du greffe) | `07` |
| 2026-05-26 | Clôture de l'instruction | `07` |

## Ce que le dossier contient volontairement

| # | Point | Où | Agent qui doit le trouver |
| --- | --- | --- | --- |
| 1 | **Numéro d'étranger différent** : `7501234567` (arrêté, procès-verbal de notification) contre `7501234576` (requête, récépissé et décision d'aide juridictionnelle) : deux chiffres inversés. | `01`, `02`, `03`, `04`, `05` | Identité et présence |
| 2 | **Durée de présence en désaccord** : la requête allègue une présence depuis le **2018-02-14** (8 ans) ; l'arrêté retient une entrée le **2021-02-14** d'après les déclarations de l'intéressé : 3 ans d'écart. | `01`, `02` | Identité et présence |
| 3 | **Pièces 4 et 5 absentes** : les justificatifs de présence depuis 2018 et le contrat de travail sont au bordereau, pas dans le dossier. Ce sont elles qui appuient le premier moyen. | `06` | Moyens et pièces |
| 4 | **Moyen sans appui** : l'ancienneté de 8 ans repose sur la seule affirmation de la requête. | `01` | Moyens et pièces |
| 5 | **Piège de recevabilité** : sans tenir compte de l'aide juridictionnelle, la requête est enregistrée 7 jours après la fin du délai (2026-04-09 contre 2026-04-02). Avec la demande d'aide juridictionnelle déposée à temps (2026-03-25), le délai est interrompu et la requête est dans le nouveau délai (jusqu'au 2026-05-03). | `01`, `03`, `04`, `05` | Recevabilité |

## Ce qui ne doit **pas** être signalé comme signal de forclusion

| Élément | Pourquoi |
| --- | --- |
| La requête enregistrée 37 jours après la notification | L'aide juridictionnelle a interrompu le délai : l'agent doit présenter **les deux calculs** et ne pas retenir le retard comme un signal. |
| « Me Sophie LAMBERT » / « Maître LAMBERT » | Même personne. |
| La mention de l'interprète par téléphone dans le procès-verbal | Information de notification, pas une anomalie. |
| L'admission à l'aide juridictionnelle | Elle n'a aucun lien avec le fond du litige. |

Un agent qui signale l'un de ces points comme une anomalie produit un **faux positif** : c'est un défaut du prompt à corriger. Le point 5 est le plus délicat : un modèle peu attentif conclura au retard sans voir l'aide juridictionnelle.

## Résultat attendu, agent par agent

- **Recevabilité :** niveau « Aucun signal » ou « Points à examiner », jamais « Doute sérieux ». Les deux calculs sont présentés (retard de 7 jours sans aide juridictionnelle, dans les délais avec). La décision revient au service du contentieux.
- **Identité et durée de présence :** « Divergence détectée » : numéro d'étranger (les deux valeurs et les sources), date d'entrée (2018 allégué, 2021 retenu, 3 ans d'écart). Nom et date de naissance concordent. Aucun jugement sur la personne.
- **Moyens et pièces :** 3 conclusions (annulation, injonction ou réexamen, 1 200 €), 4 moyens, pièces 1 à 3 présentes, 4 et 5 absentes ; l'ancienneté de présence est « non appuyée ».
- **Plan du mémoire en défense :** date limite 2026-05-12, recevabilité à soumettre au juriste avec les deux calculs, divergence d'identité à vérifier avant de défendre, pièces à réunir (dossier administratif de la demande du 2025-11-10, déclarations d'entrée en France).

## Classification attendue

| Fichier | Label |
| --- | --- |
| `01` (2 pages) | Requête introductive d'instance |
| `02` | Arrêté attaqué |
| `03` | Preuve de notification |
| `04` | Demande d'aide juridictionnelle |
| `05` | Décision d'aide juridictionnelle |
| `06` | Bordereau de pièces |
| `07` | Courrier du greffe |

## Entités attendues (extraction)

Juridiction : Tribunal administratif de Rouen · Numéro : 2601789-4 · Enregistrement : 2026-04-09 · Requérant : Marek ILIEV · Naissance : 1990-05-17 · Numéro d'étranger : 7501234576 (requête, `04`, `05`) ou 7501234567 (`02`, `03`) selon la pièce · Avocate : Me Sophie LAMBERT · Barreau : Rouen · Autorité : préfecture de Valmont · Objet : refus de titre de séjour et OQTF · Décision : 2026-02-27 · Délai de départ : 30 · Notification prouvée : 2026-03-03 · Voies et délais : oui · Entrée retenue : 2021-02-14 · Entrée alléguée : 2018-02-14 · Demande d'AJ : 2026-03-25 · Décision d'AJ : 2026-04-01 · Notification de l'AJ : 2026-04-03 · Limite du mémoire : 2026-05-12 · Clôture : 2026-05-26 · Frais : 1200.

Sert à vérifier l'extraction : un écart ici pointe un défaut des définitions d'entités. Les deux numéros d'étranger doivent être recopiés **sans correction**.
