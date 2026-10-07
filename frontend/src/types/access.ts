// Accès aux dossiers par groupe (issue #177, partie UI). Les données sont
// simulées (useDossierAccess) en attendant le backend : association dossier
// ↔ groupes Keycloak et filtre de visibilité côté serveur.

/** « restricted » : seuls les groupes associés (et les administrateurs). « analyse » : tout utilisateur ayant accès à l'analyse. */
export type Visibility = "restricted" | "analyse";

export const VISIBILITY_LABELS: Record<Visibility, string> = {
  restricted: "Restreint",
  analyse: "Selon l'analyse",
};

export const VISIBILITY_HINTS: Record<Visibility, string> = {
  restricted: "Seuls les membres des groupes choisis (et les administrateurs) voient ce dossier.",
  analyse: "Toute personne ayant accès à l'analyse voit ce dossier.",
};

export interface DossierAccess {
  visibility: Visibility;
  /** Chemins de groupes Keycloak, comparés tels quels (pas d'héritage entre groupes). */
  groups: string[];
}

export interface AccessChange {
  at: string;
  by: string;
  text: string;
}

/** « /service-culture » → « Service culture » (le chemin exact reste visible en infobulle). */
export function groupLabel(path: string): string {
  const name = path.replace(/^\//, "").replace(/[-_]/g, " ");
  return name.charAt(0).toUpperCase() + name.slice(1);
}
