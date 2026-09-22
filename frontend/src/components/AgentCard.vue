<script setup lang="ts">
import { ref, watch } from "vue";

import { suggestPrompt, useAnalyses } from "@/composables/useAnalyses";
import type { Agent } from "@/types/analyse";

const props = defineProps<{ analyseId: string; agent: Agent }>();

const { updateAgentPrompt, restoreAgentPromptVersion } = useAnalyses();

const draftPrompt = ref(props.agent.prompt);
const isDirty = ref(false);

watch(
  () => props.agent.prompt,
  (prompt) => {
    draftPrompt.value = prompt;
    isDirty.value = false;
  },
);

watch(draftPrompt, (value) => {
  isDirty.value = value !== props.agent.prompt;
});

function applySuggestion() {
  draftPrompt.value = suggestPrompt(props.agent.capability);
}

function savePrompt() {
  updateAgentPrompt(props.analyseId, props.agent.id, draftPrompt.value);
}

function restoreVersion(versionId: string) {
  restoreAgentPromptVersion(props.analyseId, props.agent.id, versionId);
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });
}
</script>

<template>
  <div class="agent-card">
    <div class="agent-card__header">
      <h3 class="fr-h5 agent-card__title">{{ agent.name }}</h3>
      <DsfrBadge :label="agent.capability" type="info" small />
    </div>

    <DsfrInput
      v-model="draftPrompt"
      label="Prompt"
      label-visible
      is-textarea
      :hint="`Version actuelle. ${agent.promptVersions.length} version(s) précédente(s).`"
    />

    <div class="agent-card__actions">
      <DsfrButton
        label="Aide à la rédaction du prompt"
        secondary
        icon="ri-magic-line"
        size="sm"
        @click="applySuggestion"
      />
      <DsfrButton label="Enregistrer" :disabled="!isDirty" size="sm" @click="savePrompt" />
    </div>

    <DsfrAccordion
      v-if="agent.promptVersions.length > 0"
      :title="`Historique des versions (${agent.promptVersions.length})`"
      class="agent-card__history"
    >
      <ul class="agent-card__version-list">
        <li v-for="version in agent.promptVersions" :key="version.id" class="agent-card__version">
          <div>
            <p class="fr-text--sm agent-card__version-date">{{ formatDate(version.createdAt) }}</p>
            <p class="fr-text--sm agent-card__version-content">{{ version.content }}</p>
          </div>
          <DsfrButton label="Restaurer" tertiary size="sm" @click="restoreVersion(version.id)" />
        </li>
      </ul>
    </DsfrAccordion>
  </div>
</template>

<style scoped>
.agent-card {
  border: 1px solid var(--border-default-grey);
  border-radius: 0.25rem;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.agent-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.agent-card__title {
  margin: 0;
}

.agent-card__actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.agent-card__version-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.agent-card__version {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  border-top: 1px solid var(--border-default-grey);
  padding-top: 1rem;
}

.agent-card__version-date {
  color: var(--text-mention-grey);
  margin: 0 0 0.25rem;
}

.agent-card__version-content {
  margin: 0;
}
</style>
