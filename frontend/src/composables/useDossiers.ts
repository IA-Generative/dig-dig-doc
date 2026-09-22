import { computed, reactive } from "vue";

import { useAnalyses } from "@/composables/useAnalyses";
import type { Agent, Analyse, EntityType } from "@/types/analyse";
import type { Dossier, DossierDocument, ExecutionStep, ExecutionStepKind } from "@/types/dossier";

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
        kind: "classification",
        label: "Classification documentaire",
        status: "terminé",
        startedAt: "2026-04-03T08:13:00Z",
        endedAt: "2026-04-03T08:13:20Z",
        output: "CNI (confiance : 96%)",
      },
      {
        id: "step-2",
        kind: "extraction",
        label: "Extraction d'entités nommées",
        status: "terminé",
        startedAt: "2026-04-03T08:13:20Z",
        endedAt: "2026-04-03T08:13:42Z",
        output: "Aucune entité configurée pour cette analyse.",
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

function mockClassificationOutput(analyse: Analyse): string {
  if (analyse.classification.labels.length === 0) return "Aucun label configuré pour cette analyse.";
  const label = analyse.classification.labels[Math.floor(Math.random() * analyse.classification.labels.length)];
  const confidence = 85 + Math.floor(Math.random() * 14);
  return `${label.name} (confiance : ${confidence}%)`;
}

const MOCK_VALUES_BY_TYPE: Record<EntityType, string[]> = {
  texte: ["Dupont", "12 rue de la République, 75011 Paris"],
  date: ["15/03/1985", "02/09/2026"],
  nombre: ["42", "1 284"],
  booléen: ["Oui", "Non"],
  identifiant: ["FR-284910-B", "2026-0417-CNI"],
};

function mockValueForType(type: EntityType): string {
  const values = MOCK_VALUES_BY_TYPE[type];
  return values[Math.floor(Math.random() * values.length)];
}

function mockExtractionOutput(analyse: Analyse): string {
  if (analyse.extraction.entities.length === 0) return "Aucune entité configurée pour cette analyse.";
  return analyse.extraction.entities.map((entity) => `${entity.name} : ${mockValueForType(entity.type)}`).join(" · ");
}

function mockAgentOutput(agent: Agent): string {
  return `Résultat généré par « ${agent.name} » à partir des documents du dossier.`;
}

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
    const steps: { kind: ExecutionStepKind; label: string; agent?: Agent }[] = [
      { kind: "classification", label: "Classification documentaire" },
      { kind: "extraction", label: "Extraction d'entités nommées" },
      ...analyse.agents.map((agent) => ({ kind: "agent" as const, label: agent.name, agent })),
    ];

    dossier.status = "en_cours";
    dossier.analyseVersion = getAnalyseVersion(dossier.analyseId);
    dossier.startedAt = now;
    dossier.endedAt = undefined;
    dossier.executionSteps = steps.map<ExecutionStep>((step, index) => ({
      id: `step-${Date.now()}-${index}`,
      kind: step.kind,
      label: step.label,
      status: "en_cours",
      startedAt: now,
    }));

    setTimeout(() => {
      if (dossier.status !== "en_cours") return; // arrêté entre-temps
      const endedAt = new Date().toISOString();
      dossier.status = "terminé";
      dossier.endedAt = endedAt;
      dossier.executionSteps.forEach((step, index) => {
        step.status = "terminé";
        step.endedAt = endedAt;
        const source = steps[index];
        if (step.kind === "classification") step.output = mockClassificationOutput(analyse);
        else if (step.kind === "extraction") step.output = mockExtractionOutput(analyse);
        else if (step.kind === "agent" && source.agent?.output) step.output = mockAgentOutput(source.agent);
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
