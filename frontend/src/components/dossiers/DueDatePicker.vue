<script setup lang="ts">
import { ref, watch } from "vue";

import DossierDueBadge from "@/components/dossiers/DossierDueBadge.vue";
import type { DueInfo } from "@/types/dossier";
import { formatDueDate } from "@/utils/due";

// Échéance du dossier (#172) : le badge (libellé + couleur) puis un champ date pour la modifier ou la supprimer.
// Le composant ne fait aucun appel : il émet la nouvelle date (ou null) et le parent l'enregistre.
const props = defineProps<{ dueAt?: string; due?: DueInfo; busy?: boolean }>();
const emit = defineEmits<{ change: [dueAt: string | null] }>();

const editing = ref(false);
const draft = ref(props.dueAt ?? "");
watch(
  () => props.dueAt,
  (value) => (draft.value = value ?? ""),
);

function save() {
  const next = draft.value || null;
  editing.value = false;
  if (next !== (props.dueAt ?? null)) emit("change", next);
}

function remove() {
  draft.value = "";
  editing.value = false;
  if (props.dueAt) emit("change", null);
}
</script>

<template>
  <div class="ddp">
    <template v-if="!editing">
      <DossierDueBadge v-if="due" :due="due" />
      <span v-else class="fr-text--sm ddp__none">Sans échéance</span>
      <span v-if="dueAt" class="fr-text--sm ddp__date">le {{ formatDueDate(dueAt) }}</span>
      <DsfrButton
        :label="dueAt ? 'Modifier' : 'Définir une échéance'"
        tertiary
        no-outline
        size="sm"
        :disabled="busy"
        @click="editing = true"
      />
    </template>
    <template v-else>
      <label class="ddp__field">
        <span class="fr-sr-only">Date d'échéance</span>
        <input v-model="draft" type="date" class="fr-input" />
      </label>
      <DsfrButton label="Enregistrer" size="sm" :disabled="busy" @click="save" />
      <DsfrButton v-if="dueAt" label="Supprimer l'échéance" tertiary size="sm" :disabled="busy" @click="remove" />
      <DsfrButton label="Annuler" tertiary no-outline size="sm" @click="editing = false" />
    </template>
  </div>
</template>

<style scoped>
.ddp {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
}

.ddp__none,
.ddp__date {
  margin: 0;
  color: var(--text-mention-grey);
}

.ddp__field {
  display: block;
}
</style>
