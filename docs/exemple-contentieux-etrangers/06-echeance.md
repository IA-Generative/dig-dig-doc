# Échéance

L'échéance suit le **délai de production du mémoire en défense** fixé par le greffe. Les contentieux des étrangers sont jugés vite : les délais du greffe sont courts, et il faut les voir venir tôt ([echeance-du-dossier.md](../backend/echeance-du-dossier.md)).

## Durée par défaut

**30 jours** depuis la création du dossier. Remplace-la par la date du greffe dès que tu la connais.

## Seuils de couleur

Un seuil signifie « N jours restants ou moins ». Au plus 5 seuils, sans doublon.

| Situation | Seuil | Couleur |
| --- | --- | --- |
| Loin | plus de 15 jours restants | `#18753c` |
| Proche | 15 jours ou moins | `#b34000` |
| Urgent | 7 jours ou moins | `#ce0500` |
| Imminent | 3 jours ou moins | `#8a0000` |
| Dépassée | échéance passée | `#5c0000` |

```json
{
  "default_due_days": 30,
  "thresholds": {
    "far_color": "#18753c",
    "steps": [
      { "days": 15, "color": "#b34000" },
      { "days": 7, "color": "#ce0500" },
      { "days": 3, "color": "#8a0000" }
    ],
    "overdue_color": "#5c0000"
  }
}
```

## Pour le dossier d'exemple

Le greffe fixe la production au **2026-05-12**. Ce dossier a donc, aujourd'hui, une échéance **dépassée** dans l'application : c'est un dossier historique, utile pour voir la couleur « dépassée ». Pour voir les autres paliers, change l'échéance du dossier.
