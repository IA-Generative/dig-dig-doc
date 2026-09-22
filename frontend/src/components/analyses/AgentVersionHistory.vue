<script setup lang="ts">
import VersionHistory from "@/components/analyses/VersionHistory.vue";
import { useAnalyses } from "@/composables/useAnalyses";
import type { Agent } from "@/types/analyse";

const props = defineProps<{ analyseId: string; agent: Agent }>();

const { restoreAgentPromptVersion } = useAnalyses();

function restore(versionId: string) {
  restoreAgentPromptVersion(props.analyseId, props.agent.id, versionId);
}

function formatContent(content: string) {
  return content;
}
</script>

<template>
  <VersionHistory :versions="agent.promptVersions" :format-content="formatContent" @restore="restore" />
</template>
