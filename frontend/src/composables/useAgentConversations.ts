import { reactive, ref } from "vue";

import { useChatStream } from "@/composables/useChatStream";
import { apiFetch } from "@/utils/api";
import type {
  AgentChatEvent,
  AgentConversation,
  AgentConversationSummary,
  AgentMessage,
  AgentMessageSource,
} from "@/types/agentConversation";

function mapSource(api: any): AgentMessageSource {
  return {
    id: api.id,
    dossierId: api.dossier_id ?? null,
    analyseId: api.analyse_id ?? null,
    excerpt: api.excerpt ?? null,
  };
}

function mapMessage(api: any): AgentMessage {
  return {
    id: api.id,
    role: api.role,
    content: api.content ?? null,
    toolName: api.tool_name ?? null,
    data: api.data ?? {},
    createdAt: api.created_at,
    sources: (api.sources ?? []).map(mapSource),
  };
}

function mapConversation(api: any): AgentConversation {
  return {
    id: api.id,
    createdBy: api.created_by,
    title: api.title ?? null,
    createdAt: api.created_at,
    messages: (api.messages ?? []).map(mapMessage),
  };
}

function mapSummary(api: any): AgentConversationSummary {
  return {
    id: api.id,
    title: api.title ?? null,
    createdAt: api.created_at,
    lastMessagePreview: api.last_message_preview ?? null,
  };
}

/**
 * SSE : s'abonne au flux d'événements de l'agent (tool_call, tool_result,
 * thinking, done, error) pendant que le worker exécute le graphe
 * LangGraph de l'agent helper.
 *
 * Retourne une fonction `close()` pour stopper le flux.
 */
function streamConversation(
  conversationId: string,
  onEvent: (event: AgentChatEvent) => void,
  onDone: () => void,
): () => void {
  const { start } = useChatStream({
    onEvent: (event) => onEvent(event as AgentChatEvent),
    onDone,
  });
  return start(`/api/agent-conversations/${conversationId}/stream`);
}

/**
 * Composable pour les conversations avec l'agent helper (issue #50).
 *
 * Gère la liste paginée des conversations (mini-sidebar de la modal) et
 * la conversation active (messages + streaming SSE). Contrairement à
 * useConversations (une conversation par dossier), les AgentConversations
 * ne sont pas rattachées à un dossier : l'agent peut en créer/retrouver
 * plusieurs au fil de l'échange.
 *
 * Endpoints REST (voir backend/app/routers/agent_conversations.py) :
 * - GET    /api/agent-conversations              (liste paginée)
 * - POST   /api/agent-conversations              (création)
 * - GET    /api/agent-conversations/{id}         (détail)
 * - DELETE /api/agent-conversations/{id}         (suppression)
 * - POST   /api/agent-conversations/{id}/messages (envoi + dispatch Celery)
 * - GET    /api/agent-conversations/{id}/stream   (SSE des événements)
 */
export function useAgentConversations() {
  const summaries = reactive<AgentConversationSummary[]>([]);
  const activeConversation = ref<AgentConversation | undefined>(undefined);
  const isLoading = ref(false);

  async function fetchList(page = 1, pageSize = 20): Promise<void> {
    const data = await apiFetch<{ items: any[]; total: number }>(
      `/api/agent-conversations?page=${page}&page_size=${pageSize}`,
    );
    summaries.splice(0, summaries.length, ...data.items.map(mapSummary));
  }

  async function createConversation(): Promise<AgentConversation> {
    const data = await apiFetch<any>("/api/agent-conversations", { method: "POST" });
    const conversation = mapConversation(data);
    // Ajoute en tête de liste (la plus récente).
    summaries.unshift({
      id: conversation.id,
      title: conversation.title,
      createdAt: conversation.createdAt,
      lastMessagePreview: null,
    });
    return conversation;
  }

  async function selectConversation(conversationId: string): Promise<void> {
    isLoading.value = true;
    try {
      const data = await apiFetch<any>(`/api/agent-conversations/${conversationId}`);
      activeConversation.value = mapConversation(data);
    } finally {
      isLoading.value = false;
    }
  }

  async function deleteConversation(conversationId: string): Promise<void> {
    await apiFetch(`/api/agent-conversations/${conversationId}`, { method: "DELETE" });
    const index = summaries.findIndex((c) => c.id === conversationId);
    if (index !== -1) summaries.splice(index, 1);
    if (activeConversation.value?.id === conversationId) {
      activeConversation.value = undefined;
    }
  }

  async function sendMessage(content: string, model: string | null = null): Promise<void> {
    const current = activeConversation.value;
    if (!current) return;
    const body: Record<string, unknown> = { content };
    if (model) body.model = model;
    const data = await apiFetch<any>(`/api/agent-conversations/${current.id}/messages`, {
      method: "POST",
      body: JSON.stringify(body),
    });
    activeConversation.value = mapConversation(data);
    // Met à jour l'aperçu dans la liste.
    const summary = summaries.find((s) => s.id === current.id);
    if (summary) {
      summary.lastMessagePreview = content;
    }
  }

  /** Recharge la conversation active depuis l'API (message assistant final). */
  async function refreshConversation(): Promise<void> {
    const current = activeConversation.value;
    if (!current) return;
    const data = await apiFetch<any>(`/api/agent-conversations/${current.id}`);
    activeConversation.value = mapConversation(data);
    // Met à jour l'aperçu dans la liste.
    const summary = summaries.find((s) => s.id === current.id);
    if (summary && activeConversation.value.messages.length > 0) {
      const lastMsg = activeConversation.value.messages[activeConversation.value.messages.length - 1];
      summary.lastMessagePreview = lastMsg.content ?? null;
    }
  }

  return {
    summaries,
    activeConversation,
    isLoading,
    fetchList,
    createConversation,
    selectConversation,
    deleteConversation,
    sendMessage,
    refreshConversation,
    streamConversation,
  };
}
