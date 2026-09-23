import { ref } from "vue";

import { apiFetch } from "@/utils/api";
import type { Conversation, Message } from "@/types/conversation";

function mapMessage(api: any): Message {
  return { id: api.id, role: api.role, content: api.content, createdAt: api.created_at };
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

  return { conversation, ensureConversation, sendMessage, deleteConversation, setModel };
}
