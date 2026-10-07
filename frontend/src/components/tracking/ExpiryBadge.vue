<script setup lang="ts">
import { computed } from "vue";

import { expiryInfo, type ExpiryTone } from "@/utils/expiry";

// Date de péremption : couleur selon les seuils de l'analyse (#172) ET libellé
// explicite (« Expire dans 5 j »), la couleur n'étant jamais le seul signal.
const props = defineProps<{ expiresAt: string | null }>();
const info = computed(() => expiryInfo(props.expiresAt));

const TONE_CLASS: Record<ExpiryTone, string> = {
  none: "",
  ok: "fr-badge--success",
  warning: "fr-badge--warning",
  danger: "fr-badge--error",
  expired: "fr-badge--error",
};
</script>

<template>
  <span v-if="info.tone === 'none'" class="expiry__none">—</span>
  <span v-else class="fr-badge fr-badge--sm fr-badge--no-icon" :class="TONE_CLASS[info.tone]">{{ info.label }}</span>
</template>

<style scoped>
.expiry__none {
  color: var(--text-mention-grey);
}
</style>
