export type MessageRole = "user" | "assistant";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
}

/** Chat de la page dossier : une conversation par (dossier, utilisateur). */
export interface Conversation {
  id: string;
  dossierId: string;
  userId: string;
  createdAt: string;
  /** Identifiant de modèle (voir GET /api/models) ; null = pas de préférence, le hub par défaut sera utilisé. */
  model: string | null;
  messages: Message[];
}

/** Entrée de la liste "mes conversations" dans la sidebar, façon ChatGPT. */
export interface ConversationSummary {
  id: string;
  dossierId: string;
  dossierName: string;
  lastMessagePreview?: string;
  lastActivityAt: string;
}
