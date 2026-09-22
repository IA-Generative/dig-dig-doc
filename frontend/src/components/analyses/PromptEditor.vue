<script setup lang="ts">
import { ref, watch } from "vue";

import LlmAssistButton from "@/components/analyses/LlmAssistButton.vue";
import VersionHistory from "@/components/analyses/VersionHistory.vue";
import type { PromptVersion } from "@/types/analyse";

const props = withDefaults(
  defineProps<{
    prompt: string;
    versions: PromptVersion[];
    suggestPrompt?: () => string;
    suggestLabel?: string;
  }>(),
  { suggestLabel: "Aide à la rédaction du prompt" },
);

const emit = defineEmits<{ save: [string]; restore: [string] }>();

const draft = ref(props.prompt);
const isDirty = ref(false);

watch(
  () => props.prompt,
  (prompt) => {
    draft.value = prompt;
    isDirty.value = false;
  },
);

watch(draft, (value) => {
  isDirty.value = value !== props.prompt;
});

function applySuggestion() {
  if (props.suggestPrompt) draft.value = props.suggestPrompt();
}

function save() {
  emit("save", draft.value);
}

function formatVersionContent(content: string) {
  return content;
}
</script>

<template>
  <div class="prompt-editor">
    <DsfrInput
      v-model="draft"
      label="Prompt"
      label-visible
      is-textarea
      :hint="`Version actuelle. ${versions.length} version(s) précédente(s).`"
    />
    <div class="prompt-editor__actions">
      <LlmAssistButton v-if="suggestPrompt" :label="suggestLabel" @click="applySuggestion" />
      <DsfrButton label="Enregistrer" :disabled="!isDirty" size="sm" @click="save" />
    </div>

    <VersionHistory :versions="versions" :format-content="formatVersionContent" @restore="emit('restore', $event)" />
  </div>
</template>

<style scoped>
.prompt-editor {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.prompt-editor__actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}
</style>
