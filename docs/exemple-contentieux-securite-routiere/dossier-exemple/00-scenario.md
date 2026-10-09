# Scénario du dossier d'exemple

M. **Damien ROUSSEL**, représenté par **Me Julien FABRE**, conteste devant le **tribunal administratif de Rouen** l'arrêté de la **préfecture de Valmont** qui a suspendu son permis de conduire pour quatre mois après un contrôle d'alcoolémie. Tu es le **service du contentieux de la préfecture** : la requête vient d'être communiquée.

Les pièces sont à déposer sur la plateforme, en PDF ([pdf/](pdf/)) :

| Fichier | Pièce |
| --- | --- |
| [01-requete.md](01-requete.md) | Requête introductive d'instance (2 pages) |
| [02-arrete-suspension.md](02-arrete-suspension.md) | Arrêté de suspension, avec voies et délais |
| [03-proces-verbal-controle.md](03-proces-verbal-controle.md) | Procès-verbal du contrôle d'alcoolémie |
| [04-certificat-verification-ethylometre.md](04-certificat-verification-ethylometre.md) | Certificat de vérification périodique de l'éthylomètre |
| [05-pv-notification.md](05-pv-notification.md) | Procès-verbal de notification de l'arrêté |
| [06-courrier-greffe.md](06-courrier-greffe.md) | Communication de la requête par le greffe |

Données **fictives**. Les règles de droit et de métrologie sont celles de l'exemple de test, à faire valider par un juriste.

## La chronologie réelle

| Date | Événement | Source |
| --- | --- | --- |
| 2025-03-11 | Dernière vérification périodique de l'éthylomètre ET-2041 | `04` |
| 2026-03-11 | **Fin de validité de cette vérification** (11/03/2025 + 1 an) | calculé |
| 2026-05-09 | Contrôle d'alcoolémie, permis retenu | `03` |
| 2026-05-12 | Arrêté de suspension (4 mois) | `02` |
| 2026-05-13 | Notification de l'arrêté | `05` |
| 2026-06-30 | Requête enregistrée au greffe | `01` |
| 2026-07-06 | Communication de la requête | `06` |
| 2026-07-13 | Fin du délai de recours (13/05 + 2 mois) : la requête est **13 jours en avance** | calculé |
| 2026-09-04 | Date limite du mémoire en défense (60 jours après le courrier du greffe) | `06` |
| 2026-09-09 | Fin de la suspension | `02` |
| 2026-09-18 | Clôture de l'instruction | `06` |

## Ce que le dossier contient volontairement

| # | Point | Où | Agent qui doit le trouver |
| --- | --- | --- | --- |
| 1 | **Heure de l'infraction différente** : **23 h 40** (procès-verbal), **22 h 40** (arrêté, soit 60 minutes de moins), « aux alentours de 23 h 30 » (requête). L'écart du procès-verbal à l'arrêté est dans un **acte de l'administration**. | `01`, `02`, `03` | Cohérence des faits |
| 2 | **Vérification de l'appareil périmée** : l'éthylomètre ET-2041 avait été vérifié le 2025-03-11, valable jusqu'au 2026-03-11. Le contrôle du 2026-05-09 a eu lieu **59 jours après la fin de validité**. Cela **corrobore le deuxième moyen** de la requête. | `03`, `04` | Moyens et régularité |
| 3 | **Moyen contredit par une pièce** : la requête affirme que M. ROUSSEL n'a jamais été informé de son droit à un second contrôle. Le procès-verbal, **signé par lui**, dit qu'il l'a été et ne l'a pas demandé. | `01`, `03` | Moyens et régularité |
| 4 | **Moyen sans pièce** : la disproportion de la suspension (situation professionnelle) repose sur la seule affirmation de la requête. | `01` | Moyens et régularité |

## Ce qui ne doit **pas** être signalé comme anomalie

| Élément | Pourquoi |
| --- | --- |
| Requête enregistrée le 2026-06-30 | Elle est dans le délai (échéance le 2026-07-13) : l'agent de recevabilité doit conclure « aucun signal ». |
| Immatriculation AB-123-CD, taux 0,62 mg/L, identité et date de naissance | Identiques dans les trois documents. |
| « Aux alentours de 23 h 30 » (requête) face à « 23 h 40 » (procès-verbal) | Heure approximative, écart de 10 minutes : tolérance. L'écart **à signaler** est celui de l'arrêté (22 h 40). |
| « RD 910 » / « route départementale 910 » | Abréviation. |
| La suspension qui prend fin le 2026-09-09, après la date limite du mémoire | À signaler en information, pas comme une irrecevabilité. |

Un agent qui signale l'un de ces points comme une anomalie produit un **faux positif** ; un agent qui **oublie** les points 1 ou 2 est plus grave encore : ils jouent contre l'administration, et c'est précisément ce qu'on veut qu'il dise.

## Résultat attendu, agent par agent

- **Recevabilité :** niveau « Aucun signal ». Échéance le 2026-07-13, requête enregistrée le 2026-06-30, 13 jours d'avance. Mention en information que la suspension se termine le 2026-09-09.
- **Cohérence des faits :** « Divergence détectée » : l'heure (23 h 40 / 22 h 40 / environ 23 h 30), avec l'écart de 60 minutes dans l'arrêté **signalé en priorité comme divergence dans un acte de l'administration**. Identité, immatriculation, taux, lieu et durée concordent.
- **Moyens et régularité :** quatre moyens. Le 1ᵉʳ (information sur le second contrôle) est **contredit** par le procès-verbal signé. Le 2ᵉ (vérification de l'appareil) est **corroboré** : vérification du 2025-03-11, expirée le 2026-03-11. Le 3ᵉ (heure) est corroboré par l'écart. Le 4ᵉ n'est pas établi par une pièce. La rubrique « points qui jouent contre l'administration » contient les moyens 2 et 3.
- **Plan du mémoire en défense :** « Faiblesses à regarder en premier » : vérification périmée et heure de l'arrêté. Date limite 2026-09-04. Pièces à réunir : carnet métrologique de l'appareil et éventuelle vérification plus récente, procès-verbal complet, éventuel rectificatif de l'arrêté.

## Classification attendue

| Fichier | Label |
| --- | --- |
| `01` (2 pages) | Requête introductive d'instance |
| `02` | Arrêté de suspension |
| `03` | Procès-verbal de contrôle |
| `04` | Attestation de vérification de l'appareil |
| `05` | Preuve de notification |
| `06` | Courrier du greffe |

## Entités attendues (extraction)

Juridiction : Tribunal administratif de Rouen · Numéro : 2602345-1 · Enregistrement : 2026-06-30 · Requérant : Damien ROUSSEL · Naissance : 1984-09-02 · Avocat : Me Julien FABRE · Barreau : Rouen · Autorité : préfecture de Valmont · Objet : suspension du permis de conduire · Arrêté : 2026-05-12 · Durée : 4 · Fin : 2026-09-09 · Notification : 2026-05-13 · Voies et délais : oui · Infraction : 2026-05-09 · **Heures : 23 h 40 (PV), 22 h 40 (arrêté), aux alentours de 23 h 30 (requête)** · Taux : 0.62 · Immatriculation : AB-123-CD · Appareil : ET-2041 · Dernière vérification : 2025-03-11 · Information sur le second contrôle : oui · Limite du mémoire : 2026-09-04 · Clôture : 2026-09-18 · Frais : 1200.

Sert à vérifier l'extraction. L'**heure** est l'entité délicate : les trois valeurs doivent toutes être extraites, chacune avec sa source.
