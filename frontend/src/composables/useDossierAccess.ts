import { computed, ref } from "vue";

import { useAuth } from "@/composables/useAuth";
import type { AccessChange, DossierAccess, Visibility } from "@/types/access";
import { groupLabel } from "@/types/access";

// MOCK (issue #177, partie UI) : état partagé au niveau du module, à
// remplacer par l'API (association dossier ↔ groupes, filtre de visibilité
// côté serveur). Règles reproduites ici :
//  - un dossier existant est « Selon l'analyse » (migration sans perte d'accès) ;
//  - un nouveau dossier est « Restreint » par défaut, avec au moins un groupe ;
//  - on n'associe que SES groupes (y compris un administrateur) ;
//  - seuls les administrateurs modifient l'accès d'un dossier existant ;
//  - pas d'héritage entre groupes ; un administrateur voit tout.

/** Groupes de l'utilisateur si le profil n'en fournit pas (environnement de démo). */
const DEMO_GROUPS = ["/service-culture", "/service-sport"];

/** Membres (identifiants du tableau de suivi) de quelques groupes de démo. */
const GROUP_MEMBERS: Record<string, string[]> = {
  "/service-culture": ["u1", "u2", "u3"],
  "/service-sport": ["u4", "u5"],
  "/service-social": ["u2", "u5"],
};

const access = ref<Record<string, DossierAccess>>({
  "trk-3": { visibility: "restricted", groups: ["/service-culture"] },
  "trk-7": { visibility: "restricted", groups: ["/service-sport"] },
  "trk-12": { visibility: "restricted", groups: ["/service-culture", "/service-social"] },
  // Aucun groupe commun avec l'utilisateur de démo : invisible pour un non-administrateur.
  "trk-20": { visibility: "restricted", groups: ["/service-social"] },
});

/** Dossiers dont l'utilisateur a perdu l'accès (démo des notifications masquées). */
const revoked = ref<Set<string>>(new Set(["mock-1"]));

const changes = ref<Record<string, AccessChange[]>>({});

export function useDossierAccess() {
  const { profile, isAdmin } = useAuth();

  const myGroups = computed(() => (profile.value?.groups.length ? profile.value.groups : DEMO_GROUPS));

  const accessOf = (dossierId: string): DossierAccess =>
    access.value[dossierId] ?? { visibility: "analyse", groups: [] };

  /** Un utilisateur voit un dossier s'il est administrateur, s'il partage un groupe associé, ou si le dossier suit l'analyse. */
  function canSee(dossierId: string): boolean {
    if (isAdmin.value) return true;
    const a = accessOf(dossierId);
    return a.visibility === "analyse" || a.groups.some((g) => myGroups.value.includes(g));
  }

  /** Une personne (identifiant de démo) a-t-elle accès à ce dossier ? Sert à limiter l'affectation. */
  function memberHasAccess(dossierId: string, memberId: string): boolean {
    const a = accessOf(dossierId);
    return a.visibility === "analyse" || a.groups.some((g) => GROUP_MEMBERS[g]?.includes(memberId));
  }

  /** Personnes qui perdraient l'accès si l'on passait de `before` à `after`. */
  function lostMembers(before: DossierAccess, after: DossierAccess): string[] {
    const has = (a: DossierAccess, id: string) =>
      a.visibility === "analyse" || a.groups.some((g) => GROUP_MEMBERS[g]?.includes(id));
    const everyone = [...new Set(Object.values(GROUP_MEMBERS).flat())];
    return everyone.filter((id) => has(before, id) && !has(after, id));
  }

  function groupsLostBy(before: DossierAccess, after: DossierAccess): string[] {
    return before.visibility === "restricted" && after.visibility === "restricted"
      ? before.groups.filter((g) => !after.groups.includes(g))
      : [];
  }

  /** Enregistre l'accès d'un dossier (administrateur) et trace le changement. */
  function setAccess(dossierId: string, next: DossierAccess, by = "Vous") {
    const before = accessOf(dossierId);
    const entries: string[] = [];
    if (before.visibility !== next.visibility) {
      entries.push(next.visibility === "restricted" ? "Dossier restreint" : "Dossier ouvert selon l'analyse");
    }
    for (const g of next.groups.filter((g) => !before.groups.includes(g))) entries.push(`Groupe « ${groupLabel(g)} » ajouté`);
    for (const g of before.groups.filter((g) => !next.groups.includes(g))) entries.push(`Groupe « ${groupLabel(g)} » retiré`);
    access.value = { ...access.value, [dossierId]: { visibility: next.visibility, groups: [...next.groups] } };
    const at = new Date().toISOString();
    changes.value = {
      ...changes.value,
      [dossierId]: [...entries.map((text) => ({ at, by, text })), ...(changes.value[dossierId] ?? [])],
    };
  }

  /** Accès initial d'un dossier créé (aucun droit particulier du créateur : il passe par ses groupes). */
  function initAccess(dossierId: string, next: DossierAccess) {
    access.value = { ...access.value, [dossierId]: { visibility: next.visibility, groups: [...next.groups] } };
  }

  return {
    isAdmin,
    myGroups,
    accessOf,
    canSee,
    memberHasAccess,
    lostMembers,
    groupsLostBy,
    setAccess,
    initAccess,
    changesOf: (id: string) => changes.value[id] ?? [],
    isRevoked: (id: string) => revoked.value.has(id),
  };
}

export type { Visibility };
