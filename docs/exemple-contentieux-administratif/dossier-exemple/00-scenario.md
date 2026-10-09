# Scénario du dossier d'exemple

M. **Samir BENALI**, représenté par **Me Hélène MARCHAND** (barreau de Rouen), conteste devant le **tribunal administratif de Rouen** le refus de la commune fictive de Valmont-sur-Orne de lui accorder une aide exceptionnelle au logement. Tu es le **service juridique de la commune** : la requête vient d'être communiquée.

Les pièces sont à déposer sur la plateforme, en PDF ([pdf/](pdf/)) :

| Fichier | Pièce |
| --- | --- |
| [01-requete.md](01-requete.md) | Requête introductive d'instance (2 pages) |
| [02-decision-attaquee.md](02-decision-attaquee.md) | Décision de refus du maire, avec voies et délais |
| [03-accuse-reception.md](03-accuse-reception.md) | Avis de réception postal |
| [04-recours-gracieux.md](04-recours-gracieux.md) | Recours gracieux de l'avocate, avec tampon de la mairie |
| [05-bordereau-pieces.md](05-bordereau-pieces.md) | Bordereau de pièces annexées |
| [06-courrier-greffe.md](06-courrier-greffe.md) | Communication de la requête par le greffe |

Données **fictives** : personnes, avocats, numéros et références n'existent pas. Les règles de délai utilisées sont celles de l'exemple de test, à faire valider par un juriste.

## La chronologie réelle

| Date | Événement | Source |
| --- | --- | --- |
| 2026-03-10 | Décision de refus | `02` |
| 2026-03-14 | Notification (remise du recommandé) | `03` |
| 2026-05-06 | Recours gracieux envoyé, avant la fin du premier délai : il le prolonge | `04` |
| 2026-05-14 | Fin du premier délai de recours (14/03 + 2 mois) | calculé |
| 2026-05-08 | Recours gracieux reçu en mairie (tampon) | `04` |
| 2026-07-08 | Rejet implicite (08/05 + 2 mois) | calculé |
| 2026-09-08 | Fin du délai de recours contentieux (08/07 + 2 mois) | calculé |
| 2026-09-18 | Requête enregistrée au greffe : **10 jours après** | `01` |
| 2026-09-25 | Communication de la requête | `06` |
| 2026-11-20 | Date limite du mémoire en défense | `06` |
| 2026-12-04 | Clôture de l'instruction | `06` |

## Ce que le dossier contient volontairement

| # | Anomalie | Où | Agent qui doit la trouver |
| --- | --- | --- | --- |
| 1 | **Date de rejet implicite fausse** : la requête affirme le 2026-07-20, alors que le tampon prouve une réception le 2026-05-08, soit un rejet implicite le **2026-07-08**. Avec la date alléguée, la requête semble dans les délais (échéance au 2026-09-20) ; avec la date prouvée, elle est déposée 10 jours trop tard (échéance au 2026-09-08). | `01` et `04` | Recevabilité, Pièces et chronologie |
| 2 | **Pièce n° 4 absente** : l'attestation de l'employeur est au bordereau mais pas dans le dossier. C'est la pièce qui appuie le premier moyen (la prime exceptionnelle). | `05` | Pièces et chronologie, Moyens |
| 3 | **Nom écrit différemment** : « BENALLI » (décision et accusé de réception) / « BENALI » (requête, recours). Probable faute de frappe de la commune. | `02`, `03` | Pièces et chronologie (à signaler en information) |
| 4 | **Moyen sans appui** : le premier moyen (prime de 2 100 €) repose sur la seule affirmation de l'avocate, sans la pièce n° 4. | `01` | Moyens et conclusions |

## Ce qui ne doit **pas** être signalé comme anomalie

| Élément | Pourquoi |
| --- | --- |
| Recours gracieux envoyé le 2026-05-06, avant la fin du premier délai (2026-05-14) | Il est dans le délai : il prolonge le délai de recours. |
| Notification le 2026-03-14 dans la requête et dans l'accusé de réception | Elles concordent. |
| « Me Hélène MARCHAND » / « Maître Marchand » | Même personne, formule de politesse. |
| Montant de 2 400 € dans la requête, la décision et le recours | Il est partout identique. |
| Décision qui mentionne les voies et délais | Le délai de 2 mois est donc opposable. |

Un agent qui signale l'un de ces points comme une anomalie produit un **faux positif** : c'est un défaut du prompt à corriger.

## Résultat attendu, agent par agent

- **Recevabilité :** niveau « Doute sérieux sur le délai ». Elle doit calculer la chaîne de dates ci-dessus, repérer l'écart de 12 jours (2026-07-08 prouvé contre 2026-07-20 allégué), constater que la requête est enregistrée 10 jours après l'échéance, et renvoyer la décision au service juridique. Elle ne doit pas conclure à l'irrecevabilité.
- **Moyens et conclusions :** trois conclusions (annulation, injonction de 2 400 €, frais de 1 500 €), trois moyens (erreur de fait, erreur manifeste d'appréciation, défaut d'examen particulier). Le premier moyen répond au motif du dépassement du plafond de 14 000 €, mais s'appuie sur une pièce absente.
- **Pièces et chronologie :** pièces 1 à 3 présentes, pièce 4 absente ; chronologie correcte, avec l'écart entre la date alléguée et la date prouvée du rejet implicite.
- **Plan du mémoire en défense :** résumé du litige ; date limite 2026-11-20 (56 jours après le courrier du greffe du 2026-09-25) ; recevabilité à soumettre au juriste, avec les dates prouvées ; fond : pièces à demander (avis d'imposition de 2026, règlement communal d'aide, dossier d'instruction AL-2026-0142).

## Classification attendue

| Fichier | Label |
| --- | --- |
| `01` (2 pages) | Requête introductive d'instance |
| `02` | Décision attaquée |
| `03` | Preuve de notification |
| `04` | Recours gracieux |
| `05` | Bordereau de pièces |
| `06` | Courrier du greffe |

## Entités attendues (extraction)

Juridiction : Tribunal administratif de Rouen · Numéro : 2603456-9 · Enregistrement : 2026-09-18 · Requérant : Samir BENALI · Avocate : Me Hélène MARCHAND · Barreau : Rouen · Défenderesse : commune de Valmont-sur-Orne · Objet : refus d'aide exceptionnelle au logement · Date de la décision : 2026-03-10 · Notification prouvée : 2026-03-14 · Voies et délais mentionnés : oui · Envoi du recours gracieux : 2026-05-06 · Réception du recours gracieux : 2026-05-08 · Rejet implicite allégué : 2026-07-20 · Limite du mémoire : 2026-11-20 · Clôture : 2026-12-04 · Aide demandée : 2400 · Frais : 1500.

Sert à vérifier l'extraction : un écart ici pointe un défaut des définitions d'entités, pas des agents. Attention à la **date de rejet implicite alléguée** (2026-07-20) : elle ne doit pas être confondue avec la date calculée.
