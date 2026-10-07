<script setup lang="ts">
import { computed } from "vue";

import { STATUSES } from "@/composables/useTracking";

// Pastille de statut : libellé toujours écrit, la couleur n'est qu'un renfort.
const props = defineProps<{ statusId: string }>();
const status = computed(() => STATUSES.find((s) => s.id === props.statusId));
</script>

<template>
  <span v-if="status" class="fr-badge fr-badge--sm fr-badge--no-icon" :class="`fr-badge--${status.tone}`">
    {{ status.label }}
  </span>
</template>
