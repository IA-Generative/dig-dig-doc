<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import ChatWindow from "@/components/ChatWindow.vue";
import DossierDocuments from "@/components/dossiers/DossierDocuments.vue";
import DossierResults from "@/components/dossiers/DossierResults.vue";
import FeedbackReasonsModal from "@/components/dossiers/FeedbackReasonsModal.vue";
import { useAnalyses } from "@/composables/useAnalyses";
import { useChatStream } from "@/composables/useChatStream";
import { useConversations } from "@/composables/useConversations";
import { useDossiers } from "@/composables/useDossiers";
import { useModels } from "@/composables/useModels";
import { useMyConversations } from "@/composables/useMyConversations";
import type { FeedbackReasonCode } from "@/types/conversation";
import { DOSSIER_STATUS_LABELS, type DossierStatus } from "@/types/dossier";

const route = useRoute();
const dossierId = String(route.params.id);
const { list: dossiers, addDocuments, fetchDossier, streamDossier, regenerateDocumentSummary, regenerateDossierSummary } = useDossiers();
const { getById: getAnalyseById, fetchAnalyse } = useAnalyses();
const {
  conversation,
  ensureConversation,
  sendMessage,
  refreshConversation,
  deleteConversation,
  setModel,
  setFeedback,
  removeFeedback,
} = useConversations(dossierId);
const { fetchList: refreshSidebarConversations } = useMyConversations();
const { models, fetchModels } = useModels();

// Pouce haut : bascule directement. Pouce bas : ouvre une modale pour
// recueillir la/les raison(s) avant d'envoyer (comme Muffin).
const feedbackReasonsModalOpened = ref(false);
const pendingDownMessageId = ref<string | null>(null);

// Streaming du chat : événements reçus pendant l'exécution du graphe
// LangGraph (tool_call, tool_result, done, error). Affichés en temps réel
// sous la forme d'une "pensée" de l'assistant.
const chatEvents = ref<{ kind: string; data: Record<string, unknown> }[]>([]);
const { isRunning: isChatRunning, start: startChatStream, stop: stopChatStream } = useChatStream({
  onEvent: (event) => chatEvents.value.push(event),
  onDone: async () => {
    // done : recharge la conversation pour récupérer le message assistant
    // final avec ses sources, puis ferme le streaming.
    await refreshConversation();
    await refreshSidebarConversations();
    chatEvents.value = [];
  },
});

// Fichiers en attente d'envoi (attachés au message).
const pendingFiles = ref<File[]>([]);
const isDetailsModalOpened = ref(false);

function formatDateTime(iso?: string) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

function thumbUp(messageId: string) {
  const current = messages.value.find((m) => m.id === messageId)?.feedback;
  if (current?.value === "up") removeFeedback(messageId);
  else setFeedback(messageId, "up");
}

function thumbDown(messageId: string) {
  const current = messages.value.find((m) => m.id === messageId)?.feedback;
  if (current?.value === "down") {
    removeFeedback(messageId);
    return;
  }
  pendingDownMessageId.value = messageId;
  feedbackReasonsModalOpened.value = true;
}

function submitDownFeedback(reasons: FeedbackReasonCode[], comment: string | null) {
  if (!pendingDownMessageId.value) return;
  setFeedback(pendingDownMessageId.value, "down", reasons, comment);
  pendingDownMessageId.value = null;
}

// "" représente "pas de préférence" (null côté API) : DsfrSelect n'accepte
// pas de valeur null pour une option.
const modelOptions = computed(() => [
  { value: "", text: "Modèle par défaut du hub" },
  ...models.value.map((id) => ({ value: id, text: id })),
]);

function onModelChange(value: string) {
  setModel(value || null);
}

const dossier = computed(() => dossiers.value.find((d) => d.id === dossierId));
const analyse = computed(() => (dossier.value ? getAnalyseById(dossier.value.analyseId) : undefined));

// SSE : on s'abonne au flux du dossier pour suivre en temps réel l'état
// d'extraction de texte des documents (et plus tard l'exécution). Le serveur
// émet `done` quand il n'y a plus de travail actif, puis on ferme.
let closeStream: (() => void) | undefined;

onMounted(async () => {
  // ensureConversation() crée la conversation de cet utilisateur pour ce
  // dossier si elle n'existe pas encore : c'est ce qui la fait apparaître
  // dans la sidebar (voir App.vue, qui rafraîchit aussi sur la navigation).
  await ensureConversation();
  refreshSidebarConversations();
  fetchModels();
  // Le dossier n'est pas forcément dans la page actuellement chargée par
  // DossiersPage (pagination côté serveur) : on le charge directement.
  const loaded = await fetchDossier(dossierId);
  await fetchAnalyse(loaded.analyseId);
  closeStream = streamDossier(dossierId, () => {});
});

onUnmounted(() => {
  closeStream?.();
  stopChatStream();
});
watch(
  () => dossier.value?.analyseId,
  (analyseId) => {
    if (analyseId) fetchAnalyse(analyseId);
  },
);

const statusBadgeType: Record<DossierStatus, "new" | "info" | "success" | "warning" | "error"> = {
  en_attente: "new",
  en_cours: "info",
  terminé: "success",
  arrêté: "warning",
  échec: "error",
};

// Fil d'échange pour alimenter l'analyse (documents, notes) : les résultats
// eux-mêmes sont présentés directement dans DossierResults, pas ici, pour
// rester visibles sans avoir à remonter la conversation.
const messages = computed(() => conversation.value?.messages ?? []);

function onAttachFiles(files: File[]) {
  pendingFiles.value.push(...files);
}

function removePendingFile(index: number) {
  pendingFiles.value.splice(index, 1);
}

async function onChatSubmit(content: string) {
  if (!dossier.value) return;
  if (isChatRunning.value) return;

  if (pendingFiles.value.length > 0) {
    await addDocuments(dossier.value.id, pendingFiles.value);
  }

  const parts = [
    ...(pendingFiles.value.length > 0
      ? [`Document(s) ajouté(s) à l'analyse : ${pendingFiles.value.map((f) => f.name).join(", ")}`]
      : []),
    ...(content ? [content] : []),
  ];

  pendingFiles.value = [];

  const current = await ensureConversation();
  // Démarre le streaming AVANT d'envoyer le message pour ne pas manquer
  // les premiers événements (le worker peut être très rapide).
  chatEvents.value = [];
  startChatStream(`/api/dossiers/${dossierId}/conversations/${current.id}/stream`);
  await sendMessage(parts.join("\n"));
}

async function onDeleteConversation() {
  if (!confirm("Supprimer cette conversation ? Le dossier et ses documents ne seront pas affectés.")) return;
  // Ne supprime que la conversation : le dossier reste ouvert, on en
  // recrée aussitôt une nouvelle (vide) pour pouvoir continuer à échanger.
  await deleteConversation();
  await ensureConversation();
  refreshSidebarConversations();
}
</script>

<template>
  <div v-if="dossier" class="dossier-detail">
    <RouterLink to="/dossiers" class="fr-link fr-icon-arrow-left-line fr-link--icon-left dossier-detail__back">
      Retour aux dossiers
    </RouterLink>

    <div class="dossier-detail__header">
      <div>
        <div class="dossier-detail__title">
          <h1 class="fr-h2">{{ dossier.name }}</h1>
          <button
            type="button"
            class="dossier-detail__icon-button"
            aria-label="Voir le détail du dossier"
            title="Voir le détail du dossier"
            @click="isDetailsModalOpened = true"
          >
            <VIcon name="ri-information-line" />
          </button>
        </div>
        <p class="fr-text--sm">
          Analyse : <RouterLink :to="`/analyses/${dossier.analyseId}`">{{ analyse?.name ?? "introuvable" }}</RouterLink>
          · Version {{ dossier.analyseVersion }}
        </p>
      </div>
      <div class="dossier-detail__header-actions">
        <DsfrSelect
          :model-value="conversation?.model ?? ''"
          label="Modèle"
          hide-label
          :options="modelOptions"
          class="dossier-detail__model-select"
          @update:model-value="onModelChange"
        />
        <DsfrBadge :label="DOSSIER_STATUS_LABELS[dossier.status]" :type="statusBadgeType[dossier.status]" />
        <button
          type="button"
          class="dossier-detail__icon-button"
          aria-label="Supprimer cette conversation"
          title="Supprimer cette conversation"
          @click="onDeleteConversation"
        >
          <VIcon name="ri-delete-bin-line" />
        </button>
      </div>
    </div>

    <DossierDocuments
      :documents="dossier.documents"
      show-summary-actions
      @regenerate-summary="regenerateDocumentSummary(dossierId, $event)"
    />

    <DossierResults :dossier="dossier" :analyse="analyse" @regenerate-summary="regenerateDossierSummary(dossierId)" />

    <ChatWindow
      :messages="messages"
      :stream-events="chatEvents"
      :is-running="isChatRunning"
      intro-title="Alimenter l'analyse"
      intro-text="Ajoutez un document, une image ou une note pour compléter ce dossier. Les résultats de l'analyse s'affichent ci-dessus."
      placeholder="Alimentez l'analyse avec un message ou un document..."
      show-file-attach
      @submit="onChatSubmit"
      @attach-files="onAttachFiles"
    >
      <template #message-actions="{ message }">
        <button
          type="button"
          class="chat-message__feedback-button"
          :class="{ 'chat-message__feedback-button--active': message.feedback?.value === 'up' }"
          aria-label="Bonne réponse"
          title="Bonne réponse"
          @click="thumbUp(message.id)"
        >
          <VIcon name="ri-thumb-up-line" />
        </button>
        <button
          type="button"
          class="chat-message__feedback-button"
          :class="{ 'chat-message__feedback-button--active': message.feedback?.value === 'down' }"
          aria-label="Mauvaise réponse"
          title="Mauvaise réponse"
          @click="thumbDown(message.id)"
        >
          <VIcon name="ri-thumb-down-line" />
        </button>
      </template>

      <template #composer-extra>
        <ul v-if="pendingFiles.length > 0" class="chat-window__chips">
          <li v-for="(file, index) in pendingFiles" :key="`${file.name}-${index}`" class="chat-window__chip">
            <VIcon name="ri-file-line" />
            <span>{{ file.name }}</span>
            <button type="button" aria-label="Retirer ce fichier" @click="removePendingFile(index)">
              <VIcon name="ri-close-line" />
            </button>
          </li>
        </ul>
      </template>
    </ChatWindow>

    <DsfrModal
      :opened="isDetailsModalOpened"
      @close="isDetailsModalOpened = false"
      title="Détail du dossier"
      icon="ri-folder-info-line"
      size="lg"
    >
      <dl class="dossier-details-modal__info">
        <div class="dossier-details-modal__row">
          <dt class="fr-text--sm">Nom</dt>
          <dd>{{ dossier.name }}</dd>
        </div>
        <div class="dossier-details-modal__row">
          <dt class="fr-text--sm">Statut</dt>
          <dd>
            <DsfrBadge :label="DOSSIER_STATUS_LABELS[dossier.status]" :type="statusBadgeType[dossier.status]" small />
          </dd>
        </div>
        <div class="dossier-details-modal__row">
          <dt class="fr-text--sm">Créé le</dt>
          <dd>{{ formatDateTime(dossier.createdAt) }}</dd>
        </div>
        <div class="dossier-details-modal__row">
          <dt class="fr-text--sm">Lancé le</dt>
          <dd>{{ formatDateTime(dossier.startedAt) }}</dd>
        </div>
        <div class="dossier-details-modal__row">
          <dt class="fr-text--sm">Terminé le</dt>
          <dd>{{ formatDateTime(dossier.endedAt) }}</dd>
        </div>
        <div class="dossier-details-modal__row">
          <dt class="fr-text--sm">Analyse</dt>
          <dd>
            <RouterLink :to="`/analyses/${dossier.analyseId}`" class="fr-link" @click="isDetailsModalOpened = false">
              {{ analyse?.name ?? "introuvable" }}
            </RouterLink>
            · Version {{ dossier.analyseVersion }}
          </dd>
        </div>
      </dl>

      <p v-if="dossier.documents.length === 0" class="fr-text--sm dossier-details-modal__no-files">
        Aucun fichier pour l'instant.
      </p>
      <DossierDocuments v-else :documents="dossier.documents" />
    </DsfrModal>

    <FeedbackReasonsModal v-model:opened="feedbackReasonsModalOpened" @submit="submitDownFeedback" />
  </div>
  <div v-else>
    <p>Dossier introuvable.</p>
    <RouterLink to="/dossiers" class="fr-link">Retour aux dossiers</RouterLink>
  </div>
</template>

<style scoped>
.dossier-detail {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 8rem);
}

.dossier-detail__back {
  display: inline-flex;
  margin-bottom: 1.5rem;
  flex-shrink: 0;
}

.dossier-detail__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-shrink: 0;
}

.dossier-detail__title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.dossier-detail__title .fr-h2 {
  margin-bottom: 0;
}

.dossier-detail__header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.dossier-detail__model-select {
  min-width: 10rem;
}

.dossier-detail__model-select :deep(.fr-select-group) {
  margin: 0;
}

.dossier-detail__icon-button {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: 1px solid var(--border-default-grey);
  border-radius: 50%;
  background: var(--background-default-grey);
  color: var(--text-default-grey);
  cursor: pointer;
}

.dossier-detail__icon-button:hover {
  background: var(--background-alt-grey-hover);
}

/* Chips de fichiers en attente (rendues dans le slot composer-extra de
   ChatWindow — les autres styles chat-* sont dans ChatWindow.vue). */
.chat-window__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
  list-style: none;
  margin: 0 0 0.5rem;
  padding: 0;
}

.chat-window__chip {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.5rem;
  border-radius: 1rem;
  border: 1px solid var(--border-action-high-blue-france);
  background: var(--background-alt-blue-france);
  color: var(--text-action-high-blue-france);
  font-size: 0.75rem;
}

.chat-window__chip button {
  display: flex;
  align-items: center;
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  padding: 0;
}

.dossier-details-modal__info {
  margin: 0 0 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.dossier-details-modal__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
  padding-bottom: 0.625rem;
  border-bottom: 1px solid var(--border-default-grey);
}

.dossier-details-modal__row dt {
  color: var(--text-mention-grey);
  flex-shrink: 0;
}

.dossier-details-modal__row dd {
  margin: 0;
  text-align: right;
}

.dossier-details-modal__no-files {
  color: var(--text-mention-grey);
}
</style>
