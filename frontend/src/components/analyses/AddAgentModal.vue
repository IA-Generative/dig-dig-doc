<script setup lang="ts">
import { ref, watch } from "vue";

import LlmAssistButton from "@/components/analyses/LlmAssistButton.vue";
import { useAnalyses } from "@/composables/useAnalyses";
import { suggestAgentPrompt } from "@/composables/useLlmAssist";
import { AGENT_TOOL_LABELS, type AgentTool } from "@/types/analyse";

const props = defineProps<{ analyseId: string }>();
const opened = defineModel<boolean>("opened", { default: false });
const emit = defineEmits<{ created: [] }>();

const { addAgent } = useAnalyses();

const toolOptions = (Object.keys(AGENT_TOOL_LABELS) as AgentTool[]).map((tool) => ({
  name: tool,
  value: tool,
  label: AGENT_TOOL_LABELS[tool],
}));

const name = ref("");
const prompt = ref("");
const tools = ref<AgentTool[]>([]);

watch(opened, (isOpened) => {
  if (isOpened) {
    name.value = "";
    prompt.value = "";
    tools.value = [];
  }
});

function applySuggestion() {
  prompt.value = suggestAgentPrompt();
}

function submit() {
  if (!name.value.trim() || !prompt.value.trim()) return;
  addAgent(props.analyseId, name.value.trim(), prompt.value.trim(), tools.value);
  opened.value = false;
  emit("created");
}
</script>

<template>
  <DsfrModal
    v-model:opened="opened"
    title="Créer un agent"
    size="lg"
    :actions="[
      { label: 'Annuler', secondary: true, onClick: () => (opened = false) },
      { label: 'Créer', onClick: submit },
    ]"
  >
    <p class="fr-text--sm">
      Un agent réalise une tâche métier propre à cette analyse (contrôle de cohérence, rédaction d'une synthèse,
      construction d'une timeline...), à la différence de la classification et de l'extraction d'entités qui sont
      des analyses systématiques.
    </p>
    <DsfrInput v-model="name" label="Nom de l'agent" label-visible required />
    <DsfrInput v-model="prompt" label="Prompt" label-visible is-textarea required class="fr-mt-2w" />
    <LlmAssistButton label="Aide à la rédaction du prompt" class="fr-mt-2w" @click="applySuggestion" />
    <DsfrCheckboxSet
      v-model="tools"
      legend="Outils disponibles"
      :options="toolOptions"
      inline
      small
      class="fr-mt-2w"
    />
  </DsfrModal>
</template>
