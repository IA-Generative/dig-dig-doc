import { ref } from "vue";

import type { DashboardData, DashboardUrgency } from "@/types/dashboard";
import type { SlotDraft } from "@/types/schedule";

// MOCK (issue #174, partie UI) : à remplacer par un appel API une fois les
// statuts (#168), la péremption (#172) et les affectations (#173) livrés.
// Pour valider les états de l'interface, ajouter `?mock=` à l'URL du
// tableau de bord : `empty` (états vides), `error` (erreur), `loading`
// (chargement sans fin), `nounassigned` (sans droit « non affectés »).

const hoursAgo = (h: number) => new Date(Date.now() - h * 3_600_000).toISOString();
const daysFromNow = (d: number) => new Date(Date.now() + d * 86_400_000).toISOString();

const MOCK_ANALYSES = ["Instruction subventions", "Urbanisme", "Commande publique", "Aides logement", "Contentieux"];
const MOCK_STATUSES = ["À instruire", "En instruction", "Pièces manquantes", "À valider"];
const MOCK_SUBJECTS = [
  "Subvention association Les Mouettes",
  "Permis de construire 2026-0412",
  "Marché public fournitures bureau",
  "Recours gracieux n°88",
  "Aide rénovation énergétique",
  "Déclaration préalable de travaux",
  "Convention de partenariat culturelle",
];

/** Quelques dossiers déjà planifiés aujourd'hui, pour valider l'affichage des horaires. */
function mockSlot(i: number): Pick<DashboardUrgency, "plannedStart" | "plannedEnd" | "recurrence" | "reminders"> {
  const slots: Record<number, [number, number]> = { 2: [9, 10.5], 5: [11, 12], 7: [14, 16] };
  const slot = slots[i];
  if (!slot) return {};
  const at = (h: number) => {
    const d = new Date();
    d.setHours(Math.floor(h), (h % 1) * 60, 0, 0);
    return d.toISOString();
  };
  return {
    plannedStart: at(slot[0]),
    plannedEnd: at(slot[1]),
    // Démo : le premier créneau se répète chaque jour ouvré, avec un rappel.
    ...(i === 2
      ? { recurrence: { unit: "week" as const, interval: 1, weekdays: [0, 1, 2, 3, 4], end: { type: "never" as const } }, reminders: [15] }
      : { reminders: [] }),
  };
}

/** Jeu de données volontairement large (28) pour éprouver pagination, filtres et recherche. */
function mockUrgencies(): DashboardUrgency[] {
  return Array.from({ length: 28 }, (_, i) => {
    const offset = Math.round((i - 6) * 0.6); // de -4 j (retard) à +12 j
    return {
      dossierId: `mock-u${i}`,
      dossierName: `${MOCK_SUBJECTS[i % MOCK_SUBJECTS.length]} #${100 + i}`,
      analyseName: MOCK_ANALYSES[i % MOCK_ANALYSES.length],
      statusLabel: MOCK_STATUSES[i % MOCK_STATUSES.length],
      dueAt: daysFromNow(offset),
      level: offset < 0 ? "overdue" : "soon",
      ...mockSlot(i),
    };
  });
}

function mockData(): DashboardData {
  return {
    stats: {
      totalDossiers: 52,
      closedDossiers: 28,
      completedThisWeek: 9,
      completedPrevWeek: 6,
      weeklyClosed: [5, 8, 6, 9],
      avgProcessingDays: 2.4,
      onTimeRate: 0.87,
    },
    urgencies: mockUrgencies(),
    statusCounts: [
      { statusId: "a_instruire", label: "À instruire", count: 7 },
      { statusId: "en_instruction", label: "En instruction", count: 12 },
      { statusId: "pieces_manquantes", label: "Pièces manquantes", count: 3 },
      { statusId: "a_valider", label: "À valider", count: 2 },
    ],
    unassigned: [
      {
        dossierId: "mock-4",
        dossierName: "Demande d'aide à la rénovation énergétique",
        analyseName: "Aides logement",
        createdAt: hoursAgo(5),
      },
      {
        dossierId: "mock-5",
        dossierName: "Recours gracieux n°88",
        analyseName: "Contentieux",
        createdAt: hoursAgo(30),
      },
    ],
    activity: [
      {
        id: "act-1",
        kind: "analysis_done",
        dossierId: "mock-2",
        dossierName: "Permis de construire 2026-0412",
        message: "Analyse terminée",
        at: hoursAgo(1),
      },
      {
        id: "act-2",
        kind: "status_changed",
        dossierId: "mock-1",
        dossierName: "Subvention association Les Mouettes",
        message: "Statut passé de « À instruire » à « En instruction » par Camille D.",
        at: hoursAgo(4),
      },
      {
        id: "act-3",
        kind: "document_added",
        dossierId: "mock-3",
        dossierName: "Marché public fournitures bureau",
        message: "Document ajouté : devis-fournisseur.pdf",
        at: hoursAgo(22),
      },
      {
        id: "act-4",
        kind: "analysis_failed",
        dossierId: "mock-5",
        dossierName: "Recours gracieux n°88",
        message: "L'analyse a échoué",
        at: hoursAgo(47),
      },
    ],
  };
}

function mockScenario(): string | null {
  return new URLSearchParams(window.location.search).get("mock");
}

export function useDashboard() {
  const data = ref<DashboardData | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchDashboard() {
    loading.value = true;
    error.value = null;
    const scenario = mockScenario();
    // Latence simulée pour pouvoir juger l'état de chargement.
    await new Promise((resolve) => setTimeout(resolve, 400));
    if (scenario === "loading") return;
    if (scenario === "error") {
      error.value = "Impossible de charger le tableau de bord.";
    } else if (scenario === "empty") {
      data.value = {
        stats: {
          totalDossiers: 0,
          closedDossiers: 0,
          completedThisWeek: 0,
          completedPrevWeek: 0,
          weeklyClosed: [0, 0, 0, 0],
          avgProcessingDays: 0,
          onTimeRate: 0,
        },
        urgencies: [],
        statusCounts: [],
        unassigned: [],
        activity: [],
      };
    } else {
      const mock = mockData();
      if (scenario === "nounassigned") mock.unassigned = null;
      data.value = mock;
    }
    loading.value = false;
  }

  /** Planifie (ou retire, avec `null`) le créneau de traitement d'un dossier. */
  function setSchedule(dossierId: string, slot: SlotDraft | null) {
    const target = data.value?.urgencies.find((u) => u.dossierId === dossierId);
    if (!target) return;
    target.plannedStart = slot?.start;
    target.plannedEnd = slot?.end;
    target.recurrence = slot?.recurrence;
    target.reminders = slot?.reminders;
  }

  return { data, loading, error, fetchDashboard, setSchedule };
}
