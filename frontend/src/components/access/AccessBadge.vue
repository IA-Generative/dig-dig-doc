<script setup lang="ts">
import type { Visibility } from "@/types/access";

// Pastille « Restreint » (icône + libellé : jamais la couleur seule). Rien n'est affiché pour un dossier
// « Selon l'analyse ».
defineProps<{ visibility?: Visibility }>();
</script>

<template>
  <span
    v-if="visibility === 'restricted'"
    class="fr-badge fr-badge--sm fr-badge--no-icon access-badge"
    title="Accès restreint à certains groupes"
  >
    <VIcon name="ri-lock-line" scale="0.7" /> Restreint
  </span>
</template>

<style scoped>
.access-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  background: var(--background-contrast-grey);
  color: var(--text-default-grey);
}
</style>
