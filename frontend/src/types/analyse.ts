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

/** Un instantané d'une valeur passée, horodaté, pour permettre une restauration. */
export interface Version<T> {
  id: string;
  content: T;
  createdAt: string;
}

export type PromptVersion = Version<string>;

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

/**
 * Classification documentaire : une analyse simple (un prompt appliqué
 * systématiquement à tous les documents du dossier, pas un agent) qui
 * retourne un label parmi ceux définis ici, avec un score de confiance.
 * Un seul jeu de labels par analyse.
 */
export interface Classification {
  prompt: string;
  promptVersions: PromptVersion[];
  labels: LabelDefinition[];
  labelsVersions: Version<LabelDefinition[]>[];
}

/**
 * Extraction d'entités nommées : même principe que la classification,
 * un seul jeu d'entités à extraire par analyse.
 */
export interface Extraction {
  prompt: string;
  promptVersions: PromptVersion[];
  entities: EntityDefinition[];
  entitiesVersions: Version<EntityDefinition[]>[];
}

/**
 * Un agent est créé librement par l'utilisateur pour un but métier propre
 * à l'analyse (contrôle de cohérence, rédaction, construction d'une
 * timeline...) : nom, prompt et outils, sans capacité prédéfinie.
 */
export interface Agent {
  id: string;
  name: string;
  prompt: string;
  promptVersions: PromptVersion[];
  tools: AgentTool[];
  toolsVersions: Version<AgentTool[]>[];
  /** Si vrai, le résultat de cet agent est présenté comme une sortie visible dans la page de résultat du dossier. */
  output: boolean;
  outputVersions: Version<boolean>[];
}

export interface Analyse {
  id: string;
  name: string;
  description: string;
  createdAt: string;
  classification: Classification;
  extraction: Extraction;
  agents: Agent[];
}

/** Version allégée renvoyée par la liste des analyses (GET /api/analyses). */
export interface AnalyseSummary {
  id: string;
  name: string;
  description: string;
  createdAt: string;
  agentCount: number;
}
