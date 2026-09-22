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
  messages: Message[];
}
