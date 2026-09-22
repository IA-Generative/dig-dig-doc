<script setup lang="ts">
import { computed } from "vue";

import AgentPromptEditor from "@/components/analyses/AgentPromptEditor.vue";
import AgentToolsEditor from "@/components/analyses/AgentToolsEditor.vue";
import AgentVersionHistory from "@/components/analyses/AgentVersionHistory.vue";
import EntitiesEditor from "@/components/analyses/EntitiesEditor.vue";
import LabelsEditor from "@/components/analyses/LabelsEditor.vue";
import type { Agent, AgentCapability } from "@/types/analyse";

const props = defineProps<{ analyseId: string; agent: Agent }>();

const NER_CAPABILITY: AgentCapability = "Extraction d'entités nommées";
const isNerAgent = computed(() => props.agent.capability === NER_CAPABILITY);

const capabilityIcons: Record<AgentCapability, string> = {
  "Classification documentaire": "ri-price-tag-3-line",
  "Extraction d'entités nommées": "ri-braces-line",
  "Contrôle de cohérence": "ri-shield-check-line",
  "Agent généraliste": "ri-robot-line",
};
const icon = computed(() => capabilityIcons[props.agent.capability]);
</script>

<template>
  <div class="agent-card">
    <div class="agent-card__header">
      <div class="agent-card__identity">
        <span class="agent-card__icon"><VIcon :name="icon" /></span>
        <h3 class="fr-h5 agent-card__title">{{ agent.name }}</h3>
      </div>
      <DsfrBadge :label="agent.capability" type="info" small />
    </div>

    <AgentPromptEditor :analyse-id="analyseId" :agent="agent" />

    <hr class="agent-card__divider" />
    <AgentToolsEditor :analyse-id="analyseId" :agent="agent" />

    <template v-if="agent.capability === 'Classification documentaire' || isNerAgent">
      <hr class="agent-card__divider" />
      <LabelsEditor v-if="agent.capability === 'Classification documentaire'" :analyse-id="analyseId" :agent="agent" />
      <EntitiesEditor v-if="isNerAgent" :analyse-id="analyseId" :agent="agent" />
    </template>

    <template v-if="agent.promptVersions.length > 0">
      <hr class="agent-card__divider" />
      <AgentVersionHistory :analyse-id="analyseId" :agent="agent" />
    </template>
  </div>
</template>

<style scoped>
.agent-card {
  background: var(--background-default-grey);
  border: 1px solid var(--border-default-grey);
  border-radius: 1rem;
  padding: 1.75rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition:
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.agent-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.agent-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.agent-card__identity {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.agent-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.75rem;
  background: linear-gradient(135deg, #6a5cff1a 0%, #ff6ca01a 100%);
  color: #4b3fd9;
  flex-shrink: 0;
}

.agent-card__title {
  margin: 0;
}

.agent-card__divider {
  border: none;
  border-top: 1px solid var(--border-default-grey);
  margin: 0;
}
</style>
