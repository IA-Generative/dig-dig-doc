import { computed, reactive } from "vue";

import type { Agent, AgentCapability, Analyse } from "@/types/analyse";

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

let nextId = analyses.length + 1;

const promptTemplates: Record<AgentCapability, string> = {
  "Classification documentaire":
    "Tu es un agent de classification documentaire. Analyse le document fourni et retourne une catégorie " +
    "normalisée parmi [CNI, passeport, justificatif de domicile, avis d'imposition, autre] avec un score de confiance.",
  "Extraction d'entités nommées":
    "Tu es un agent d'extraction d'entités nommées. Extrait nom, prénom, date de naissance, adresse postale et " +
    "numéros d'identification au format JSON strict, sans inventer de champ absent du document.",
  "Contrôle de cohérence":
    "Tu es un agent de contrôle de cohérence. Compare les entités extraites entre les pièces du dossier et signale " +
    "les incohérences (valide / incohérence_détectée / vérification_manuelle_requise) en citant les champs divergents.",
  "Agent généraliste": "Tu es un agent généraliste. Décris précisément la tâche que tu dois accomplir sur le dossier.",
};

export function suggestPrompt(capability: AgentCapability): string {
  return promptTemplates[capability];
}

export function useAnalyses() {
  const list = computed(() => analyses);

  const getById = (id: string) => analyses.find((a) => a.id === id);

  const create = (name: string, description: string) => {
    const analyse: Analyse = {
      id: `analyse-${nextId++}`,
      name,
      description,
      createdAt: new Date().toISOString(),
      agents: [],
    };
    analyses.unshift(analyse);
    return analyse;
  };

  const addAgent = (analyseId: string, name: string, capability: AgentCapability, prompt: string) => {
    const analyse = getById(analyseId);
    if (!analyse) return;
    const agent: Agent = {
      id: `agent-${Date.now()}`,
      name,
      capability,
      prompt,
      promptVersions: [],
    };
    analyse.agents.push(agent);
    return agent;
  };

  const updateAgentPrompt = (analyseId: string, agentId: string, newPrompt: string) => {
    const analyse = getById(analyseId);
    const agent = analyse?.agents.find((a) => a.id === agentId);
    if (!agent || agent.prompt === newPrompt) return;
    agent.promptVersions.unshift({
      id: `v-${Date.now()}`,
      content: agent.prompt,
      createdAt: new Date().toISOString(),
    });
    agent.prompt = newPrompt;
  };

  const restoreAgentPromptVersion = (analyseId: string, agentId: string, versionId: string) => {
    const analyse = getById(analyseId);
    const agent = analyse?.agents.find((a) => a.id === agentId);
    const version = agent?.promptVersions.find((v) => v.id === versionId);
    if (!agent || !version) return;
    updateAgentPrompt(analyseId, agentId, version.content);
  };

  return { list, getById, create, addAgent, updateAgentPrompt, restoreAgentPromptVersion };
}
