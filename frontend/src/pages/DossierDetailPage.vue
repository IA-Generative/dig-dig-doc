<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { useAnalyses } from "@/composables/useAnalyses";
import { useDossiers } from "@/composables/useDossiers";
import { DOSSIER_STATUS_LABELS, type DossierStatus } from "@/types/dossier";

interface FeedMessage {
  id: string;
  role: "user" | "system";
  sender: string;
  content: string;
  timestamp: string;
}

const route = useRoute();
const { list: dossiers, addDocuments } = useDossiers();
const { getById: getAnalyseById } = useAnalyses();

const dossier = computed(() => dossiers.value.find((d) => d.id === String(route.params.id)));
const analyse = computed(() => (dossier.value ? getAnalyseById(dossier.value.analyseId) : undefined));

const statusBadgeType: Record<DossierStatus, "new" | "info" | "success" | "warning" | "error"> = {
  en_attente: "new",
  en_cours: "info",
  terminé: "success",
  arrêté: "warning",
  échec: "error",
};

const classificationStep = computed(() => dossier.value?.executionSteps.find((s) => s.kind === "classification"));
const detectedLabelName = computed(() => classificationStep.value?.output?.split(" (")[0]);

// Fil de discussion : les résultats produits par l'exécution (côté "système",
// aligné à gauche, sans bulle - comme les réponses de l'assistant sur
// Muffin) et les messages ajoutés localement en alimentant l'analyse (côté
// "vous", bulle grise alignée à droite).
const localMessages = ref<FeedMessage[]>([]);

const messages = computed<FeedMessage[]>(() => {
  const stepMessages: FeedMessage[] = (dossier.value?.executionSteps ?? [])
    .filter((s) => !!s.output)
    .map((s) => ({
      id: s.id,
      role: "system",
      sender: s.label,
      content: s.output!,
      timestamp: s.endedAt ?? s.startedAt,
    }));
  return [...stepMessages, ...localMessages.value].sort((a, b) => a.timestamp.localeCompare(b.timestamp));
});

const messagesEndRef = ref<HTMLElement | null>(null);
watch(messages, () => {
  nextTick(() => messagesEndRef.value?.scrollIntoView({ behavior: "smooth" }));
});

const draft = ref("");
const pendingFiles = ref<File[]>([]);
const textareaRef = ref<HTMLTextAreaElement | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);

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

function submit() {
  if (!dossier.value) return;
  const content = draft.value.trim();
  if (!content && pendingFiles.value.length === 0) return;

  if (pendingFiles.value.length > 0) {
    addDocuments(dossier.value.id, pendingFiles.value);
  }

  const parts = [
    ...(pendingFiles.value.length > 0
      ? [`Document(s) ajouté(s) à l'analyse : ${pendingFiles.value.map((f) => f.name).join(", ")}`]
      : []),
    ...(content ? [content] : []),
  ];

  localMessages.value.push({
    id: `feed-${Date.now()}`,
    role: "user",
    sender: "Vous",
    content: parts.join("\n"),
    timestamp: new Date().toISOString(),
  });

  draft.value = "";
  pendingFiles.value = [];
  nextTick(resizeTextarea);
}
</script>

<template>
  <div v-if="dossier" class="dossier-detail">
    <RouterLink to="/dossiers" class="fr-link fr-icon-arrow-left-line fr-link--icon-left dossier-detail__back">
      Retour aux dossiers
    </RouterLink>

    <div class="dossier-detail__header">
      <div>
        <h1 class="fr-h2">{{ dossier.name }}</h1>
        <p class="fr-text--sm">
          Analyse : <RouterLink :to="`/analyses/${dossier.analyseId}`">{{ analyse?.name ?? "introuvable" }}</RouterLink>
          · Version {{ dossier.analyseVersion }}
        </p>
      </div>
      <DsfrBadge :label="DOSSIER_STATUS_LABELS[dossier.status]" :type="statusBadgeType[dossier.status]" />
    </div>

    <div v-if="analyse" class="dossier-detail__tags">
      <div class="dossier-detail__tags-group">
        <span class="fr-text--sm dossier-detail__tags-label">Classification</span>
        <span v-if="analyse.classification.labels.length === 0" class="fr-text--sm">Aucun label configuré.</span>
        <DsfrTag
          v-for="label in analyse.classification.labels"
          :key="label.id"
          :label="label.name"
          :icon="label.name === detectedLabelName ? 'ri-check-line' : undefined"
          :link="`/analyses/${dossier.analyseId}`"
          small
        />
      </div>
      <div class="dossier-detail__tags-group">
        <span class="fr-text--sm dossier-detail__tags-label">Entités</span>
        <span v-if="analyse.extraction.entities.length === 0" class="fr-text--sm">Aucune entité configurée.</span>
        <DsfrTag
          v-for="entity in analyse.extraction.entities"
          :key="entity.id"
          :label="entity.name"
          :link="`/analyses/${dossier.analyseId}`"
          small
        />
      </div>
    </div>

    <section class="chat-window">
      <div v-if="messages.length === 0" class="chat-window__intro">
        <h2>En attente des résultats</h2>
        <p class="fr-text--sm">
          Les résultats de la classification, de l'extraction et des agents apparaîtront ici dès que l'analyse aura
          tourné. Vous pouvez déjà alimenter l'analyse avec un document ou une note ci-dessous.
        </p>
      </div>

      <div v-else class="chat-window__messages">
        <div class="chat-window__inner">
          <div
            v-for="message in messages"
            :key="message.id"
            class="chat-message"
            :class="`chat-message--${message.role}`"
          >
            <div class="chat-message__bubble">
              <span v-if="message.role === 'system'" class="chat-message__sender">{{ message.sender }}</span>
              <p class="chat-message__text">{{ message.content }}</p>
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
  height: calc(100vh - 8rem);
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

.dossier-detail__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 2rem;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-default-grey);
  flex-shrink: 0;
}

.dossier-detail__tags-group {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.dossier-detail__tags-label {
  font-weight: bold;
  margin-right: 0.25rem;
}

/* Style repris de Muffin (frontend/src/components/ChatWindow.vue et
   ChatMessage.vue) : colonne centrée, messages "système" à gauche sans
   bulle, messages "vous" en bulle grise à droite, composer en pilule
   arrondie avec textarea auto-agrandissante. */
.chat-window {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.chat-window__inner {
  max-width: 48rem;
  margin: 0 auto;
  padding: 0 0.5rem;
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
  padding: 0.5rem 0;
}

.chat-message--system {
  justify-content: flex-start;
}

.chat-message--user {
  justify-content: flex-end;
}

.chat-message--user .chat-message__bubble {
  max-width: 75%;
  padding: 0.75rem 1.125rem;
  border-radius: 1.25rem;
  background: var(--background-alt-grey);
}

.chat-message--system .chat-message__bubble {
  max-width: 100%;
}

.chat-message__sender {
  display: block;
  font-size: 0.8125rem;
  font-weight: bold;
  margin-bottom: 0.25rem;
  color: var(--text-mention-grey);
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
</style>
