import { ref } from "vue";

import { useDossierAccess } from "@/composables/useDossierAccess";
import { useTracking } from "@/composables/useTracking";
import { ME, STATUSES } from "@/mocks/dossiers";
import type { DashboardActivity, DashboardData, DashboardUrgency } from "@/types/dashboard";
import type { SlotDraft } from "@/types/schedule";
import { dayOffset } from "@/utils/dates";

// MOCK (issue #174, partie UI) : à remplacer par un appel API une fois les
// statuts (#168), l'échéance (#172) et les affectations (#173) livrés.
// Pour valider les états de l'interface, ajouter `?mock=` à l'URL du
// tableau de bord : `empty` (états vides), `error` (erreur), `loading`
// (chargement sans fin), `nounassigned` (sans droit « non affectés »).

const hoursAgo = (h: number) => new Date(Date.now() - h * 3_600_000).toISOString();

/** Créneaux planifiés, conservés tant que la page n'est pas rechargée (ils survivent à la navigation). */
const slots = new Map<string, SlotDraft>();
let slotsSeeded = false;

function demoSlot(position: number): SlotDraft | null {
  const hours: Record<number, [number, number]> = { 2: [9, 10.5], 5: [11, 12], 7: [14, 16] };
  const range = hours[position];
  if (!range) return null;
  const at = (h: number) => {
    const d = new Date();
    d.setHours(Math.floor(h), (h % 1) * 60, 0, 0);
    return d.toISOString();
  };
  return {
    start: at(range[0]),
    end: at(range[1]),
    // Démo : le premier créneau se répète chaque jour ouvré, avec un rappel.
    recurrence: position === 2 ? { unit: "week", interval: 1, weekdays: [0, 1, 2, 3, 4], end: { type: "never" } } : undefined,
    reminders: position === 2 ? [15] : [],
  };
}

const URGENCY_HORIZON_DAYS = 14;

/**
 * Construit le tableau de bord à partir du jeu de données commun (@/mocks/dossiers) :
 * mes dossiers affectés, ceux sans responsable, les statuts. Seuls les dossiers
 * accessibles (#177) sont pris en compte. Ainsi les affectations faites dans le
 * tableau de suivi se retrouvent ici.
 */
function mockData(): DashboardData {
  const { rows, analyseName } = useTracking();
  const { canSee } = useDossierAccess();
  const isFinal = (statusId: string) => STATUSES.find((s) => s.id === statusId)?.final ?? false;
  const statusLabel = (statusId: string) => STATUSES.find((s) => s.id === statusId)?.label ?? statusId;

  const visible = rows.value.filter((r) => canSee(r.id));
  const mine = visible.filter((r) => r.assigneeId === ME);
  const open = mine.filter((r) => !isFinal(r.statusId));

  const urgentRows = open
    .filter((r) => r.dueAt && dayOffset(r.dueAt) <= URGENCY_HORIZON_DAYS)
    .sort((a, b) => Date.parse(a.dueAt!) - Date.parse(b.dueAt!));

  if (!slotsSeeded && urgentRows.length) {
    slotsSeeded = true;
    urgentRows.forEach((r, i) => {
      const slot = demoSlot(i);
      if (slot) slots.set(r.id, slot);
    });
  }

  const urgencies: DashboardUrgency[] = urgentRows.map((r) => {
    const slot = slots.get(r.id);
    return {
      dossierId: r.id,
      dossierName: r.name,
      analyseId: r.analyseId,
      analyseName: analyseName(r.analyseId),
      statusLabel: statusLabel(r.statusId),
      dueAt: r.dueAt!,
      level: dayOffset(r.dueAt!) < 0 ? "overdue" : "soon",
      plannedStart: slot?.start,
      plannedEnd: slot?.end,
      recurrence: slot?.recurrence,
      reminders: slot?.reminders,
    };
  });

  const statusCounts = STATUSES.filter((s) => !s.final)
    .map((s) => ({ statusId: s.id, label: s.label, count: open.filter((r) => r.statusId === s.id).length }))
    .filter((s) => s.count > 0);

  const unassigned = visible
    .filter((r) => r.assigneeId === null && !isFinal(r.statusId))
    .map((r) => ({
      dossierId: r.id,
      dossierName: r.name,
      analyseName: analyseName(r.analyseId),
      createdAt: r.createdAt,
    }));

  const messages: { kind: DashboardActivity["kind"]; text: string }[] = [
    { kind: "analysis_done", text: "Analyse terminée" },
    { kind: "status_changed", text: "Statut modifié par Camille D." },
    { kind: "document_added", text: "Document ajouté : devis-fournisseur.pdf" },
    { kind: "analysis_failed", text: "L'analyse a échoué" },
  ];
  const activity = mine.slice(0, messages.length).map((r, i) => ({
    id: `act-${i + 1}`,
    kind: messages[i].kind,
    dossierId: r.id,
    dossierName: r.name,
    message: messages[i].text,
    at: hoursAgo([1, 4, 22, 47][i]),
  }));

  return {
    stats: {
      totalDossiers: mine.length,
      closedDossiers: mine.length - open.length,
      completedThisWeek: 9,
      completedPrevWeek: 6,
      weeklyClosed: [5, 8, 6, 9],
      avgProcessingDays: 2.4,
      onTimeRate: 0.87,
    },
    urgencies,
    statusCounts,
    unassigned,
    activity,
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
    if (slot) slots.set(dossierId, slot);
    else slots.delete(dossierId);
    target.plannedStart = slot?.start;
    target.plannedEnd = slot?.end;
    target.recurrence = slot?.recurrence;
    target.reminders = slot?.reminders;
  }

  return { data, loading, error, fetchDashboard, setSchedule };
}
