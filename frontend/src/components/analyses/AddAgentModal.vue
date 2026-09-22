<script setup lang="ts">
import { computed, ref, watch } from "vue";

import LlmAssistButton from "@/components/analyses/LlmAssistButton.vue";
import { useAnalyses } from "@/composables/useAnalyses";
import { suggestPrompt } from "@/composables/useLlmAssist";
import { AGENT_TOOL_LABELS, type AgentCapability, type AgentTool } from "@/types/analyse";

const props = defineProps<{ analyseId: string }>();
const opened = defineModel<boolean>("opened", { default: false });
const emit = defineEmits<{ created: [] }>();

const { addAgent } = useAnalyses();

const capabilities: AgentCapability[] = [
  "Classification documentaire",
  "Extraction d'entités nommées",
  "Contrôle de cohérence",
  "Agent généraliste",
];

const toolOptions = (Object.keys(AGENT_TOOL_LABELS) as AgentTool[]).map((tool) => ({
  name: tool,
  value: tool,
  label: AGENT_TOOL_LABELS[tool],
}));

const name = ref("");
const capability = ref<AgentCapability>(capabilities[0]);
const prompt = ref("");
const tools = ref<AgentTool[]>([]);

// Seul "Agent généraliste" est un vrai agent avec des outils : la
// classification, l'extraction d'entités et le contrôle de cohérence sont
// des analyses simples, appliquées systématiquement, pas des agents outillés.
const isRealAgent = computed(() => capability.value === "Agent généraliste");

watch(opened, (isOpened) => {
  if (isOpened) {
    name.value = "";
    capability.value = capabilities[0];
    prompt.value = "";
    tools.value = [];
  }
});

watch(isRealAgent, (value) => {
  if (!value) tools.value = [];
});

function applySuggestion() {
  prompt.value = suggestPrompt(capability.value);
}

function submit() {
  if (!name.value.trim() || !prompt.value.trim()) return;
  addAgent(props.analyseId, name.value.trim(), capability.value, prompt.value.trim(), tools.value);
  opened.value = false;
  emit("created");
}
</script>

<template>
  <DsfrModal
    v-model:opened="opened"
    title="Ajouter un agent"
    size="lg"
    :actions="[
      { label: 'Annuler', secondary: true, onClick: () => (opened = false) },
      { label: 'Ajouter', onClick: submit },
    ]"
  >
    <DsfrInput v-model="name" label="Nom de l'agent" label-visible required />
    <DsfrSelect v-model="capability" label="Capacité" class="fr-mt-2w" :options="capabilities" />
    <DsfrInput v-model="prompt" label="Prompt" label-visible is-textarea required class="fr-mt-2w" />
    <LlmAssistButton label="Aide à la rédaction du prompt" class="fr-mt-2w" @click="applySuggestion" />
    <DsfrCheckboxSet
      v-if="isRealAgent"
      v-model="tools"
      legend="Outils disponibles"
      :options="toolOptions"
      inline
      small
      class="fr-mt-2w"
    />
  </DsfrModal>
</template>
