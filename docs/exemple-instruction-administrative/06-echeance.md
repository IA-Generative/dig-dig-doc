# Échéance

Le délai d'instruction est de **2 mois** à compter du dépôt ; l'échéance est calculée à la création du dossier ([echeance-du-dossier.md](../backend/echeance-du-dossier.md)).

## Durée par défaut

**60 jours** depuis la création du dossier.

## Seuils de couleur

Un seuil signifie « N jours restants ou moins ». Au plus 5 seuils, sans doublon.

| Situation | Seuil | Couleur |
| --- | --- | --- |
| Loin | plus de 30 jours restants | `#18753c` (vert) |
| Proche | 30 jours ou moins | `#b34000` (orange) |
| Urgent | 7 jours ou moins | `#ce0500` (rouge) |
| Dépassée | échéance passée | `#8a0000` (rouge foncé) |

Forme JSON équivalente :

```json
{
  "default_due_days": 60,
  "thresholds": {
    "far_color": "#18753c",
    "steps": [
      { "days": 30, "color": "#b34000" },
      { "days": 7, "color": "#ce0500" }
    ],
    "overdue_color": "#8a0000"
  }
}
```

## Pour le dossier d'exemple

Déposé le 2026-10-02, il a pour échéance le **2026-12-01**. Pour voir une couleur d'alerte, change son échéance depuis la fiche du dossier.
