/**
 * Types pour les conversations avec l'agent helper (issue #50).
 *
 * Contrairement à `Conversation` (types/conversation.ts), une
 * `AgentConversation` n'est rattachée à aucun dossier unique : elle peut
 * en créer/retrouver plusieurs (ou aucun) au fil de l'échange, via les
 * tools de l'agent. Les sources peuvent pointer vers un dossier ou une
 * analyse créée pendant l'échange.
 *
 * Voir backend/app/models/agent_conversation.py et
 * backend/app/schemas/agent_conversation.py pour les définitions côté API.
 */

/** Rôles des messages (aligné sur AgentMessageRole côté backend). */
export type AgentMessageRole = "user" | "assistant" | "tool_call" | "tool_result" | "error";

/** Types d'événements de streaming (aligné sur AgentChatEventKind). */
export type AgentChatEventKind = "tool_call" | "tool_result" | "thinking" | "done" | "error";

/** Source citée par l'assistant dans un message. */
export interface AgentMessageSource {
  id: string;
  /** Dossier créé/retrouvé par l'agent pendant l'échange. */
  dossierId: string | null;
  /** Analyse créée par l'agent pendant l'échange. */
  analyseId: string | null;
  /** Extrait de texte pertinent, si applicable. */
  excerpt: string | null;
}

/** Message d'une conversation avec l'agent helper. */
export interface AgentMessage {
  id: string;
  role: AgentMessageRole;
  /** Contenu textuel (null pour les tool_call/tool_result purs). */
  content: string | null;
  /** Nom du tool appelé (pour tool_call/tool_result). */
  toolName: string | null;
  /** Données structurées du tool (arguments, résultat). */
  data: Record<string, unknown>;
  createdAt: string;
  sources: AgentMessageSource[];
}

/** Conversation complète avec l'agent helper. */
export interface AgentConversation {
  id: string;
  /** user_id Keycloak ou identity.id d'un jeton API. */
  createdBy: string;
  title: string | null;
  createdAt: string;
  messages: AgentMessage[];
}

/** Vue légère pour la liste des conversations dans la mini-sidebar. */
export interface AgentConversationSummary {
  id: string;
  title: string | null;
  createdAt: string;
  lastMessagePreview: string | null;
}

/** Événement d'exécution du graphe (streaming via SSE). */
export interface AgentChatEvent {
  id: string;
  agentConversationId: string;
  kind: AgentChatEventKind;
  data: Record<string, unknown>;
}
