<script setup lang="ts">
import { computed } from "vue";

import { dueInfo, type DueTone } from "@/utils/due";

// Date d'échéance : couleur selon les seuils de l'analyse (#172) ET libellé
// explicite (« Échéance dans 5 j »), la couleur n'étant jamais le seul signal.
const props = defineProps<{ dueAt: string | null }>();
const info = computed(() => dueInfo(props.dueAt));

const TONE_CLASS: Record<DueTone, string> = {
  none: "",
  ok: "fr-badge--success",
  warning: "fr-badge--warning",
  danger: "fr-badge--error",
  overdue: "fr-badge--error",
};
</script>

<template>
  <span v-if="info.tone === 'none'" class="due__none">—</span>
  <span v-else class="fr-badge fr-badge--sm fr-badge--no-icon" :class="TONE_CLASS[info.tone]">{{ info.label }}</span>
</template>

<style scoped>
.due__none {
  color: var(--text-mention-grey);
}
</style>
