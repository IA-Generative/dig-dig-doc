# Statuts de dossier par analyse (backend)

Issue #168, parent #167. Chaque **analyse** définit ses propres **statuts de dossier** ; chaque dossier rattaché à une analyse a l'un d'eux. Ils sont **distincts** du champ `status` d'un dossier (`en_attente`, `en_cours`, `terminé`…), qui reste l'état d'**exécution** de l'analyse automatique.

## Modèle

| Table | Champs |
| --- | --- |
| `status_definitions` | `id`, `analyse_id`, `name`, `color` (`#RRGGBB`), `position`, `is_initial`, `is_final`. |
| `dossiers` (ajouts) | `workflow_status_id` (FK `status_definitions`, `RESTRICT`), `closed_at`. |

- **Initial** : le statut que reçoit un dossier à sa création ou à son rattachement à une analyse. **Un seul** par analyse.
- **Final** : le dossier est **clos**. Passer dans un statut final pose `closed_at` (conservée d'un statut final à un autre) ; tout autre statut l'efface. `closed_at` alimente les indicateurs du tableau de bord (#174) : clôturés, traités par semaine, délai moyen.
- Un dossier « à ranger » (sans analyse) n'a **pas de statut** ; il reçoit le statut initial de l'analyse qui l'accueille.
- Toute nouvelle analyse reçoit trois statuts par défaut : *À instruire* (initial), *En instruction*, *Terminé* (final).
- Contrairement aux labels et aux entités (recréés à chaque enregistrement), un statut **garde son identifiant** : les dossiers y font référence.

## API

| Route | Effet |
| --- | --- |
| `GET /api/analyses/{id}/statuses` | Statuts de l'analyse, dans l'ordre. |
| `PUT /api/analyses/{id}/statuses` | Remplace la liste (voir ci-dessous) ; renvoie l'analyse, avec `statuses` et `statuses_versions`. |
| `POST /api/analyses/{id}/statuses/restore/{version_id}` | Restaure une version antérieure. |
| `PUT /api/dossiers/{id}/workflow-status` | `{"status_id": …}` : change le statut du dossier. |

| `GET /api/dossiers?workflow_status_id=…&sort=…` | Liste des dossiers : `workflow_status_id` ne garde que ce statut ; `sort=status` trie par statut, dans l'ordre défini par chaque analyse (dossiers sans statut en dernier), puis du plus récent au plus ancien (`sort=created_at`, par défaut). |
| `GET /api/analyses` | Chaque élément porte aussi ses `statuses` (la liste des dossiers s'en sert pour son filtre). |

`DossierOut` expose `workflow_status` (`id`, `name`, `color`, `position`, `is_initial`, `is_final`) et `closed_at`.

### Modifier la liste

```json
{
  "statuses": [
    {"id": "…", "name": "À instruire", "color": "#6a6af4", "is_initial": true},
    {"name": "Pièces manquantes", "color": "#b34000"},
    {"id": "…", "name": "Terminé", "color": "#18753c", "is_final": true}
  ],
  "replacements": {"<id d'un statut supprimé>": "<id d'un statut conservé>"}
}
```

- **L'ordre de la liste** donne la position. Un statut qui a un `id` est conservé (renommage, couleur, caractère initial/final modifiables) ; sans `id`, il est créé.
- **Règles** (422) : au moins un statut ; **exactement un initial** ; un statut n'est pas à la fois initial et final ; noms **uniques** (casse ignorée) et non vides ; couleur `#RRGGBB` ; un `id` doit appartenir à l'analyse.
- **Supprimer un statut utilisé** : sans remplaçant dans `replacements`, la réponse est **409** :

```json
{"detail": {"code": "status_in_use", "message": "…", "statuses": [{"id": "…", "name": "En instruction", "dossier_count": 3}]}}
```

  Avec un remplaçant (un statut **conservé**), les dossiers le reprennent et `closed_at` suit son caractère final. Un statut inutilisé se supprime librement.
- **Changer le caractère final** d'un statut clôt (ou rouvre) tous ses dossiers : `closed_at` est recalculé.

## Versionnement

Comme tout champ éditable d'une analyse, la liste est **versionnée** (`FieldVersion`, champ `statuses`) : chaque modification conserve l'état précédent, **identifiants compris**. Restaurer **ajoute** une version (l'état courant devient lui-même une version) et **recrée avec son identifiant** un statut supprimé depuis. Une restauration qui supprimerait des statuts utilisés suit la même règle (409 sans `replacements`, passés dans le corps de la requête). Une modification sans effet ne crée pas de version.

## Migration

La migration `c2d3e4f5a6b7` crée la table, ajoute les deux colonnes, donne **les trois statuts par défaut à chaque analyse existante** et place **tous les dossiers rattachés à une analyse sur son statut initial** (`closed_at` reste vide). Les dossiers « à ranger » restent sans statut. Le retour arrière supprime table et colonnes (la valeur d'enum `STATUSES` de `versioned_field` est conservée : PostgreSQL ne sait pas retirer une valeur d'enum).

## Choix et limites

- Les transitions entre statuts sont **libres** (n'importe quel statut de l'analyse) : « transitions autorisées » reste une question ouverte de #167.
- Comme les autres routes de configuration d'une analyse, celles-ci sont ouvertes à tout utilisateur connecté ; les restrictions de droits arriveront avec l'accès par groupe (#177) et les rôles (#178).
- Les changements de statut, clôtures et réouvertures sont tracés dans le [journal du dossier](journal-du-dossier.md) (#169).
- L'interface (configuration des statuts, pastille, filtre et tri dans la liste, changement de statut) est décrite dans [`statuts-de-dossier`](../frontend/statuts-de-dossier/README.md) (#170).
