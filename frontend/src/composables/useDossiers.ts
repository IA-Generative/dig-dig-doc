import { computed, reactive } from "vue";

import { useAnalyses } from "@/composables/useAnalyses";
import type { Dossier, DossierDocument, ExecutionStep } from "@/types/dossier";

// In-memory mock store until the BFF/worker exposes a real /dossiers API.
// A launch is simulated with a timeout instead of a real Celery run.
const EXECUTION_DURATION_MS = 3000;

const dossiers = reactive<Dossier[]>([
  {
    id: "dossier-2026-1042",
    name: "Dossier 2026-1042",
    analyseId: "cni-2026-04",
    analyseVersion: "v1",
    createdAt: "2026-04-03T08:12:00Z",
    status: "terminé",
    startedAt: "2026-04-03T08:13:00Z",
    endedAt: "2026-04-03T08:13:42Z",
    executionSteps: [
      {
        id: "step-1",
        label: "Classification documentaire",
        status: "terminé",
        startedAt: "2026-04-03T08:13:00Z",
        endedAt: "2026-04-03T08:13:20Z",
      },
      {
        id: "step-2",
        label: "Extraction d'entités nommées",
        status: "terminé",
        startedAt: "2026-04-03T08:13:20Z",
        endedAt: "2026-04-03T08:13:42Z",
      },
    ],
    documents: [{ id: "doc-1", name: "cni_recto.jpg", size: 482_000 }],
  },
  {
    id: "dossier-2026-1043",
    name: "Dossier 2026-1043",
    analyseId: "cni-2026-04",
    analyseVersion: "v1",
    createdAt: "2026-04-04T10:05:00Z",
    status: "en_attente",
    executionSteps: [],
    documents: [],
  },
]);

export function useDossiers() {
  const { getById: getAnalyseById, getAnalyseVersion } = useAnalyses();

  const list = computed(() => dossiers);

  const getById = (id: string) => dossiers.find((d) => d.id === id);

  const create = (name: string, analyseId: string, documents: DossierDocument[] = []) => {
    const dossier: Dossier = {
      id: `dossier-${Date.now()}`,
      name,
      analyseId,
      analyseVersion: getAnalyseVersion(analyseId),
      createdAt: new Date().toISOString(),
      status: "en_attente",
      executionSteps: [],
      documents,
    };
    dossiers.unshift(dossier);
    return dossier;
  };

  const addDocuments = (dossierId: string, files: FileList | File[]) => {
    const dossier = getById(dossierId);
    if (!dossier) return;
    dossier.documents.push(
      ...Array.from(files).map<DossierDocument>((file, index) => ({
        id: `doc-${Date.now()}-${index}`,
        name: file.name,
        size: file.size,
      })),
    );
  };

  const launch = (dossierId: string) => {
    const dossier = getById(dossierId);
    const analyse = dossier ? getAnalyseById(dossier.analyseId) : undefined;
    if (!dossier || !analyse || dossier.status === "en_cours") return;

    const now = new Date().toISOString();
    const stepLabels = [
      "Classification documentaire",
      "Extraction d'entités nommées",
      ...analyse.agents.map((agent) => agent.name),
    ];

    dossier.status = "en_cours";
    dossier.analyseVersion = getAnalyseVersion(dossier.analyseId);
    dossier.startedAt = now;
    dossier.endedAt = undefined;
    dossier.executionSteps = stepLabels.map<ExecutionStep>((label, index) => ({
      id: `step-${Date.now()}-${index}`,
      label,
      status: "en_cours",
      startedAt: now,
    }));

    setTimeout(() => {
      if (dossier.status !== "en_cours") return; // arrêté entre-temps
      const endedAt = new Date().toISOString();
      dossier.status = "terminé";
      dossier.endedAt = endedAt;
      dossier.executionSteps.forEach((step) => {
        step.status = "terminé";
        step.endedAt = endedAt;
      });
    }, EXECUTION_DURATION_MS);
  };

  const stop = (dossierId: string) => {
    const dossier = getById(dossierId);
    if (!dossier || dossier.status !== "en_cours") return;
    dossier.status = "arrêté";
    dossier.endedAt = new Date().toISOString();
  };

  return { list, getById, create, addDocuments, launch, stop };
}
