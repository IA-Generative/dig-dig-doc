<script setup lang="ts">
import { computed } from "vue";

import type { ToolStep } from "@/utils/groupToolEvents";

const props = defineProps<{ steps: ToolStep[] }>();

// Noms lisibles des outils du chat. Un outil inconnu s'affiche tel quel.
const TOOL_LABELS: Record<string, string> = {
  search_documents: "Recherche dans les documents",
  read_page: "Lecture d'une page",
  view_classifications: "Consultation des classifications",
  view_entities: "Consultation des entités",
};
const label = (name: string) => TOOL_LABELS[name] ?? name;

const running = computed(() => props.steps.find((s) => s.status === "running"));
const summary = computed(() => {
  if (running.value) return `${label(running.value.name)}…`;
  const n = props.steps.length;
  return `${n} outil${n > 1 ? "s" : ""} utilisé${n > 1 ? "s" : ""}`;
});

const stepIcon = (status: ToolStep["status"]) =>
  status === "running" ? "ri-loader-4-line" : status === "error" ? "ri-error-warning-line" : "ri-check-line";
</script>

<template>
  <details v-if="steps.length" class="tool-steps">
    <summary class="tool-steps__summary">
      <VIcon :name="running ? 'ri-loader-4-line' : 'ri-check-line'" :class="{ spin: running }" />
      {{ summary }}
    </summary>
    <ul class="tool-steps__list">
      <li v-for="(step, i) in steps" :key="i" class="tool-steps__step">
        <VIcon :name="stepIcon(step.status)" :class="{ spin: step.status === 'running' }" />
        <span>{{ label(step.name) }}</span>
        <details class="tool-steps__detail">
          <summary>Détail</summary>
          <pre>{{ JSON.stringify(step.args, null, 2) }}</pre>
          <pre v-if="step.result">{{ step.result }}</pre>
        </details>
      </li>
    </ul>
  </details>
</template>

<style scoped>
.tool-steps { font-size: 0.875rem; color: var(--text-mention-grey, #666); }
.tool-steps__summary { cursor: pointer; }
.tool-steps__list { list-style: none; padding-left: 0; margin: 0.5rem 0 0; }
.tool-steps__step { margin-bottom: 0.25rem; }
.tool-steps__detail pre { white-space: pre-wrap; font-size: 0.75rem; }

.spin { animation: tool-steps-spin 1s linear infinite; }
@keyframes tool-steps-spin { to { transform: rotate(360deg); } }
</style>
