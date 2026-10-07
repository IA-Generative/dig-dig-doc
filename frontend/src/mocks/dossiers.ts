import type { Assignee, CustomField, CustomValue, MockAnalyse, TrackingRow, TrackingStatus } from "@/types/tracking";

// MOCK : jeu de données unique partagé par le tableau de bord (#174), le
// tableau de suivi par analyse et sa vue transversale (#173, #186). Les trois
// écrans montrent ainsi les mêmes dossiers, avec les mêmes totaux. À remplacer
// par l'API.

/** Utilisateur connecté, dans les données simulées. */
export const ME = "u1";

export const ASSIGNEES: Assignee[] = [
  { id: "u1", name: "Alex Martin" },
  { id: "u2", name: "Camille Durand" },
  { id: "u3", name: "Samir Benali" },
  { id: "u4", name: "Léa Petit" },
  { id: "u5", name: "Noah Roux" },
];

// Simplification : toutes les analyses partagent ces statuts. Dans l'application
// réelle ils sont propres à chaque analyse (#168) ; `category` permet de les
// regrouper dans la vue transversale.
export const STATUSES: TrackingStatus[] = [
  { id: "a_instruire", label: "À instruire", tone: "new", final: false, category: "initial" },
  { id: "en_instruction", label: "En instruction", tone: "info", final: false, category: "progress" },
  { id: "pieces_manquantes", label: "Pièces manquantes", tone: "warning", final: false, category: "progress" },
  { id: "a_valider", label: "À valider", tone: "new", final: false, category: "progress" },
  { id: "clos", label: "Clos", tone: "success", final: true, category: "final" },
];

export const MOCK_ANALYSES: MockAnalyse[] = [
  { id: "an-subv", name: "Instruction subventions" },
  { id: "an-urba", name: "Urbanisme" },
  { id: "an-cmd", name: "Commande publique" },
  { id: "an-log", name: "Aides logement" },
  { id: "an-cont", name: "Contentieux" },
];

const SERVICES = ["Culture", "Sport", "Social", "Éducation"];

const field = (f: Partial<CustomField> & Pick<CustomField, "id" | "name" | "type">): CustomField => ({
  definition: "",
  required: false,
  defaultValue: null,
  choices: [],
  currency: "EUR",
  ...f,
});

/** Colonnes personnalisées de départ, par analyse (certaines analyses n'en ont pas). */
export function initialFieldsByAnalyse(): Record<string, CustomField[]> {
  return {
    "an-subv": [
      field({ id: "f_subv_montant", name: "Montant demandé", type: "amount", definition: "Montant de l'aide sollicité par le demandeur, tel qu'indiqué dans le formulaire." }),
      field({ id: "f_subv_service", name: "Service", type: "choice", required: true, defaultValue: "Culture", choices: SERVICES, definition: "Service instructeur en charge du dossier." }),
      field({ id: "f_subv_depot", name: "Date de dépôt", type: "date", definition: "Date de réception du dossier complet. Sert de point de départ au délai d'instruction." }),
      field({ id: "f_subv_prio", name: "Prioritaire", type: "boolean", defaultValue: false, definition: "À cocher quand le dossier doit être traité avant les autres." }),
    ],
    "an-urba": [
      field({ id: "f_urba_surface", name: "Surface (m²)", type: "number", definition: "Surface de plancher créée, en mètres carrés." }),
      field({ id: "f_urba_zone", name: "Zone", type: "choice", choices: ["UA", "UB", "AU", "N"], definition: "Zone du plan local d'urbanisme concernée." }),
    ],
    "an-cmd": [
      field({ id: "f_cmd_montant", name: "Montant HT", type: "amount", definition: "Montant estimé du marché, hors taxes." }),
      field({ id: "f_cmd_procedure", name: "Procédure", type: "choice", choices: ["Adaptée", "Appel d'offres", "Négociée"], definition: "Procédure de passation retenue." }),
    ],
    "an-log": [],
    "an-cont": [],
  };
}

const SUBJECTS: Record<string, string[]> = {
  "an-subv": ["Subvention association Les Mouettes", "Convention de partenariat culturelle", "Aide au projet sportif jeunesse", "Subvention festival de quartier"],
  "an-urba": ["Permis de construire", "Déclaration préalable de travaux", "Certificat d'urbanisme"],
  "an-cmd": ["Marché public fournitures bureau", "Marché entretien espaces verts", "Accord-cadre fournitures scolaires"],
  "an-log": ["Aide rénovation énergétique", "Demande d'allocation logement", "Aide à l'accession"],
  "an-cont": ["Recours gracieux", "Recours contentieux", "Demande de médiation"],
};

const daysFromNow = (d: number) => new Date(Date.now() + d * 86_400_000).toISOString();

function valuesFor(analyseId: string, i: number): Record<string, CustomValue> {
  switch (analyseId) {
    case "an-subv":
      return {
        f_subv_montant: i % 5 === 4 ? null : 1000 + ((i * 937) % 24000),
        f_subv_service: SERVICES[i % SERVICES.length],
        f_subv_depot: daysFromNow(-70 + i).slice(0, 10),
        f_subv_prio: i % 6 === 0,
      };
    case "an-urba":
      return { f_urba_surface: 20 + ((i * 13) % 180), f_urba_zone: ["UA", "UB", "AU", "N"][i % 4] };
    case "an-cmd":
      return { f_cmd_montant: 5000 + ((i * 7919) % 90000), f_cmd_procedure: ["Adaptée", "Appel d'offres", "Négociée"][i % 3] };
    default:
      return {};
  }
}

/** 60 dossiers répartis sur les 5 analyses. */
export function initialDossiers(): TrackingRow[] {
  return Array.from({ length: 60 }, (_, i) => {
    const analyse = MOCK_ANALYSES[i % MOCK_ANALYSES.length];
    const subjects = SUBJECTS[analyse.id];
    return {
      id: `dos-${i + 1}`,
      reference: `DOS-2026-${String(i + 1).padStart(4, "0")}`,
      name: `${subjects[Math.floor(i / MOCK_ANALYSES.length) % subjects.length]} n°${100 + i}`,
      analyseId: analyse.id,
      // Varié au sein de chaque analyse (une analyse reçoit un dossier sur cinq).
      statusId: STATUSES[(i * 7 + Math.floor(i / MOCK_ANALYSES.length)) % STATUSES.length].id,
      // Environ un dossier sur quatre est affecté à l'utilisateur, un sur six n'est pas affecté.
      assigneeId: i % 6 === 5 ? null : i % 4 === 0 ? ME : ASSIGNEES[1 + (i % 4)].id,
      dueAt: i % 9 === 8 ? null : daysFromNow(((i * 7) % 66) - 8),
      createdAt: daysFromNow(-60 + i),
      lastActivityAt: daysFromNow(-((i * 3) % 20)),
      values: valuesFor(analyse.id, i),
    };
  });
}

const BY_ID = new Map(initialDossiers().map((d) => [d.id, d]));

/** Nom d'un dossier simulé, pour les autres jeux de données (notifications, activité). */
export const mockDossierName = (id: string): string => BY_ID.get(id)?.name ?? id;
