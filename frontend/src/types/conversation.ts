export type MessageRole = "user" | "assistant";

export type FeedbackValue = "up" | "down";

export type FeedbackReasonCode =
  | "incorrect_answer"
  | "not_useful"
  | "questionable_sources"
  | "inappropriate_tone"
  | "other";

export const FEEDBACK_REASON_LABELS: Record<FeedbackReasonCode, string> = {
  incorrect_answer: "Réponse incorrecte",
  not_useful: "Pas utile",
  questionable_sources: "Sources douteuses",
  inappropriate_tone: "Ton inapproprié",
  other: "Autre",
};

export interface Feedback {
  id: string;
  messageId: string;
  value: FeedbackValue;
  reasons: FeedbackReasonCode[];
  comment: string | null;
  createdAt: string;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
  feedback: Feedback | null;
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
