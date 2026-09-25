<script setup lang="ts">
/**
 * Modal de l'agent helper (issue #50) : mini-sidebar (liste des
 * agent_conversations via useAgentConversations) + ChatWindow branché sur
 * /api/agent-conversations/*. Une source dossier_id dans un message → lien
 * cliquable router.push({ path: '/dossiers/' + dossierId }).
 *
 * Ouverte depuis UserMenu.vue (bouton "Assistant" à côté des entrées
 * existantes). Contrairement au chat de dossier (DossierDetailPage), les
 * conversations de l'agent helper ne sont pas rattachées à un dossier :
 * l'agent peut en créer/retrouver plusieurs au fil de l'échange.
 */
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import ChatWindow, { type ChatWindowMessage, type ChatWindowSource } from "@/components/ChatWindow.vue";
import InfoModal from "@/components/InfoModal.vue";
import { useAgentConversations } from "@/composables/useAgentConversations";
import { useModels } from "@/composables/useModels";
import type { AgentChatEvent } from "@/types/agentConversation";
import { DOSSIER_STATUS_LABELS, type DossierStatus } from "@/types/dossier";

const props = defineProps<{ open: boolean }>();
const emit = defineEmits<{ close: [] }>();

const { models: availableModels, fetchModels } = useModels();
const selectedModel = ref<string>("");

const router = useRouter();
const {
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
} = useAgentConversations();

// Streaming des événements d'exécution (tool_call, tool_result, etc.).
const chatEvents = ref<{ kind: string; data: Record<string, unknown> }[]>([]);
const isChatRunning = ref(false);
let closeChatStream: (() => void) | undefined;

// Messages formatés pour ChatWindow (user + assistant uniquement, les
// tool_call/tool_result sont des traces d'exécution affichées via le
// streaming, pas comme des messages persistés).
const messages = computed<ChatWindowMessage[]>(() => {
  if (!activeConversation.value) return [];
  return activeConversation.value.messages
    .filter((m) => m.role === "user" || m.role === "assistant")
    .map((m) => ({
      id: m.id,
      role: m.role as "user" | "assistant",
      content: m.content ?? "",
      sources: m.sources.map((s): ChatWindowSource => ({
        id: s.id,
        excerpt: s.excerpt,
      })),
    }));
});

onMounted(() => {
  if (props.open) {
    fetchList();
    fetchModels();
  }
});

/**
 * Dossiers dont le pipeline a été lancé par l'agent pendant l'exécution
 * courante. Détecté en scannant les tool_call events du flux SSE à la
 * recherche de "run_dossier" — l'agent appelle cet outil pour démarrer
 * le pipeline (classification, extraction, agents) sur un dossier.
 */
const launchedDossiers = computed(() => {
  const result: { dossierId: string; name: string | null; status: DossierStatus | null }[] = [];
  for (const event of chatEvents.value) {
    if (event.kind === "tool_call" && event.data.tool_name === "run_dossier") {
      const args = event.data.arguments as Record<string, unknown> | undefined;
      const dossierId = args?.dossier_id as string | undefined;
      if (dossierId) {
        result.push({ dossierId, name: null, status: null });
      }
    }
    if (event.kind === "tool_result" && event.data.tool_name === "run_dossier") {
      const preview = event.data.preview as string | undefined;
      if (preview && result.length > 0) {
        // Le preview contient « Pipeline lancé sur « <name> » (statut : <status>). »
        const nameMatch = preview.match(/« (.+?) »/);
        const statusMatch = preview.match(/statut : (\w+)/);
        const last = result[result.length - 1];
        if (nameMatch) last.name = nameMatch[1];
        if (statusMatch) last.status = statusMatch[1] as DossierStatus;
      }
    }
  }
  return result;
});

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      fetchList();
      fetchModels();
    } else {
      stopStream();
    }
  },
);

onUnmounted(() => stopStream());

function stopStream() {
  closeChatStream?.();
  closeChatStream = undefined;
  isChatRunning.value = false;
}

async function onNewConversation() {
  stopStream();
  activeConversation.value = await createConversation();
}

async function onSelectConversation(conversationId: string) {
  stopStream();
  await selectConversation(conversationId);
}

async function onDeleteConversation(conversationId: string) {
  if (!confirm("Supprimer cette conversation ?")) return;
  stopStream();
  await deleteConversation(conversationId);
}

async function onChatSubmit(content: string) {
  if (isChatRunning.value) return;

  // Crée une conversation si aucune n'est active.
  if (!activeConversation.value) {
    activeConversation.value = await createConversation();
  }

  const conversationId = activeConversation.value.id;

  // Démarre le streaming AVANT d'envoyer le message pour ne pas manquer
  // les premiers événements (le worker peut être très rapide).
  isChatRunning.value = true;
  chatEvents.value = [];
  closeChatStream = streamConversation(
    conversationId,
    (event: AgentChatEvent) => {
      chatEvents.value.push({ kind: event.kind, data: event.data });
    },
    async () => {
      // done : recharge la conversation pour récupérer le message assistant
      // final avec ses sources.
      await refreshConversation();
      isChatRunning.value = false;
      chatEvents.value = [];
      closeChatStream = undefined;
    },
  );
  await sendMessage(content, selectedModel.value);
}

function goToDossier(dossierId: string) {
  emit("close");
  router.push({ path: `/dossiers/${dossierId}` });
}

function formatRelativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(diffMs / 60_000);
  if (minutes < 1) return "à l'instant";
  if (minutes < 60) return `il y a ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `il y a ${hours} h`;
  const days = Math.round(hours / 24);
  return `il y a ${days} j`;
}
</script>

<template>
  <InfoModal title="Assistant" :open="open" @close="emit('close')">
    <div class="helper-agent">
      <!-- Mini-sidebar : liste des conversations -->
      <aside class="helper-agent__sidebar">
        <button
          type="button"
          class="helper-agent__new-btn"
          :disabled="isChatRunning"
          @click="onNewConversation"
        >
          <VIcon name="ri-add-line" />
          <span>Nouvelle conversation</span>
        </button>

        <div v-if="summaries.length === 0" class="helper-agent__empty">
          Aucune conversation pour l'instant.
        </div>
        <nav v-else class="helper-agent__list" aria-label="Conversations de l'assistant">
          <div
            v-for="item in summaries"
            :key="item.id"
            role="button"
            tabindex="0"
            class="helper-agent__item"
            :class="{ 'helper-agent__item--active': activeConversation?.id === item.id }"
            @click="onSelectConversation(item.id)"
            @keydown.enter="onSelectConversation(item.id)"
            @keydown.space.prevent="onSelectConversation(item.id)"
          >
            <VIcon name="ri-chat-3-line" />
            <span class="helper-agent__item-text">
              <span class="helper-agent__item-title">{{ item.title ?? "Sans titre" }}</span>
              <span class="helper-agent__item-preview">
                {{ item.lastMessagePreview ?? "Aucun message" }}
              </span>
            </span>
            <span class="helper-agent__item-time">{{ formatRelativeTime(item.createdAt) }}</span>
            <button
              type="button"
              class="helper-agent__item-delete"
              aria-label="Supprimer cette conversation"
              title="Supprimer cette conversation"
              @click.stop="onDeleteConversation(item.id)"
            >
              <VIcon name="ri-delete-bin-line" />
            </button>
          </div>
        </nav>
      </aside>

      <!-- Zone de chat -->
      <div class="helper-agent__chat">
        <!-- Indicateur "pipeline en cours" : visible quand l'agent a lancé
             un dossier via run_dossier pendant l'exécution courante. -->
        <div
          v-for="dossier in launchedDossiers"
          :key="dossier.dossierId"
          class="helper-agent__pipeline-indicator"
        >
          <VIcon name="ri-loader-4-line" class="spin" />
          <span class="helper-agent__pipeline-text">
            Pipeline en cours sur « {{ dossier.name ?? dossier.dossierId }} »
            <span v-if="dossier.status" class="helper-agent__pipeline-status">
              ({{ DOSSIER_STATUS_LABELS[dossier.status] }})
            </span>
          </span>
          <button
            type="button"
            class="helper-agent__pipeline-link"
            @click="goToDossier(dossier.dossierId)"
          >
            <VIcon name="ri-external-link-line" />
            <span>Voir le dossier</span>
          </button>
        </div>

        <div v-if="isLoading" class="helper-agent__loading">
          <VIcon name="ri-loader-4-line" class="spin" />
          <span>Chargement…</span>
        </div>
        <div v-else class="helper-agent__chat-inner">
          <div class="helper-agent__model-bar">
            <label class="helper-agent__model-label" for="helper-model-select">
              <VIcon name="ri-cpu-line" />
              <span>Modèle</span>
            </label>
            <select
              id="helper-model-select"
              v-model="selectedModel"
              class="helper-agent__model-select"
              :disabled="isChatRunning"
            >
              <option value="">Modèle par défaut</option>
              <option v-for="id in availableModels" :key="id" :value="id">{{ id }}</option>
            </select>
          </div>
          <ChatWindow
            :messages="messages"
          :stream-events="chatEvents"
          :is-running="isChatRunning"
          intro-title="Assistant dig-dig-doc"
          intro-text="Posez une question, demandez la création d'un dossier, la recherche d'analyses, et plus encore."
          placeholder="Écrivez votre message à l'assistant..."
          @submit="onChatSubmit"
        >
          <!-- Sources : si une source a un dossierId, on affiche un lien cliquable -->
          <template #source="{ source }">
            <span v-if="source.pages && source.pages.length > 0" class="chat-message__source-pages">
              {{ source.pages.map((p) => `p. ${p.pageNumber}`).join(", ") }}
            </span>
            <span v-if="source.excerpt" class="chat-message__source-excerpt">« {{ source.excerpt }} »</span>
          </template>
        </ChatWindow>
        </div>
      </div>
    </div>
  </InfoModal>
</template>

<style scoped>
.helper-agent {
  display: flex;
  gap: 1rem;
  height: 60vh;
  min-height: 24rem;
}

/* Mini-sidebar façon ChatGPT */
.helper-agent__sidebar {
  width: 14rem;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  border-right: 1px solid var(--border-default-grey);
  padding-right: 0.75rem;
  overflow: hidden;
}

.helper-agent__new-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-action-high-blue-france);
  border-radius: 0.375rem;
  background: var(--background-alt-blue-france);
  color: var(--text-action-high-blue-france);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  flex-shrink: 0;
}

.helper-agent__new-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.helper-agent__empty {
  padding: 1rem 0.5rem;
  text-align: center;
  font-size: 0.8rem;
  color: var(--text-mention-grey);
}

.helper-agent__list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.helper-agent__item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border: none;
  border-radius: 0.375rem;
  background: transparent;
  color: var(--text-default-grey);
  cursor: pointer;
  text-align: left;
  width: 100%;
}

.helper-agent__item:hover {
  background: var(--background-alt-grey-hover);
}

.helper-agent__item--active {
  background: var(--background-action-low-blue-france);
  color: var(--text-active-blue-france);
}

.helper-agent__item-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.helper-agent__item-title {
  font-size: 0.8rem;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.helper-agent__item-preview {
  font-size: 0.7rem;
  color: var(--text-mention-grey);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.helper-agent__item-time {
  font-size: 0.65rem;
  color: var(--text-mention-grey);
  flex-shrink: 0;
}

.helper-agent__item-delete {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--text-mention-grey);
  cursor: pointer;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.1s;
}

.helper-agent__item:hover .helper-agent__item-delete,
.helper-agent__item--active .helper-agent__item-delete {
  opacity: 1;
}

.helper-agent__item-delete:hover {
  background: var(--background-alt-grey-hover);
  color: var(--text-default-grey);
}

/* Zone de chat */
.helper-agent__chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.helper-agent__chat-inner {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.helper-agent__model-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0;
  margin-bottom: 0.25rem;
}

.helper-agent__model-label {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--text-mention-grey);
  white-space: nowrap;
}

.helper-agent__model-select {
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 0.25rem;
  background: var(--background-default-grey);
  color: var(--text-default-grey);
  cursor: pointer;
}

.helper-agent__model-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.helper-agent__loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: var(--text-mention-grey);
}

.helper-agent__loading .spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Lien cliquable vers un dossier dans les sources */
.helper-agent__source-link {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  color: var(--text-action-high-blue-france);
  text-decoration: none;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
}

.helper-agent__source-link:hover {
  text-decoration: underline;
}

/* Indicateur "pipeline en cours" pendant que l'agent a lancé un dossier */
.helper-agent__pipeline-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--background-alt-blue-france);
  border: 1px solid var(--border-action-high-blue-france);
  border-radius: 0.375rem;
  font-size: 0.8rem;
  color: var(--text-action-high-blue-france);
  margin-bottom: 0.5rem;
}

.helper-agent__pipeline-indicator .spin {
  animation: spin 1s linear infinite;
  flex-shrink: 0;
}

.helper-agent__pipeline-text {
  flex: 1;
  min-width: 0;
}

.helper-agent__pipeline-status {
  color: var(--text-mention-grey);
  font-weight: 400;
}

.helper-agent__pipeline-link {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  border: none;
  background: transparent;
  color: var(--text-action-high-blue-france);
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  flex-shrink: 0;
}

.helper-agent__pipeline-link:hover {
  text-decoration: underline;
}
</style>
