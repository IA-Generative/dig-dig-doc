import { computed, reactive } from "vue";

import { apiFetch } from "@/utils/api";
import type {
  Agent,
  AgentTool,
  Analyse,
  AnalyseSummary,
  EntityDefinition,
  LabelDefinition,
  Version,
} from "@/types/analyse";

function mapVersion<TApi, T>(v: { id: string; content: TApi; created_at: string }, mapContent: (c: TApi) => T): Version<T> {
  return { id: v.id, content: mapContent(v.content), createdAt: v.created_at };
}

const identity = <T,>(value: T) => value;

function mapLabel(api: { id: string; name: string; definition: string }): LabelDefinition {
  return { id: api.id, name: api.name, definition: api.definition };
}

function mapEntity(api: { id: string; name: string; definition: string; type: EntityDefinition["type"] }): EntityDefinition {
  return { id: api.id, name: api.name, definition: api.definition, type: api.type };
}

function mapAgent(api: any): Agent {
  return {
    id: api.id,
    name: api.name,
    prompt: api.prompt,
    promptVersions: api.prompt_versions.map((v: any) => mapVersion(v, identity<string>)),
    tools: api.tools,
    toolsVersions: api.tools_versions.map((v: any) => mapVersion(v, identity<AgentTool[]>)),
    output: api.output,
    outputVersions: api.output_versions.map((v: any) => mapVersion(v, identity<boolean>)),
  };
}

function mapAnalyse(api: any): Analyse {
  return {
    id: api.id,
    name: api.name,
    description: api.description,
    createdAt: api.created_at,
    classification: {
      prompt: api.classification.prompt,
      promptVersions: api.classification.prompt_versions.map((v: any) => mapVersion(v, identity<string>)),
      labels: api.classification.labels.map(mapLabel),
      labelsVersions: api.classification.labels_versions.map((v: any) =>
        mapVersion(v, (content: any[]) => content.map(mapLabel)),
      ),
    },
    extraction: {
      prompt: api.extraction.prompt,
      promptVersions: api.extraction.prompt_versions.map((v: any) => mapVersion(v, identity<string>)),
      entities: api.extraction.entities.map(mapEntity),
      entitiesVersions: api.extraction.entities_versions.map((v: any) =>
        mapVersion(v, (content: any[]) => content.map(mapEntity)),
      ),
    },
    agents: api.agents.map(mapAgent),
  };
}

function mapSummary(api: any): AnalyseSummary {
  return { id: api.id, name: api.name, description: api.description, createdAt: api.created_at, agentCount: api.agent_count };
}

// Store partagé par toute l'application : `summaries` alimente les listes
// (GET /analyses, léger), `cache` les analyses complètes une fois ouvertes
// (GET /analyses/:id ou réponse d'une mutation).
const summaries = reactive<AnalyseSummary[]>([]);
const cache = reactive<Record<string, Analyse>>({});

async function fetchList() {
  const data = await apiFetch<any[]>("/api/analyses");
  summaries.splice(0, summaries.length, ...data.map(mapSummary));
}

fetchList();

function replaceAgent(analyseId: string, agent: Agent) {
  const analyse = cache[analyseId];
  if (!analyse) return;
  const index = analyse.agents.findIndex((a) => a.id === agent.id);
  if (index === -1) analyse.agents.push(agent);
  else analyse.agents[index] = agent;
}

export function useAnalyses() {
  const list = computed(() => summaries);

  const getById = (id: string) => cache[id];

  const fetchAnalyse = async (id: string) => {
    const data = await apiFetch<any>(`/api/analyses/${id}`);
    cache[id] = mapAnalyse(data);
    return cache[id];
  };

  const create = async (name: string, description: string) => {
    const data = await apiFetch<any>("/api/analyses", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    });
    const analyse = mapAnalyse(data);
    cache[analyse.id] = analyse;
    summaries.unshift({ id: analyse.id, name: analyse.name, description: analyse.description, createdAt: analyse.createdAt, agentCount: 0 });
    return analyse;
  };

  // --- Classification ---

  const updateClassificationPrompt = async (analyseId: string, prompt: string) => {
    const data = await apiFetch<any>(`/api/analyses/${analyseId}/classification/prompt`, {
      method: "PUT",
      body: JSON.stringify({ prompt }),
    });
    cache[analyseId] = mapAnalyse(data);
  };

  const restoreClassificationPromptVersion = async (analyseId: string, versionId: string) => {
    const data = await apiFetch<any>(`/api/analyses/${analyseId}/classification/prompt/restore/${versionId}`, {
      method: "POST",
    });
    cache[analyseId] = mapAnalyse(data);
  };

  const updateClassificationLabels = async (analyseId: string, labels: LabelDefinition[]) => {
    const data = await apiFetch<any>(`/api/analyses/${analyseId}/classification/labels`, {
      method: "PUT",
      body: JSON.stringify({ labels: labels.map(({ name, definition }) => ({ name, definition })) }),
    });
    cache[analyseId] = mapAnalyse(data);
  };

  const restoreClassificationLabelsVersion = async (analyseId: string, versionId: string) => {
    const data = await apiFetch<any>(`/api/analyses/${analyseId}/classification/labels/restore/${versionId}`, {
      method: "POST",
    });
    cache[analyseId] = mapAnalyse(data);
  };

  // --- Extraction ---

  const updateExtractionPrompt = async (analyseId: string, prompt: string) => {
    const data = await apiFetch<any>(`/api/analyses/${analyseId}/extraction/prompt`, {
      method: "PUT",
      body: JSON.stringify({ prompt }),
    });
    cache[analyseId] = mapAnalyse(data);
  };

  const restoreExtractionPromptVersion = async (analyseId: string, versionId: string) => {
    const data = await apiFetch<any>(`/api/analyses/${analyseId}/extraction/prompt/restore/${versionId}`, {
      method: "POST",
    });
    cache[analyseId] = mapAnalyse(data);
  };

  const updateExtractionEntities = async (analyseId: string, entities: EntityDefinition[]) => {
    const data = await apiFetch<any>(`/api/analyses/${analyseId}/extraction/entities`, {
      method: "PUT",
      body: JSON.stringify({ entities: entities.map(({ name, definition, type }) => ({ name, definition, type })) }),
    });
    cache[analyseId] = mapAnalyse(data);
  };

  const restoreExtractionEntitiesVersion = async (analyseId: string, versionId: string) => {
    const data = await apiFetch<any>(`/api/analyses/${analyseId}/extraction/entities/restore/${versionId}`, {
      method: "POST",
    });
    cache[analyseId] = mapAnalyse(data);
  };

  // --- Agents (créés librement par l'utilisateur pour un but métier) ---

  const addAgent = async (analyseId: string, name: string, prompt: string, tools: AgentTool[] = [], output = true) => {
    const data = await apiFetch<any>(`/api/analyses/${analyseId}/agents`, {
      method: "POST",
      body: JSON.stringify({ name, prompt, tools, output }),
    });
    const agent = mapAgent(data);
    replaceAgent(analyseId, agent);
    const summary = summaries.find((s) => s.id === analyseId);
    if (summary) summary.agentCount += 1;
    return agent;
  };

  const updateAgentPrompt = async (analyseId: string, agentId: string, newPrompt: string) => {
    const data = await apiFetch<any>(`/api/analyses/${analyseId}/agents/${agentId}/prompt`, {
      method: "PUT",
      body: JSON.stringify({ prompt: newPrompt }),
    });
    replaceAgent(analyseId, mapAgent(data));
  };

  const restoreAgentPromptVersion = async (analyseId: string, agentId: string, versionId: string) => {
    const data = await apiFetch<any>(`/api/analyses/${analyseId}/agents/${agentId}/prompt/restore/${versionId}`, {
      method: "POST",
    });
    replaceAgent(analyseId, mapAgent(data));
  };

  const updateAgentTools = async (analyseId: string, agentId: string, tools: AgentTool[]) => {
    const data = await apiFetch<any>(`/api/analyses/${analyseId}/agents/${agentId}/tools`, {
      method: "PUT",
      body: JSON.stringify({ tools }),
    });
    replaceAgent(analyseId, mapAgent(data));
  };

  const restoreAgentToolsVersion = async (analyseId: string, agentId: string, versionId: string) => {
    const data = await apiFetch<any>(`/api/analyses/${analyseId}/agents/${agentId}/tools/restore/${versionId}`, {
      method: "POST",
    });
    replaceAgent(analyseId, mapAgent(data));
  };

  const updateAgentOutput = async (analyseId: string, agentId: string, output: boolean) => {
    const data = await apiFetch<any>(`/api/analyses/${analyseId}/agents/${agentId}/output`, {
      method: "PUT",
      body: JSON.stringify({ output }),
    });
    replaceAgent(analyseId, mapAgent(data));
  };

  const restoreAgentOutputVersion = async (analyseId: string, agentId: string, versionId: string) => {
    const data = await apiFetch<any>(`/api/analyses/${analyseId}/agents/${agentId}/output/restore/${versionId}`, {
      method: "POST",
    });
    replaceAgent(analyseId, mapAgent(data));
  };

  return {
    list,
    getById,
    fetchAnalyse,
    fetchList,
    create,
    updateClassificationPrompt,
    restoreClassificationPromptVersion,
    updateClassificationLabels,
    restoreClassificationLabelsVersion,
    updateExtractionPrompt,
    restoreExtractionPromptVersion,
    updateExtractionEntities,
    restoreExtractionEntitiesVersion,
    addAgent,
    updateAgentPrompt,
    restoreAgentPromptVersion,
    updateAgentTools,
    restoreAgentToolsVersion,
    updateAgentOutput,
    restoreAgentOutputVersion,
  };
}
