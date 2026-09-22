export type AgentCapability =
  | "Classification documentaire"
  | "Extraction d'entités nommées"
  | "Contrôle de cohérence"
  | "Agent généraliste";

export type EntityType = "texte" | "date" | "nombre" | "booléen" | "identifiant";

export type AgentTool =
  | "lecture_document"
  | "recherche_web"
  | "base_connaissances"
  | "appel_agent"
  | "calculatrice"
  | "verification_coherence";

export const AGENT_TOOL_LABELS: Record<AgentTool, string> = {
  lecture_document: "Lecture de document",
  recherche_web: "Recherche web",
  base_connaissances: "Base de connaissances",
  appel_agent: "Appel à un autre agent",
  calculatrice: "Calculatrice",
  verification_coherence: "Vérification de cohérence",
};

export interface PromptVersion {
  id: string;
  content: string;
  createdAt: string;
}

export interface LabelDefinition {
  id: string;
  name: string;
  definition: string;
}

export interface EntityDefinition {
  id: string;
  name: string;
  definition: string;
  type: EntityType;
}

export interface Agent {
  id: string;
  name: string;
  capability: AgentCapability;
  prompt: string;
  promptVersions: PromptVersion[];
  tools: AgentTool[];
  /** Utilisé quand capability === "Classification documentaire". */
  labels: LabelDefinition[];
  /** Utilisé quand capability === "Extraction d'entités nommées". */
  entities: EntityDefinition[];
}

export interface Analyse {
  id: string;
  name: string;
  description: string;
  createdAt: string;
  agents: Agent[];
}
