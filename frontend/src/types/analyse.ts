export type AgentCapability =
  | "Classification documentaire"
  | "Extraction d'entités nommées"
  | "Contrôle de cohérence"
  | "Agent généraliste";

export type EntityType = "texte" | "date" | "nombre" | "booléen" | "identifiant";

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
