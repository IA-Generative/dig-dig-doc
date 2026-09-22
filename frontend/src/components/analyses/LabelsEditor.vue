<script setup lang="ts">
import { ref, watch } from "vue";

import { useAnalyses } from "@/composables/useAnalyses";
import { suggestLabels } from "@/composables/useLlmAssist";
import type { Agent, LabelDefinition } from "@/types/analyse";

const props = defineProps<{ analyseId: string; agent: Agent }>();

const { updateAgentLabels } = useAnalyses();

const draftLabels = ref<LabelDefinition[]>(cloneLabels(props.agent.labels));
const isDirty = ref(false);

function cloneLabels(labels: LabelDefinition[]): LabelDefinition[] {
  return labels.map((label) => ({ ...label }));
}

watch(
  () => props.agent.labels,
  (labels) => {
    draftLabels.value = cloneLabels(labels);
    isDirty.value = false;
  },
);

watch(
  draftLabels,
  (labels) => {
    isDirty.value = JSON.stringify(labels) !== JSON.stringify(props.agent.labels);
  },
  { deep: true },
);

function addLabel() {
  draftLabels.value.push({ id: `label-${Date.now()}`, name: "", definition: "" });
}

function removeLabel(id: string) {
  draftLabels.value = draftLabels.value.filter((label) => label.id !== id);
}

function applySuggestions() {
  draftLabels.value = suggestLabels();
}

function save() {
  updateAgentLabels(props.analyseId, props.agent.id, draftLabels.value);
}
</script>

<template>
  <div class="labels-editor">
    <h4 class="fr-h6 labels-editor__title">Labels de classification</h4>

    <p v-if="draftLabels.length === 0" class="fr-text--sm">Aucun label défini pour cet agent.</p>

    <ul v-else class="labels-editor__list">
      <li v-for="label in draftLabels" :key="label.id" class="labels-editor__row">
        <div class="labels-editor__row-header">
          <DsfrInput v-model="label.name" label="Label" label-visible class="labels-editor__name" />
          <DsfrButton
            label="Supprimer le label"
            icon-only
            tertiary
            icon="ri-delete-bin-line"
            size="sm"
            @click="removeLabel(label.id)"
          />
        </div>
        <DsfrInput v-model="label.definition" label="Définition" label-visible />
      </li>
    </ul>

    <div class="labels-editor__actions">
      <DsfrButton label="Ajouter un label" tertiary icon="ri-add-line" size="sm" @click="addLabel" />
      <DsfrButton label="Aide LLM" secondary icon="ri-magic-line" size="sm" @click="applySuggestions" />
      <DsfrButton label="Enregistrer" :disabled="!isDirty" size="sm" @click="save" />
    </div>
  </div>
</template>

<style scoped>
.labels-editor {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.labels-editor__title {
  margin: 0;
}

.labels-editor__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.labels-editor__row {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 0.25rem;
}

.labels-editor__row-header {
  display: flex;
  align-items: end;
  gap: 0.75rem;
}

.labels-editor__name {
  flex: 1;
}

.labels-editor__actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}
</style>
