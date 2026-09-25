import { computed, reactive, ref } from "vue";

import { API_BASE_URL, apiFetch } from "@/utils/api";
import type { Dossier, DossierDocument, ExecutionStep, Summary } from "@/types/dossier";

function mapSummary(api: any): Summary | undefined {
  if (!api) return undefined;
  return {
    id: api.id,
    content: api.content,
    model: api.model ?? undefined,
    createdAt: api.created_at,
  };
}

function mapDocument(api: any): DossierDocument {
  return {
    id: api.id,
    name: api.name,
    size: api.size,
    s3Key: api.s3_key,
    mimetype: api.mimetype,
    label: api.label ?? undefined,
    textExtractionStatus: api.text_extraction_status,
    textExtractionError: api.text_extraction_error ?? undefined,
    fileHash: api.file_hash ?? undefined,
    summaryStatus: api.summary_status,
    summaryError: api.summary_error ?? undefined,
    summary: mapSummary(api.summary),
  };
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
    summaryStatus: api.summary_status,
    summaryError: api.summary_error ?? undefined,
    summary: mapSummary(api.summary),
  };
}

// Store partagé par toute l'application : `dossiers` contient la page
// actuellement chargée (pagination côté serveur, voir fetchList) plus tout
// dossier ouvert individuellement (fetchDossier) qui ne s'y trouvait pas.
const dossiers = reactive<Dossier[]>([]);
const total = ref(0);
const pageCount = ref(1);
const currentPage = ref(1);
const pageSize = ref(10);

async function fetchList(page = currentPage.value, size = pageSize.value) {
  const data = await apiFetch<{ items: any[]; total: number; page: number; page_size: number; pages: number }>(
    `/api/dossiers?page=${page}&page_size=${size}`,
  );
  dossiers.splice(0, dossiers.length, ...data.items.map(mapDossier));
  total.value = data.total;
  pageCount.value = data.pages;
  currentPage.value = data.page;
  pageSize.value = data.page_size;
}

function upsert(dossier: Dossier) {
  const index = dossiers.findIndex((d) => d.id === dossier.id);
  if (index === -1) dossiers.unshift(dossier);
  else dossiers[index] = dossier;
}

export function useDossiers() {
  const list = computed(() => dossiers);

  const getById = (id: string) => dossiers.find((d) => d.id === id);

  // Pour ouvrir un dossier qui n'est pas forcément dans la page actuellement
  // chargée (navigation directe vers /dossiers/:id).
  const fetchDossier = async (id: string) => {
    const data = await apiFetch<any>(`/api/dossiers/${id}`);
    const dossier = mapDossier(data);
    upsert(dossier);
    return dossier;
  };

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

  // Régénère le résumé d'un document (issue #52) : le backend dispatche
  // une tâche Celery sur la file agent_execution.
  const regenerateDocumentSummary = async (dossierId: string, documentId: string) => {
    await apiFetch<any>(`/api/dossiers/${dossierId}/documents/${documentId}/summary`, { method: "POST" });
    const data = await apiFetch<any>(`/api/dossiers/${dossierId}`);
    upsert(mapDossier(data));
  };

  // Régénère le résumé global du dossier (issue #52).
  const regenerateDossierSummary = async (dossierId: string) => {
    await apiFetch<any>(`/api/dossiers/${dossierId}/summary`, { method: "POST" });
    const data = await apiFetch<any>(`/api/dossiers/${dossierId}`);
    upsert(mapDossier(data));
  };

  const stop = async (dossierId: string) => {
    const data = await apiFetch<any>(`/api/dossiers/${dossierId}/stop`, { method: "POST" });
    upsert(mapDossier(data));
  };

  // SSE : le navigateur s'abonne à /dossiers/{id}/stream, qui émet un
  // `execution-update` à chaque changement d'état (statut du dossier, statut
  // d'extraction de texte d'un document...) puis un `done` quand il n'y a
  // plus de travail actif. Le callback reçoit le dossier sérialisé (même
  // forme que GET /dossiers/{id}) et met à jour le store via upsert.
  const streamDossier = (dossierId: string, onUpdate: (dossier: Dossier) => void): (() => void) => {
    const url = `${API_BASE_URL}/api/dossiers/${dossierId}/stream`;
    const eventSource = new EventSource(url, { withCredentials: true });

    eventSource.addEventListener("execution-update", (event) => {
      const dossier = mapDossier(JSON.parse(event.data));
      upsert(dossier);
      onUpdate(dossier);
    });
    eventSource.addEventListener("done", () => {
      eventSource.close();
    });
    eventSource.addEventListener("error", () => {
      // Le navigateur reconnecte automatiquement en cas d'erreur réseau ;
      // on ferme pour éviter une boucle infinie (le serveur a déjà émis
      // `done` ou la session a expiré).
      eventSource.close();
    });

    return () => eventSource.close();
  };

  return {
    list,
    total,
    pageCount,
    currentPage,
    pageSize,
    getById,
    fetchDossier,
    fetchList,
    create,
    addDocuments,
    setDocumentLabel,
    launch,
    stop,
    regenerateDocumentSummary,
    regenerateDossierSummary,
    streamDossier,
  };
}
