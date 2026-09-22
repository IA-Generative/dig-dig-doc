<script setup lang="ts">
import AgentToolsEditor from "@/components/analyses/AgentToolsEditor.vue";
import PromptEditor from "@/components/analyses/PromptEditor.vue";
import { useAnalyses } from "@/composables/useAnalyses";
import { suggestAgentPrompt } from "@/composables/useLlmAssist";
import type { Agent } from "@/types/analyse";

const props = defineProps<{ analyseId: string; agent: Agent }>();

const { updateAgentPrompt, restoreAgentPromptVersion, updateAgentOutput } = useAnalyses();

function savePrompt(prompt: string) {
  updateAgentPrompt(props.analyseId, props.agent.id, prompt);
}

function restorePromptVersion(versionId: string) {
  restoreAgentPromptVersion(props.analyseId, props.agent.id, versionId);
}

function toggleOutput(output: boolean) {
  updateAgentOutput(props.analyseId, props.agent.id, output);
}
</script>

<template>
  <div class="agent-card">
    <div class="agent-card__header">
      <div class="agent-card__identity">
        <span class="agent-card__icon"><VIcon name="ri-robot-line" /></span>
        <h3 class="fr-h5 agent-card__title">{{ agent.name }}</h3>
      </div>
      <DsfrToggleSwitch
        :model-value="agent.output"
        label="Sortie"
        no-text
        label-left
        class="agent-card__output-toggle"
        @update:model-value="toggleOutput"
      />
    </div>

    <PromptEditor
      :prompt="agent.prompt"
      :versions="agent.promptVersions"
      :suggest-prompt="suggestAgentPrompt"
      @save="savePrompt"
      @restore="restorePromptVersion"
    />

    <hr class="agent-card__divider" />
    <AgentToolsEditor :analyse-id="analyseId" :agent="agent" />
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
  gap: 0.75rem;
}

.agent-card__identity {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.agent-card__output-toggle {
  margin: 0;
  flex-shrink: 0;
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
