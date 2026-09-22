<script setup lang="ts">
import { ref, watch } from "vue";

import { useAnalyses } from "@/composables/useAnalyses";
import { suggestPrompt } from "@/composables/useLlmAssist";
import type { Agent } from "@/types/analyse";

const props = defineProps<{ analyseId: string; agent: Agent }>();

const { updateAgentPrompt } = useAnalyses();

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

function save() {
  updateAgentPrompt(props.analyseId, props.agent.id, draftPrompt.value);
}
</script>

<template>
  <div class="agent-prompt-editor">
    <DsfrInput
      v-model="draftPrompt"
      label="Prompt"
      label-visible
      is-textarea
      :hint="`Version actuelle. ${agent.promptVersions.length} version(s) précédente(s).`"
    />
    <div class="agent-prompt-editor__actions">
      <DsfrButton
        label="Aide à la rédaction du prompt"
        secondary
        icon="ri-magic-line"
        size="sm"
        @click="applySuggestion"
      />
      <DsfrButton label="Enregistrer" :disabled="!isDirty" size="sm" @click="save" />
    </div>
  </div>
</template>

<style scoped>
.agent-prompt-editor {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.agent-prompt-editor__actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}
</style>
