<script setup lang="ts">
import { ref, watch } from "vue";

import { useAnalyses } from "@/composables/useAnalyses";
import { AGENT_TOOL_LABELS, type Agent, type AgentTool } from "@/types/analyse";

const props = defineProps<{ analyseId: string; agent: Agent }>();

const { updateAgentTools } = useAnalyses();

const toolOptions = (Object.keys(AGENT_TOOL_LABELS) as AgentTool[]).map((tool) => ({
  name: tool,
  value: tool,
  label: AGENT_TOOL_LABELS[tool],
}));

const draftTools = ref<AgentTool[]>([...props.agent.tools]);
const isDirty = ref(false);

watch(
  () => props.agent.tools,
  (tools) => {
    draftTools.value = [...tools];
    isDirty.value = false;
  },
);

watch(
  draftTools,
  (tools) => {
    isDirty.value = JSON.stringify([...tools].sort()) !== JSON.stringify([...props.agent.tools].sort());
  },
  { deep: true },
);

function save() {
  updateAgentTools(props.analyseId, props.agent.id, draftTools.value);
}
</script>

<template>
  <div class="agent-tools-editor">
    <DsfrCheckboxSet
      v-model="draftTools"
      legend="Outils disponibles"
      :options="toolOptions"
      inline
      small
    />
    <DsfrButton label="Enregistrer" :disabled="!isDirty" size="sm" @click="save" />
  </div>
</template>

<style scoped>
.agent-tools-editor {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.75rem;
}
</style>
