# Échéance

L'échéance suit le **délai de production du mémoire en défense** fixé par le greffe ([echeance-du-dossier.md](../backend/echeance-du-dossier.md)).

## Durée par défaut

**45 jours** depuis la création du dossier. Remplace-la par la date du greffe dès que tu la connais.

## Seuils de couleur

Un seuil signifie « N jours restants ou moins ». Au plus 5 seuils, sans doublon.

| Situation | Seuil | Couleur |
| --- | --- | --- |
| Loin | plus de 20 jours restants | `#18753c` |
| Proche | 20 jours ou moins | `#b34000` |
| Urgent | 10 jours ou moins | `#ce0500` |
| Imminent | 3 jours ou moins | `#8a0000` |
| Dépassée | échéance passée | `#5c0000` |

```json
{
  "default_due_days": 45,
  "thresholds": {
    "far_color": "#18753c",
    "steps": [
      { "days": 20, "color": "#b34000" },
      { "days": 10, "color": "#ce0500" },
      { "days": 3, "color": "#8a0000" }
    ],
    "overdue_color": "#5c0000"
  }
}
```

## Pour le dossier d'exemple

Le greffe fixe la production au **2026-09-04**. À la date du jour, cette échéance est dépassée : c'est un dossier historique, utile pour voir la couleur « dépassée ».
