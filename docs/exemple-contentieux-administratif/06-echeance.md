# Échéance

Ici l'échéance suit le **délai de production du mémoire en défense**, fixé par le greffe : à ajuster dossier par dossier à partir du courrier du greffe ([echeance-du-dossier.md](../backend/echeance-du-dossier.md)).

## Durée par défaut

**60 jours** depuis la création du dossier, un ordre de grandeur courant pour un premier mémoire en défense. Remplace-la par la date du greffe dès que tu la connais.

## Seuils de couleur

Un seuil signifie « N jours restants ou moins ». Au plus 5 seuils, sans doublon.

| Situation | Seuil | Couleur |
| --- | --- | --- |
| Loin | plus de 30 jours restants | `#18753c` (vert) |
| Proche | 30 jours ou moins | `#b34000` (orange) |
| Urgent | 15 jours ou moins | `#ce0500` (rouge) |
| Imminent | 5 jours ou moins | `#8a0000` (rouge foncé) |
| Dépassée | échéance passée | `#5c0000` (bordeaux) |

Forme JSON équivalente :

```json
{
  "default_due_days": 60,
  "thresholds": {
    "far_color": "#18753c",
    "steps": [
      { "days": 30, "color": "#b34000" },
      { "days": 15, "color": "#ce0500" },
      { "days": 5, "color": "#8a0000" }
    ],
    "overdue_color": "#5c0000"
  }
}
```

## Pourquoi plus de seuils que pour l'instruction

Une échéance contentieuse dépassée peut priver l'administration de sa défense écrite : on veut voir arriver la date plus tôt, avec un palier de plus.

## Pour le dossier d'exemple

Le greffe fixe la production au **2026-11-20**. Positionne l'échéance du dossier à cette date.
