<script setup lang="ts">
import { computed } from "vue";

import AgentPromptEditor from "@/components/analyses/AgentPromptEditor.vue";
import AgentVersionHistory from "@/components/analyses/AgentVersionHistory.vue";
import EntitiesEditor from "@/components/analyses/EntitiesEditor.vue";
import LabelsEditor from "@/components/analyses/LabelsEditor.vue";
import type { Agent, AgentCapability } from "@/types/analyse";

const props = defineProps<{ analyseId: string; agent: Agent }>();

const NER_CAPABILITY: AgentCapability = "Extraction d'entités nommées";
const isNerAgent = computed(() => props.agent.capability === NER_CAPABILITY);
</script>

<template>
  <div class="agent-card">
    <div class="agent-card__header">
      <h3 class="fr-h5 agent-card__title">{{ agent.name }}</h3>
      <DsfrBadge :label="agent.capability" type="info" small />
    </div>

    <AgentPromptEditor :analyse-id="analyseId" :agent="agent" />

    <LabelsEditor v-if="agent.capability === 'Classification documentaire'" :analyse-id="analyseId" :agent="agent" />
    <EntitiesEditor v-if="isNerAgent" :analyse-id="analyseId" :agent="agent" />

    <AgentVersionHistory :analyse-id="analyseId" :agent="agent" />
  </div>
</template>

<style scoped>
.agent-card {
  border: 1px solid var(--border-default-grey);
  border-radius: 0.25rem;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
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
</style>
