<script setup lang="ts">
import { ref } from "vue";

import type { Assignee } from "@/types/tracking";

// Affectation en lot : apparaît dès qu'au moins une ligne est sélectionnée.
defineProps<{ count: number; assignees: Assignee[]; canSetAccess?: boolean }>();
const emit = defineEmits<{ assign: [assigneeId: string | null]; clear: []; "set-access": [] }>();

const target = ref("");
</script>

<template>
  <div class="bulk" role="region" aria-label="Actions sur la sélection">
    <strong class="bulk__count">{{ count }} dossier{{ count > 1 ? "s" : "" }} sélectionné{{ count > 1 ? "s" : "" }}</strong>
    <label class="fr-sr-only" for="bulk-assignee">Affecter à</label>
    <select id="bulk-assignee" v-model="target" class="fr-select bulk__select">
      <option value="" disabled>Affecter à…</option>
      <option v-for="a in assignees" :key="a.id" :value="a.id">{{ a.name }}</option>
    </select>
    <button type="button" class="fr-btn fr-btn--sm" :disabled="!target" @click="emit('assign', target); target = ''">
      Affecter
    </button>
    <button type="button" class="fr-btn fr-btn--sm fr-btn--secondary" @click="emit('assign', null)">Retirer l'affectation</button>
    <button v-if="canSetAccess" type="button" class="fr-btn fr-btn--sm fr-btn--secondary fr-btn--icon-left ri-lock-line" @click="emit('set-access')">
      Définir l'accès
    </button>
    <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline" @click="emit('clear')">Tout désélectionner</button>
  </div>
</template>

<style scoped>
.bulk {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  background: var(--background-action-low-blue-france);
}

.bulk__count {
  margin-right: 0.5rem;
  color: var(--text-active-blue-france);
}

.bulk__select {
  max-width: 14rem;
  padding: 0.25rem 2rem 0.25rem 0.5rem;
}
</style>
