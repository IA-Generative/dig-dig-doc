export type AgentCapability =
  | "Classification documentaire"
  | "Extraction d'entités nommées"
  | "Contrôle de cohérence"
  | "Agent généraliste";

export interface PromptVersion {
  id: string;
  content: string;
  createdAt: string;
}

export interface Agent {
  id: string;
  name: string;
  capability: AgentCapability;
  prompt: string;
  promptVersions: PromptVersion[];
}

export interface Analyse {
  id: string;
  name: string;
  description: string;
  createdAt: string;
  agents: Agent[];
}
