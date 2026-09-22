<script setup lang="ts">
import { useAnalyses } from "@/composables/useAnalyses";
import type { Agent } from "@/types/analyse";

const props = defineProps<{ analyseId: string; agent: Agent }>();

const { restoreAgentPromptVersion } = useAnalyses();

function restore(versionId: string) {
  restoreAgentPromptVersion(props.analyseId, props.agent.id, versionId);
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });
}
</script>

<template>
  <DsfrAccordion
    v-if="agent.promptVersions.length > 0"
    :title="`Historique des versions (${agent.promptVersions.length})`"
  >
    <ul class="agent-version-history__list">
      <li v-for="version in agent.promptVersions" :key="version.id" class="agent-version-history__item">
        <div>
          <p class="fr-text--sm agent-version-history__date">{{ formatDate(version.createdAt) }}</p>
          <p class="fr-text--sm agent-version-history__content">{{ version.content }}</p>
        </div>
        <DsfrButton label="Restaurer" tertiary size="sm" @click="restore(version.id)" />
      </li>
    </ul>
  </DsfrAccordion>
</template>

<style scoped>
.agent-version-history__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.agent-version-history__item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  border-top: 1px solid var(--border-default-grey);
  padding-top: 1rem;
}

.agent-version-history__item:first-child {
  border-top: none;
  padding-top: 0;
}

.agent-version-history__date {
  color: var(--text-mention-grey);
  margin: 0 0 0.25rem;
}

.agent-version-history__content {
  margin: 0;
}
</style>
