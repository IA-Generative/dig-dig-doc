<script setup lang="ts">
import { ref, watch } from "vue";

import LlmAssistButton from "@/components/analyses/LlmAssistButton.vue";
import { useAnalyses } from "@/composables/useAnalyses";
import { suggestPrompt } from "@/composables/useLlmAssist";
import type { AgentCapability } from "@/types/analyse";

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

const name = ref("");
const capability = ref<AgentCapability>(capabilities[0]);
const prompt = ref("");

watch(opened, (isOpened) => {
  if (isOpened) {
    name.value = "";
    capability.value = capabilities[0];
    prompt.value = "";
  }
});

function applySuggestion() {
  prompt.value = suggestPrompt(capability.value);
}

function submit() {
  if (!name.value.trim() || !prompt.value.trim()) return;
  addAgent(props.analyseId, name.value.trim(), capability.value, prompt.value.trim());
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
  </DsfrModal>
</template>
