<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";

import LlmAssistButton from "@/components/analyses/LlmAssistButton.vue";
import VersionHistory from "@/components/analyses/VersionHistory.vue";
import { useAnalyses } from "@/composables/useAnalyses";
import { suggestLabelDefinition, suggestLabels } from "@/composables/useLlmAssist";
import type { Agent, LabelDefinition } from "@/types/analyse";

const props = defineProps<{ analyseId: string; agent: Agent }>();

const { updateAgentLabels, restoreAgentLabelsVersion } = useAnalyses();

const pageSize = 3;

const draftLabels = ref<LabelDefinition[]>(cloneLabels(props.agent.labels));
const isDirty = ref(false);
const currentPage = ref(1);

function cloneLabels(labels: LabelDefinition[]): LabelDefinition[] {
  return labels.map((label) => ({ ...label }));
}

watch(
  () => props.agent.labels,
  (labels) => {
    draftLabels.value = cloneLabels(labels);
    isDirty.value = false;
    currentPage.value = 1;
  },
);

watch(
  draftLabels,
  (labels) => {
    isDirty.value = JSON.stringify(labels) !== JSON.stringify(props.agent.labels);
  },
  { deep: true },
);

const pageCount = computed(() => Math.max(1, Math.ceil(draftLabels.value.length / pageSize)));

const paginatedLabels = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  return draftLabels.value.slice(start, start + pageSize);
});

const pages = computed(() =>
  Array.from({ length: pageCount.value }, (_, i) => ({ label: String(i + 1), title: `Page ${i + 1}` })),
);

function addLabel() {
  draftLabels.value.push({ id: `label-${Date.now()}`, name: "", definition: "" });
  nextTick(() => (currentPage.value = pageCount.value));
}

function removeLabel(id: string) {
  draftLabels.value = draftLabels.value.filter((label) => label.id !== id);
  nextTick(() => (currentPage.value = Math.min(currentPage.value, pageCount.value)));
}

function applySuggestions() {
  draftLabels.value = suggestLabels();
  nextTick(() => (currentPage.value = 1));
}

function applyDefinitionSuggestion(label: LabelDefinition) {
  label.definition = suggestLabelDefinition(label.name);
}

function save() {
  updateAgentLabels(props.analyseId, props.agent.id, draftLabels.value);
}

function restoreVersion(versionId: string) {
  restoreAgentLabelsVersion(props.analyseId, props.agent.id, versionId);
}

function formatVersionContent(labels: LabelDefinition[]) {
  return labels.length > 0 ? labels.map((label) => label.name || "(sans nom)").join(", ") : "(aucun label)";
}
</script>

<template>
  <div class="labels-editor">
    <h4 class="fr-h6 labels-editor__title">Labels de classification</h4>

    <p v-if="draftLabels.length === 0" class="fr-text--sm">Aucun label défini pour cet agent.</p>

    <template v-else>
      <ul class="labels-editor__list">
        <li v-for="label in paginatedLabels" :key="label.id" class="labels-editor__row">
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
          <div class="labels-editor__definition-row">
            <DsfrInput v-model="label.definition" label="Définition" label-visible class="labels-editor__definition" />
            <LlmAssistButton compact label="Suggérer une définition" @click="applyDefinitionSuggestion(label)" />
          </div>
        </li>
      </ul>

      <DsfrPagination
        v-if="pageCount > 1"
        :pages="pages"
        v-model:current-page="currentPage"
        class="labels-editor__pagination"
      />
    </template>

    <div class="labels-editor__actions">
      <DsfrButton label="Ajouter un label" tertiary icon="ri-add-line" size="sm" @click="addLabel" />
      <LlmAssistButton @click="applySuggestions" />
      <DsfrButton label="Enregistrer" :disabled="!isDirty" size="sm" @click="save" />
    </div>

    <VersionHistory :versions="agent.labelsVersions" :format-content="formatVersionContent" @restore="restoreVersion" />
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
  padding: 1.25rem;
  background: var(--background-default-grey);
  border: 1px solid var(--border-default-grey);
  border-left: 3px solid #6a5cff;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  transition:
    box-shadow 0.15s ease,
    transform 0.15s ease;
}

.labels-editor__row:hover {
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.labels-editor__row-header {
  display: flex;
  align-items: end;
  gap: 0.75rem;
}

.labels-editor__name {
  flex: 1;
}

.labels-editor__definition-row {
  display: flex;
  align-items: end;
  gap: 0.5rem;
}

.labels-editor__definition {
  flex: 1;
}

.labels-editor__pagination {
  display: flex;
  justify-content: center;
}

.labels-editor__actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}
</style>
