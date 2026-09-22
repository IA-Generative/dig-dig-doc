import { computed, reactive } from "vue";

import type { Agent, AgentTool, Analyse, EntityDefinition, LabelDefinition } from "@/types/analyse";

function emptyClassification() {
  return { prompt: "", promptVersions: [], labels: [], labelsVersions: [] };
}

function emptyExtraction() {
  return { prompt: "", promptVersions: [], entities: [], entitiesVersions: [] };
}

// In-memory mock store until the BFF exposes a real /analyses API (issue #2).
// Shape and operations (create, addAgent, update*/restore* with versioning)
// are meant to map 1:1 onto future REST calls.
const analyses = reactive<Analyse[]>([
  {
    id: "cni-2026-04",
    name: "Contrôle CNI - lot avril",
    description: "Vérification des cartes nationales d'identité déposées en avril.",
    createdAt: "2026-04-02T09:00:00Z",
    classification: {
      prompt: "Identifie la nature du document (CNI, passeport, justificatif de domicile, avis d'imposition).",
      promptVersions: [],
      labels: [],
      labelsVersions: [],
    },
    extraction: emptyExtraction(),
    agents: [],
  },
  {
    id: "avis-imposition-2026",
    name: "Avis d'imposition 2026",
    description: "Extraction des données fiscales des avis d'imposition déposés.",
    createdAt: "2026-03-18T14:30:00Z",
    classification: emptyClassification(),
    extraction: emptyExtraction(),
    agents: [],
  },
  {
    id: "coherence-domicile",
    name: "Cohérence justificatif de domicile",
    description: "Recoupement entre justificatif de domicile et formulaire usager.",
    createdAt: "2026-02-27T11:15:00Z",
    classification: emptyClassification(),
    extraction: emptyExtraction(),
    agents: [],
  },
]);

let nextAnalyseId = analyses.length + 1;

export function useAnalyses() {
  const list = computed(() => analyses);

  const getById = (id: string) => analyses.find((a) => a.id === id);

  const create = (name: string, description: string) => {
    const analyse: Analyse = {
      id: `analyse-${nextAnalyseId++}`,
      name,
      description,
      createdAt: new Date().toISOString(),
      classification: emptyClassification(),
      extraction: emptyExtraction(),
      agents: [],
    };
    analyses.unshift(analyse);
    return analyse;
  };

  // --- Classification ---

  const updateClassificationPrompt = (analyseId: string, prompt: string) => {
    const analyse = getById(analyseId);
    if (!analyse || analyse.classification.prompt === prompt) return;
    analyse.classification.promptVersions.unshift({
      id: `v-${Date.now()}`,
      content: analyse.classification.prompt,
      createdAt: new Date().toISOString(),
    });
    analyse.classification.prompt = prompt;
  };

  const restoreClassificationPromptVersion = (analyseId: string, versionId: string) => {
    const analyse = getById(analyseId);
    const version = analyse?.classification.promptVersions.find((v) => v.id === versionId);
    if (!analyse || !version) return;
    updateClassificationPrompt(analyseId, version.content);
  };

  const updateClassificationLabels = (analyseId: string, labels: LabelDefinition[]) => {
    const analyse = getById(analyseId);
    if (!analyse || JSON.stringify(analyse.classification.labels) === JSON.stringify(labels)) return;
    analyse.classification.labelsVersions.unshift({
      id: `v-${Date.now()}`,
      content: analyse.classification.labels,
      createdAt: new Date().toISOString(),
    });
    analyse.classification.labels = labels;
  };

  const restoreClassificationLabelsVersion = (analyseId: string, versionId: string) => {
    const analyse = getById(analyseId);
    const version = analyse?.classification.labelsVersions.find((v) => v.id === versionId);
    if (!analyse || !version) return;
    updateClassificationLabels(analyseId, version.content);
  };

  // --- Extraction ---

  const updateExtractionPrompt = (analyseId: string, prompt: string) => {
    const analyse = getById(analyseId);
    if (!analyse || analyse.extraction.prompt === prompt) return;
    analyse.extraction.promptVersions.unshift({
      id: `v-${Date.now()}`,
      content: analyse.extraction.prompt,
      createdAt: new Date().toISOString(),
    });
    analyse.extraction.prompt = prompt;
  };

  const restoreExtractionPromptVersion = (analyseId: string, versionId: string) => {
    const analyse = getById(analyseId);
    const version = analyse?.extraction.promptVersions.find((v) => v.id === versionId);
    if (!analyse || !version) return;
    updateExtractionPrompt(analyseId, version.content);
  };

  const updateExtractionEntities = (analyseId: string, entities: EntityDefinition[]) => {
    const analyse = getById(analyseId);
    if (!analyse || JSON.stringify(analyse.extraction.entities) === JSON.stringify(entities)) return;
    analyse.extraction.entitiesVersions.unshift({
      id: `v-${Date.now()}`,
      content: analyse.extraction.entities,
      createdAt: new Date().toISOString(),
    });
    analyse.extraction.entities = entities;
  };

  const restoreExtractionEntitiesVersion = (analyseId: string, versionId: string) => {
    const analyse = getById(analyseId);
    const version = analyse?.extraction.entitiesVersions.find((v) => v.id === versionId);
    if (!analyse || !version) return;
    updateExtractionEntities(analyseId, version.content);
  };

  // --- Agents (créés librement par l'utilisateur pour un but métier) ---

  const addAgent = (
    analyseId: string,
    name: string,
    prompt: string,
    tools: AgentTool[] = [],
    output = true,
  ) => {
    const analyse = getById(analyseId);
    if (!analyse) return;
    const agent: Agent = {
      id: `agent-${Date.now()}`,
      name,
      prompt,
      promptVersions: [],
      tools,
      toolsVersions: [],
      output,
      outputVersions: [],
    };
    analyse.agents.push(agent);
    return agent;
  };

  const getAgent = (analyseId: string, agentId: string) => getById(analyseId)?.agents.find((a) => a.id === agentId);

  const updateAgentPrompt = (analyseId: string, agentId: string, newPrompt: string) => {
    const agent = getAgent(analyseId, agentId);
    if (!agent || agent.prompt === newPrompt) return;
    agent.promptVersions.unshift({
      id: `v-${Date.now()}`,
      content: agent.prompt,
      createdAt: new Date().toISOString(),
    });
    agent.prompt = newPrompt;
  };

  const restoreAgentPromptVersion = (analyseId: string, agentId: string, versionId: string) => {
    const agent = getAgent(analyseId, agentId);
    const version = agent?.promptVersions.find((v) => v.id === versionId);
    if (!agent || !version) return;
    updateAgentPrompt(analyseId, agentId, version.content);
  };

  const updateAgentTools = (analyseId: string, agentId: string, tools: AgentTool[]) => {
    const agent = getAgent(analyseId, agentId);
    const sortTools = (t: AgentTool[]) => [...t].sort((a, b) => a.localeCompare(b));
    if (!agent || JSON.stringify(sortTools(agent.tools)) === JSON.stringify(sortTools(tools))) return;
    agent.toolsVersions.unshift({ id: `v-${Date.now()}`, content: agent.tools, createdAt: new Date().toISOString() });
    agent.tools = tools;
  };

  const restoreAgentToolsVersion = (analyseId: string, agentId: string, versionId: string) => {
    const agent = getAgent(analyseId, agentId);
    const version = agent?.toolsVersions.find((v) => v.id === versionId);
    if (!agent || !version) return;
    updateAgentTools(analyseId, agentId, version.content);
  };

  const updateAgentOutput = (analyseId: string, agentId: string, output: boolean) => {
    const agent = getAgent(analyseId, agentId);
    if (!agent || agent.output === output) return;
    agent.outputVersions.unshift({ id: `v-${Date.now()}`, content: agent.output, createdAt: new Date().toISOString() });
    agent.output = output;
  };

  const restoreAgentOutputVersion = (analyseId: string, agentId: string, versionId: string) => {
    const agent = getAgent(analyseId, agentId);
    const version = agent?.outputVersions.find((v) => v.id === versionId);
    if (!agent || !version) return;
    updateAgentOutput(analyseId, agentId, version.content);
  };

  // La version d'une analyse est dérivée du nombre total de modifications
  // enregistrées (chaque entrée d'historique, prompt/labels/entités/agents
  // confondus) : v1 au départ, +1 à chaque changement sauvegardé.
  const getAnalyseVersion = (analyseId: string): string => {
    const analyse = getById(analyseId);
    if (!analyse) return "v1";
    const editCount =
      analyse.classification.promptVersions.length +
      analyse.classification.labelsVersions.length +
      analyse.extraction.promptVersions.length +
      analyse.extraction.entitiesVersions.length +
      analyse.agents.reduce((sum, agent) => sum + agent.promptVersions.length, 0);
    return `v${editCount + 1}`;
  };

  return {
    list,
    getById,
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
    getAnalyseVersion,
  };
}
