import { computed, reactive } from "vue";

import { apiFetch } from "@/utils/api";
import type { Dossier, DossierDocument, ExecutionStep } from "@/types/dossier";

function mapDocument(api: any): DossierDocument {
  return { id: api.id, name: api.name, size: api.size, s3Key: api.s3_key, mimetype: api.mimetype, label: api.label ?? undefined };
}

function mapStep(api: any): ExecutionStep {
  return {
    id: api.id,
    kind: api.kind,
    label: api.label,
    status: api.status,
    startedAt: api.started_at,
    endedAt: api.ended_at ?? undefined,
    output: api.output ?? undefined,
  };
}

function mapDossier(api: any): Dossier {
  return {
    id: api.id,
    name: api.name,
    analyseId: api.analyse_id,
    analyseVersion: api.analyse_version,
    createdAt: api.created_at,
    status: api.status,
    startedAt: api.started_at ?? undefined,
    endedAt: api.ended_at ?? undefined,
    executionSteps: api.execution_steps.map(mapStep),
    documents: api.documents.map(mapDocument),
  };
}

// Store partagé par toute l'application, alimenté depuis la vraie API BFF.
const dossiers = reactive<Dossier[]>([]);

async function fetchList() {
  const data = await apiFetch<any[]>("/api/dossiers");
  dossiers.splice(0, dossiers.length, ...data.map(mapDossier));
}

fetchList();

function upsert(dossier: Dossier) {
  const index = dossiers.findIndex((d) => d.id === dossier.id);
  if (index === -1) dossiers.unshift(dossier);
  else dossiers[index] = dossier;
}

export function useDossiers() {
  const list = computed(() => dossiers);

  const getById = (id: string) => dossiers.find((d) => d.id === id);

  const create = async (name: string, analyseId: string) => {
    const data = await apiFetch<any>("/api/dossiers", {
      method: "POST",
      body: JSON.stringify({ name, analyse_id: analyseId }),
    });
    const dossier = mapDossier(data);
    upsert(dossier);
    return dossier;
  };

  const addDocuments = async (dossierId: string, files: FileList | File[]) => {
    const formData = new FormData();
    for (const file of Array.from(files)) formData.append("files", file);
    const data = await apiFetch<any>(`/api/dossiers/${dossierId}/documents`, {
      method: "POST",
      body: formData,
    });
    upsert(mapDossier(data));
  };

  const setDocumentLabel = async (dossierId: string, documentId: string, label: string | null) => {
    await apiFetch<any>(`/api/dossiers/${dossierId}/documents/${documentId}/label`, {
      method: "PUT",
      body: JSON.stringify({ label }),
    });
    const data = await apiFetch<any>(`/api/dossiers/${dossierId}`);
    upsert(mapDossier(data));
  };

  const launch = async (dossierId: string) => {
    const data = await apiFetch<any>(`/api/dossiers/${dossierId}/launch`, { method: "POST" });
    upsert(mapDossier(data));
  };

  const stop = async (dossierId: string) => {
    const data = await apiFetch<any>(`/api/dossiers/${dossierId}/stop`, { method: "POST" });
    upsert(mapDossier(data));
  };

  return { list, getById, fetchList, create, addDocuments, setDocumentLabel, launch, stop };
}
