<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import DossierDocuments from "@/components/dossiers/DossierDocuments.vue";
import DossierResults from "@/components/dossiers/DossierResults.vue";
import FeedbackReasonsModal from "@/components/dossiers/FeedbackReasonsModal.vue";
import { useAnalyses } from "@/composables/useAnalyses";
import { useConversations } from "@/composables/useConversations";
import { useDossiers } from "@/composables/useDossiers";
import { useModels } from "@/composables/useModels";
import { useMyConversations } from "@/composables/useMyConversations";
import type { FeedbackReasonCode } from "@/types/conversation";
import { DOSSIER_STATUS_LABELS, type DossierStatus } from "@/types/dossier";

const route = useRoute();
const dossierId = String(route.params.id);
const { list: dossiers, addDocuments, fetchDossier, streamDossier } = useDossiers();
const { getById: getAnalyseById, fetchAnalyse } = useAnalyses();
const { conversation, ensureConversation, sendMessage, deleteConversation, setModel, setFeedback, removeFeedback } =
  useConversations(dossierId);
const { fetchList: refreshSidebarConversations } = useMyConversations();
const { models, fetchModels } = useModels();

// Pouce haut : bascule directement. Pouce bas : ouvre une modale pour
// recueillir la/les raison(s) avant d'envoyer (comme Muffin).
const feedbackReasonsModalOpened = ref(false);
const pendingDownMessageId = ref<string | null>(null);

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

const messagesEndRef = ref<HTMLElement | null>(null);
watch(messages, () => {
  nextTick(() => messagesEndRef.value?.scrollIntoView({ behavior: "smooth" }));
});

const draft = ref("");
const pendingFiles = ref<File[]>([]);
const textareaRef = ref<HTMLTextAreaElement | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);
const isDetailsModalOpened = ref(false);

function formatDateTime(iso?: string) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

function resizeTextarea() {
  const el = textareaRef.value;
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
}

function openFilePicker() {
  fileInputRef.value?.click();
}

function onFilesSelected(event: Event) {
  const target = event.target as HTMLInputElement;
  if (target.files) pendingFiles.value.push(...Array.from(target.files));
  target.value = "";
}

function removePendingFile(index: number) {
  pendingFiles.value.splice(index, 1);
}

async function submit() {
  if (!dossier.value) return;
  const content = draft.value.trim();
  if (!content && pendingFiles.value.length === 0) return;

  if (pendingFiles.value.length > 0) {
    await addDocuments(dossier.value.id, pendingFiles.value);
  }

  const parts = [
    ...(pendingFiles.value.length > 0
      ? [`Document(s) ajouté(s) à l'analyse : ${pendingFiles.value.map((f) => f.name).join(", ")}`]
      : []),
    ...(content ? [content] : []),
  ];

  draft.value = "";
  pendingFiles.value = [];
  nextTick(resizeTextarea);

  await sendMessage(parts.join("\n"));
  // Le libellé/l'horodatage affichés dans la sidebar viennent de changer.
  refreshSidebarConversations();
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

    <DossierDocuments :documents="dossier.documents" />

    <DossierResults :dossier="dossier" :analyse="analyse" />

    <section class="chat-window">
      <div v-if="messages.length === 0" class="chat-window__intro">
        <h2>Alimenter l'analyse</h2>
        <p class="fr-text--sm">
          Ajoutez un document, une image ou une note pour compléter ce dossier. Les résultats de l'analyse
          s'affichent ci-dessus.
        </p>
      </div>

      <div v-else class="chat-window__messages">
        <div class="chat-window__inner">
          <div v-for="message in messages" :key="message.id" class="chat-message">
            <div class="chat-message__bubble">
              <p class="chat-message__text">{{ message.content }}</p>
            </div>
            <div class="chat-message__feedback">
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
            </div>
          </div>
          <div ref="messagesEndRef" />
        </div>
      </div>

      <form class="chat-window__form" @submit.prevent="submit">
        <div class="chat-window__inner">
          <ul v-if="pendingFiles.length > 0" class="chat-window__chips">
            <li v-for="(file, index) in pendingFiles" :key="`${file.name}-${index}`" class="chat-window__chip">
              <VIcon name="ri-file-line" />
              <span>{{ file.name }}</span>
              <button type="button" aria-label="Retirer ce fichier" @click="removePendingFile(index)">
                <VIcon name="ri-close-line" />
              </button>
            </li>
          </ul>

          <div class="chat-window__composer">
            <input
              ref="fileInputRef"
              type="file"
              multiple
              accept=".pdf,image/*"
              class="chat-window__file-input"
              aria-label="Choisir des documents à ajouter à l'analyse"
              @change="onFilesSelected"
            />
            <button
              type="button"
              class="chat-window__attach"
              aria-label="Joindre un document"
              title="Joindre un document"
              @click="openFilePicker"
            >
              <VIcon name="ri-attachment-2" />
            </button>
            <textarea
              ref="textareaRef"
              v-model="draft"
              class="chat-window__textarea"
              placeholder="Alimentez l'analyse avec un message ou un document..."
              rows="1"
              @input="resizeTextarea"
              @keydown.enter.exact.prevent="submit"
            />
            <button
              type="submit"
              class="chat-window__send"
              :disabled="!draft.trim() && pendingFiles.length === 0"
              aria-label="Envoyer"
            >
              <VIcon name="ri-arrow-up-line" />
            </button>
          </div>
        </div>
      </form>
    </section>

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

/* Style repris de Muffin (frontend/src/components/ChatWindow.vue et
   ChatMessage.vue) : colonne centrée, bulle grise arrondie à droite,
   composer en pilule arrondie avec textarea auto-agrandissante. */
.chat-window {
  flex: 1;
  min-height: 16rem;
  display: flex;
  flex-direction: column;
}

.chat-window__inner {
  max-width: 48rem;
  margin: 0 auto;
  padding: 0 0.5rem;
  width: 100%;
}

.chat-window__intro {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 0.5rem;
  padding: 0 1.5rem;
  color: var(--text-mention-grey);
}

.chat-window__intro h2 {
  margin: 0;
  color: var(--text-default-grey);
}

.chat-window__intro p {
  max-width: 28rem;
}

.chat-window__messages {
  flex: 1;
  overflow-y: auto;
  padding-top: 1rem;
}

.chat-message {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  padding: 0.5rem 0;
}

.chat-message__bubble {
  max-width: 75%;
  padding: 0.75rem 1.125rem;
  border-radius: 1.25rem;
  background: var(--background-alt-grey);
}

.chat-message__feedback {
  display: flex;
  gap: 0.25rem;
  margin-top: 0.25rem;
}

.chat-message__feedback-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--text-mention-grey);
  cursor: pointer;
  font-size: 0.9rem;
}

.chat-message__feedback-button:hover {
  background: var(--background-alt-grey-hover);
  color: var(--text-default-grey);
}

.chat-message__feedback-button--active {
  color: var(--text-active-blue-france);
  background: var(--background-action-low-blue-france);
}

.chat-message__text {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.6;
}

.chat-window__form {
  padding: 0.5rem 0 0;
  flex-shrink: 0;
}

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

.chat-window__composer {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
  padding: 0.625rem 0.625rem 0.625rem 1.125rem;
  border-radius: 1.5rem;
  border: 1px solid var(--border-default-grey);
  background: var(--background-default-grey);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.chat-window__textarea {
  flex: 1;
  resize: none;
  border: none;
  background: transparent;
  color: var(--text-default-grey);
  font: inherit;
  line-height: 1.5;
  max-height: 200px;
  padding: 0.375rem 0;
}

.chat-window__textarea:focus {
  outline: none;
}

.chat-window__file-input {
  display: none;
}

.chat-window__attach,
.chat-window__send {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border: none;
  border-radius: 50%;
  cursor: pointer;
}

.chat-window__attach {
  background: transparent;
  color: var(--text-mention-grey);
}

.chat-window__attach:hover {
  background: var(--background-alt-grey-hover);
  color: var(--text-default-grey);
}

.chat-window__send {
  background: var(--background-action-high-blue-france);
  color: var(--text-inverted-blue-france);
}

.chat-window__send:disabled {
  background: var(--background-disabled-grey);
  color: var(--text-disabled-grey);
  cursor: not-allowed;
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
