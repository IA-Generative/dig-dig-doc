import { computed, reactive } from "vue";

import type { Agent, AgentCapability, AgentTool, Analyse, EntityDefinition, LabelDefinition } from "@/types/analyse";

// In-memory mock store until the BFF exposes a real /analyses API (issue #2).
// Shape and operations (create, addAgent, updatePrompt with versioning) are
// meant to map 1:1 onto future REST calls.
const analyses = reactive<Analyse[]>([
  {
    id: "cni-2026-04",
    name: "Contrôle CNI - lot avril",
    description: "Vérification des cartes nationales d'identité déposées en avril.",
    createdAt: "2026-04-02T09:00:00Z",
    agents: [
      {
        id: "typage",
        name: "Typage documentaire",
        capability: "Classification documentaire",
        prompt: "Identifie la nature du document (CNI, passeport, justificatif de domicile, avis d'imposition).",
        promptVersions: [],
        tools: ["lecture_document"],
        labels: [],
        labelsVersions: [],
        entities: [],
        entitiesVersions: [],
      },
    ],
  },
  {
    id: "avis-imposition-2026",
    name: "Avis d'imposition 2026",
    description: "Extraction des données fiscales des avis d'imposition déposés.",
    createdAt: "2026-03-18T14:30:00Z",
    agents: [],
  },
  {
    id: "coherence-domicile",
    name: "Cohérence justificatif de domicile",
    description: "Recoupement entre justificatif de domicile et formulaire usager.",
    createdAt: "2026-02-27T11:15:00Z",
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
      agents: [],
    };
    analyses.unshift(analyse);
    return analyse;
  };

  const addAgent = (
    analyseId: string,
    name: string,
    capability: AgentCapability,
    prompt: string,
    tools: AgentTool[] = [],
  ) => {
    const analyse = getById(analyseId);
    if (!analyse) return;
    const agent: Agent = {
      id: `agent-${Date.now()}`,
      name,
      capability,
      prompt,
      promptVersions: [],
      tools,
      labels: [],
      labelsVersions: [],
      entities: [],
      entitiesVersions: [],
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
    if (!agent) return;
    agent.tools = tools;
  };

  const updateAgentLabels = (analyseId: string, agentId: string, labels: LabelDefinition[]) => {
    const agent = getAgent(analyseId, agentId);
    if (!agent || JSON.stringify(agent.labels) === JSON.stringify(labels)) return;
    agent.labelsVersions.unshift({
      id: `v-${Date.now()}`,
      content: agent.labels,
      createdAt: new Date().toISOString(),
    });
    agent.labels = labels;
  };

  const restoreAgentLabelsVersion = (analyseId: string, agentId: string, versionId: string) => {
    const agent = getAgent(analyseId, agentId);
    const version = agent?.labelsVersions.find((v) => v.id === versionId);
    if (!agent || !version) return;
    updateAgentLabels(analyseId, agentId, version.content);
  };

  const updateAgentEntities = (analyseId: string, agentId: string, entities: EntityDefinition[]) => {
    const agent = getAgent(analyseId, agentId);
    if (!agent || JSON.stringify(agent.entities) === JSON.stringify(entities)) return;
    agent.entitiesVersions.unshift({
      id: `v-${Date.now()}`,
      content: agent.entities,
      createdAt: new Date().toISOString(),
    });
    agent.entities = entities;
  };

  const restoreAgentEntitiesVersion = (analyseId: string, agentId: string, versionId: string) => {
    const agent = getAgent(analyseId, agentId);
    const version = agent?.entitiesVersions.find((v) => v.id === versionId);
    if (!agent || !version) return;
    updateAgentEntities(analyseId, agentId, version.content);
  };

  return {
    list,
    getById,
    create,
    addAgent,
    updateAgentPrompt,
    restoreAgentPromptVersion,
    updateAgentTools,
    updateAgentLabels,
    restoreAgentLabelsVersion,
    updateAgentEntities,
    restoreAgentEntitiesVersion,
  };
}
