import { computed, reactive } from "vue";

import { apiFetch } from "@/utils/api";
import type { ConversationSummary } from "@/types/conversation";

function mapSummary(api: any): ConversationSummary {
  return {
    id: api.id,
    dossierId: api.dossier_id,
    dossierName: api.dossier_name,
    lastMessagePreview: api.last_message_preview ?? undefined,
    lastActivityAt: api.last_activity_at,
  };
}

// Store partagé par toute l'application : la liste "mes conversations"
// affichée dans la sidebar (façon ChatGPT), tous dossiers confondus.
const conversations = reactive<ConversationSummary[]>([]);

async function fetchList() {
  const data = await apiFetch<any[]>("/api/conversations");
  conversations.splice(0, conversations.length, ...data.map(mapSummary));
}

export function useMyConversations() {
  return { list: computed(() => conversations), fetchList };
}
