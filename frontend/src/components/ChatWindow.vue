<script setup lang="ts">
/**
 * Composant de chat réutilisable, extrait de DossierDetailPage.vue.
 *
 * Affiche une liste de messages génériques, les événements de streaming
 * (tool_call, tool_result, thinking, done, error) pendant l'exécution du
 * graphe LangGraph, et un composer (textarea auto-agrandissable + bouton
 * envoyer). Les actions spécifiques au contexte (feedback thumbs up/down,
 * attachement de fichiers, sélection de modèle) sont déléguées au parent
 * via des slots et des events.
 *
 * Props :
 * - `messages` : liste de messages génériques (role, content, sources).
 * - `streamEvents` : événements de streaming en cours (affichés sous forme
 *   de "pensée" de l'assistant).
 * - `isRunning` : vrai pendant l'exécution (désactive le composer).
 * - `introTitle` / `introText` : texte affiché quand la liste est vide.
 * - `placeholder` : placeholder du textarea.
 * - `showFileAttach` : affiche le bouton d'attachement de fichiers (dossier).
 *
 * Slots :
 * - `message-actions` : actions par message (ex: feedback), reçoit
 *   `{ message }` en slot props.
 * - `source` : rendu personnalisé d'une source, reçoit `{ source }`.
 * - `composer-extra` : contenu supplémentaire avant le composer (ex: chips
 *   de fichiers en attente).
 *
 * Events :
 * - `submit` : émis avec le texte saisi quand l'utilisateur envoie.
 * - `attach-files` : émis avec les fichiers sélectionnés (si showFileAttach).
 */
import { nextTick, ref, watch } from "vue";

import MarkdownText from "@/components/MarkdownText.vue";
import type { StreamEvent } from "@/composables/useChatStream";

export interface ChatWindowMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: ChatWindowSource[];
  /** Feedback optionnel (thumbs up/down), utilisé par le chat de dossier. */
  feedback?: { value: "up" | "down" } | null;
}

export interface ChatWindowSource {
  id: string;
  excerpt?: string | null;
  pages?: { id: string; pageNumber: number }[];
}

const props = withDefaults(
  defineProps<{
    messages: ChatWindowMessage[];
    streamEvents?: StreamEvent[];
    isRunning?: boolean;
    introTitle?: string;
    introText?: string;
    placeholder?: string;
    showFileAttach?: boolean;
  }>(),
  {
    streamEvents: () => [],
    isRunning: false,
    introTitle: "Démarrez une conversation",
    introText: "",
    placeholder: "Écrivez votre message...",
    showFileAttach: false,
  },
);

const emit = defineEmits<{
  submit: [content: string];
  "attach-files": [files: File[]];
}>();

const draft = ref("");
const textareaRef = ref<HTMLTextAreaElement | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);
const messagesEndRef = ref<HTMLElement | null>(null);

watch(
  () => props.messages,
  () => {
    nextTick(() => messagesEndRef.value?.scrollIntoView({ behavior: "smooth" }));
  },
  { deep: true },
);
watch(
  () => props.streamEvents,
  () => {
    nextTick(() => messagesEndRef.value?.scrollIntoView({ behavior: "smooth" }));
  },
  { deep: true },
);

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
  if (target.files) {
    emit("attach-files", Array.from(target.files));
  }
  target.value = "";
}

function submit() {
  const content = draft.value.trim();
  if (!content || props.isRunning) return;
  emit("submit", content);
  draft.value = "";
  nextTick(resizeTextarea);
}

defineExpose({ resizeTextarea });
</script>

<template>
  <section class="chat-window">
    <div v-if="messages.length === 0" class="chat-window__intro">
      <h2>{{ introTitle }}</h2>
      <p v-if="introText" class="fr-text--sm">{{ introText }}</p>
    </div>

    <div v-else class="chat-window__messages">
      <div class="chat-window__inner">
        <div
          v-for="message in messages"
          :key="message.id"
          class="chat-message"
          :class="{ 'chat-message--assistant': message.role === 'assistant' }"
        >
          <div class="chat-message__bubble">
            <MarkdownText :content="message.content" class="chat-message__text" />
            <!-- Sources citées par l'assistant -->
            <div v-if="message.sources && message.sources.length > 0" class="chat-message__sources">
              <p class="chat-message__sources-title">Sources :</p>
              <ul>
                <li v-for="source in message.sources" :key="source.id" class="chat-message__source">
                  <slot name="source" :source="source">
                    <span v-if="source.pages && source.pages.length > 0" class="chat-message__source-pages">
                      {{ source.pages.map((p) => `p. ${p.pageNumber}`).join(", ") }}
                    </span>
                    <span v-if="source.excerpt" class="chat-message__source-excerpt">« {{ source.excerpt }} »</span>
                  </slot>
                </li>
              </ul>
            </div>
          </div>
          <div v-if="message.role === 'assistant'" class="chat-message__feedback">
            <slot name="message-actions" :message="message" />
          </div>
        </div>

        <!-- Streaming en cours : événements du graphe LangGraph -->
        <div v-if="isRunning" class="chat-message chat-message--assistant chat-message--streaming">
          <div class="chat-message__bubble">
            <div v-for="event in streamEvents" :key="event.kind + JSON.stringify(event.data)" class="chat-message__event">
              <VIcon
                :name="
                  event.kind === 'tool_call'
                    ? 'ri-tools-line'
                    : event.kind === 'tool_result'
                      ? 'ri-check-line'
                      : event.kind === 'error'
                        ? 'ri-error-warning-line'
                        : 'ri-loader-4-line'
                "
              />
              <span>{{ event.data?.label || event.data?.tool || event.kind }}</span>
            </div>
            <div v-if="streamEvents.length === 0" class="chat-message__event chat-message__event--pending">
              <VIcon name="ri-loader-4-line" class="spin" />
              <span>Réflexion en cours…</span>
            </div>
          </div>
        </div>

        <div ref="messagesEndRef" />
      </div>
    </div>

    <form class="chat-window__form" @submit.prevent="submit">
      <div class="chat-window__inner">
        <slot name="composer-extra" />

        <div class="chat-window__composer">
          <input
            v-if="showFileAttach"
            ref="fileInputRef"
            type="file"
            multiple
            accept=".pdf,image/*"
            class="chat-window__file-input"
            aria-label="Choisir des documents à joindre"
            @change="onFilesSelected"
          />
          <button
            v-if="showFileAttach"
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
            :placeholder="placeholder"
            aria-label="Message"
            rows="1"
            :disabled="isRunning"
            @input="resizeTextarea"
            @keydown.enter.exact.prevent="submit"
          />
          <button
            type="submit"
            class="chat-window__send"
            :disabled="isRunning || !draft.trim()"
            aria-label="Envoyer"
          >
            <VIcon name="ri-arrow-up-line" />
          </button>
        </div>
      </div>
    </form>
  </section>
</template>

<style scoped>
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

/* Messages assistant : alignés à gauche, bulle neutre */
.chat-message--assistant {
  align-items: flex-start;
}

.chat-message--assistant .chat-message__bubble {
  background: var(--background-contrast-grey);
  border-top-left-radius: 0.25rem;
}

/* Sources citées par l'assistant */
.chat-message__sources {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border-default-grey);
}

.chat-message__sources-title {
  margin: 0 0 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-mention-grey);
}

.chat-message__sources ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

.chat-message__source {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0.25rem 0;
  font-size: 0.8rem;
  color: var(--text-mention-grey);
}

.chat-message__source-pages {
  font-weight: 500;
  color: var(--text-default-grey);
}

.chat-message__source-excerpt {
  font-style: italic;
  color: var(--text-mention-grey);
}

/* Streaming en cours */
.chat-message--streaming .chat-message__bubble {
  opacity: 0.85;
}

.chat-message__event {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0;
  font-size: 0.8rem;
  color: var(--text-mention-grey);
}

.chat-message__event--pending {
  font-style: italic;
}

.chat-message__event .spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
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
