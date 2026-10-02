<script setup lang="ts">
import { computed } from "vue";

import type { FieldType } from "@/types/documentTemplate";

// Saisie de la valeur d'un champ selon son type : texte, date, nombre, oui/non, liste (un élément par ligne).
// Le texte saisi est converti en valeur par `textToValue` (types/documentDraft.ts) au moment d'enregistrer.
const props = defineProps<{ modelValue: string; type: FieldType; label: string }>();
const emit = defineEmits<{ "update:modelValue": [string] }>();

const booleanOptions = [
  { value: "oui", text: "Oui" },
  { value: "non", text: "Non" },
];

const hint = computed(() => {
  if (props.type === "list") return "Un élément par ligne";
  if (props.type === "number") return "Un nombre, par exemple 1250,5";
  return undefined;
});
</script>

<template>
  <div class="value-editor">
    <DsfrSelect
      v-if="type === 'boolean'"
      :model-value="modelValue || 'non'"
      :label="label"
      label-visible
      :options="booleanOptions"
      @update:model-value="emit('update:modelValue', String($event))"
    />
    <DsfrInput
      v-else-if="type === 'date'"
      :model-value="modelValue"
      :label="label"
      label-visible
      type="date"
      @update:model-value="emit('update:modelValue', String($event))"
    />
    <DsfrInput
      v-else-if="type === 'number'"
      :model-value="modelValue"
      :label="label"
      label-visible
      :hint="hint"
      @update:model-value="emit('update:modelValue', String($event))"
    />
    <DsfrInput
      v-else
      :model-value="modelValue"
      :label="label"
      label-visible
      :hint="hint"
      is-textarea
      :rows="type === 'list' ? 4 : 3"
      @update:model-value="emit('update:modelValue', String($event))"
    />
  </div>
</template>
