import { ref } from "vue";

import { apiFetch } from "@/utils/api";
import type {
  ChatEvent,
  Conversation,
  Feedback,
  FeedbackReasonCode,
  FeedbackValue,
  Message,
  MessageSource,
} from "@/types/conversation";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

function mapFeedback(api: any): Feedback | null {
  if (!api) return null;
  return {
    id: api.id,
    messageId: api.message_id,
    value: api.value,
    reasons: api.reasons,
    comment: api.comment,
    createdAt: api.created_at,
  };
}

function mapSource(api: any): MessageSource {
  return {
    id: api.id,
    dossierDocumentId: api.dossier_document_id,
    executionStepId: api.execution_step_id,
    excerpt: api.excerpt,
    pages: (api.pages ?? []).map((p: any) => ({ id: p.id, pageNumber: p.page_number })),
    boundingBoxes: (api.bounding_boxes ?? []).map((b: any) => ({ id: b.id })),
  };
}

function mapMessage(api: any): Message {
  return {
    id: api.id,
    role: api.role,
    content: api.content,
    createdAt: api.created_at,
    sources: (api.sources ?? []).map(mapSource),
    feedback: mapFeedback(api.feedback),
  };
}

function mapConversation(api: any): Conversation {
  return {
    id: api.id,
    dossierId: api.dossier_id,
    userId: api.user_id,
    createdAt: api.created_at,
    model: api.model,
    messages: api.messages.map(mapMessage),
  };
}

// Chat de la page dossier : une conversation par (dossier, utilisateur
// courant). Instancié par dossier, contrairement à useAnalyses/useDossiers
// qui sont des stores partagés par toute l'application.
export function useConversations(dossierId: string) {
  const conversation = ref<Conversation | undefined>(undefined);

  // Garde contre les appels concurrents : si ensureConversation() est
  // appelé plusieurs fois avant la résolution du premier appel (ex:
  // onMounted + sendMessage), on réutilise la même promesse au lieu de
  // déclencher plusieurs créations de conversation.
  let pending: Promise<Conversation> | undefined;

  const ensureConversation = async (): Promise<Conversation> => {
    if (conversation.value) return conversation.value;
    if (pending) return pending;

    pending = (async () => {
      const existing = await apiFetch<any[]>(`/api/dossiers/${dossierId}/conversations`);
      if (existing.length > 0) {
        conversation.value = mapConversation(existing[0]);
      } else {
        const created = await apiFetch<any>(`/api/dossiers/${dossierId}/conversations`, { method: "POST" });
        conversation.value = mapConversation(created);
      }
      return conversation.value!;
    })().finally(() => {
      pending = undefined;
    });

    return pending;
  };

  const sendMessage = async (content: string) => {
    const current = await ensureConversation();
    const data = await apiFetch<any>(`/api/dossiers/${dossierId}/conversations/${current.id}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
    conversation.value = mapConversation(data);
  };

  // SSE : s'abonne au flux d'événements de chat (tool_call, tool_result,
  // done, error) pendant que le worker exécute le graphe LangGraph. Le
  // callback reçoit chaque événement au fur et à mesure, et onEventDone est
  // appelé quand l'exécution est terminée (le frontend peut alors
  // recharger la conversation pour récupérer le message assistant final).
  const streamConversation = (
    conversationId: string,
    onEvent: (event: ChatEvent) => void,
    onDone: () => void,
  ): (() => void) => {
    const url = `${API_BASE_URL}/api/dossiers/${dossierId}/conversations/${conversationId}/stream`;
    const eventSource = new EventSource(url, { withCredentials: true });

    eventSource.addEventListener("chat-event", (event) => {
      const data = JSON.parse(event.data);
      onEvent(data);
    });
    eventSource.addEventListener("done", () => {
      eventSource.close();
      onDone();
    });
    eventSource.addEventListener("error", () => {
      eventSource.close();
    });

    return () => eventSource.close();
  };

  // Recharge la conversation depuis l'API (pour récupérer le message
  // assistant final avec ses sources après la fin du streaming).
  const refreshConversation = async () => {
    const current = conversation.value;
    if (!current) return;
    const list = await apiFetch<any[]>(`/api/dossiers/${dossierId}/conversations`);
    const found = list.find((c: any) => c.id === current.id);
    if (found) conversation.value = mapConversation(found);
  };

  // Supprime uniquement la conversation (et ses messages) : le dossier, ses
  // documents et l'analyse associée ne sont pas touchés.
  const deleteConversation = async () => {
    const current = conversation.value;
    if (!current) return;
    await apiFetch(`/api/dossiers/${dossierId}/conversations/${current.id}`, { method: "DELETE" });
    conversation.value = undefined;
  };

  const setModel = async (model: string | null) => {
    const current = await ensureConversation();
    const data = await apiFetch<any>(`/api/dossiers/${dossierId}/conversations/${current.id}/model`, {
      method: "PUT",
      body: JSON.stringify({ model }),
    });
    conversation.value = mapConversation(data);
  };

  const setFeedback = async (
    messageId: string,
    value: FeedbackValue,
    reasons: FeedbackReasonCode[] = [],
    comment: string | null = null,
  ) => {
    const current = await ensureConversation();
    const data = await apiFetch<any>(
      `/api/dossiers/${dossierId}/conversations/${current.id}/messages/${messageId}/feedback`,
      { method: "PUT", body: JSON.stringify({ value, reasons, comment }) },
    );
    conversation.value = mapConversation(data);
  };

  const removeFeedback = async (messageId: string) => {
    const current = await ensureConversation();
    const data = await apiFetch<any>(
      `/api/dossiers/${dossierId}/conversations/${current.id}/messages/${messageId}/feedback`,
      { method: "DELETE" },
    );
    conversation.value = mapConversation(data);
  };

  return {
    conversation,
    ensureConversation,
    sendMessage,
    streamConversation,
    refreshConversation,
    deleteConversation,
    setModel,
    setFeedback,
    removeFeedback,
  };
}
