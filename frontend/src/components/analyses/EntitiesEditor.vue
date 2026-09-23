<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";

import LlmAssistButton from "@/components/analyses/LlmAssistButton.vue";
import VersionHistory from "@/components/analyses/VersionHistory.vue";
import { suggestEntities, suggestEntityDefinition } from "@/composables/useLlmAssist";
import type { EntityDefinition, EntityType, Version } from "@/types/analyse";

const props = defineProps<{ entities: EntityDefinition[]; versions: Version<EntityDefinition[]>[] }>();
const emit = defineEmits<{ save: [EntityDefinition[]]; restore: [string] }>();

const entityTypes: EntityType[] = ["texte", "date", "nombre", "booléen", "identifiant"];
const pageSize = 3;

const draftEntities = ref<EntityDefinition[]>(cloneEntities(props.entities));
const isDirty = ref(false);
const currentPage = ref(1);
const isSuggestingList = ref(false);
const suggestingDefinitionId = ref<string | null>(null);

function cloneEntities(entities: EntityDefinition[]): EntityDefinition[] {
  return entities.map((entity) => ({ ...entity }));
}

watch(
  () => props.entities,
  (entities) => {
    draftEntities.value = cloneEntities(entities);
    isDirty.value = false;
    currentPage.value = 1;
  },
);

watch(
  draftEntities,
  (entities) => {
    isDirty.value = JSON.stringify(entities) !== JSON.stringify(props.entities);
  },
  { deep: true },
);

const pageCount = computed(() => Math.max(1, Math.ceil(draftEntities.value.length / pageSize)));

const paginatedEntities = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  return draftEntities.value.slice(start, start + pageSize);
});

const pages = computed(() =>
  Array.from({ length: pageCount.value }, (_, i) => ({ label: String(i + 1), title: `Page ${i + 1}` })),
);

function addEntity() {
  draftEntities.value.push({ id: `entity-${Date.now()}`, name: "", definition: "", type: "texte" });
  nextTick(() => (currentPage.value = pageCount.value));
}

function removeEntity(id: string) {
  draftEntities.value = draftEntities.value.filter((entity) => entity.id !== id);
  nextTick(() => (currentPage.value = Math.min(currentPage.value, pageCount.value)));
}

async function applySuggestions(model: string | null) {
  isSuggestingList.value = true;
  try {
    const suggestions = await suggestEntities(model);
    draftEntities.value = suggestions.map((entity, index) => ({ ...entity, id: `entity-suggestion-${index}` }));
    nextTick(() => (currentPage.value = 1));
  } catch (error) {
    alert(error instanceof Error ? error.message : "Échec de l'aide LLM.");
  } finally {
    isSuggestingList.value = false;
  }
}

async function applyDefinitionSuggestion(entity: EntityDefinition, model: string | null) {
  suggestingDefinitionId.value = entity.id;
  try {
    const suggestion = await suggestEntityDefinition(entity.name, model);
    entity.definition = suggestion.definition;
    entity.type = suggestion.type;
  } catch (error) {
    alert(error instanceof Error ? error.message : "Échec de l'aide LLM.");
  } finally {
    suggestingDefinitionId.value = null;
  }
}

function save() {
  emit("save", draftEntities.value);
}

function formatVersionContent(entities: EntityDefinition[]) {
  return entities.length > 0
    ? entities.map((entity) => `${entity.name || "(sans nom)"} (${entity.type})`).join(", ")
    : "(aucune entité)";
}
</script>

<template>
  <div class="entities-editor">
    <h4 class="fr-h6 entities-editor__title">Entités à extraire</h4>

    <p v-if="draftEntities.length === 0" class="fr-text--sm">Aucune entité définie.</p>

    <template v-else>
      <ul class="entities-editor__list">
        <li v-for="entity in paginatedEntities" :key="entity.id" class="entities-editor__row">
          <div class="entities-editor__row-header">
            <DsfrInput v-model="entity.name" label="Entité" label-visible class="entities-editor__name" />
            <DsfrSelect v-model="entity.type" label="Type" :options="entityTypes" class="entities-editor__type" />
            <DsfrButton
              label="Supprimer l'entité"
              icon-only
              tertiary
              icon="ri-delete-bin-line"
              size="sm"
              @click="removeEntity(entity.id)"
            />
          </div>
          <div class="entities-editor__definition-row">
            <DsfrInput
              v-model="entity.definition"
              label="Définition"
              label-visible
              class="entities-editor__definition"
            />
            <LlmAssistButton
              compact
              label="Suggérer une définition"
              :loading="suggestingDefinitionId === entity.id"
              @click="(model) => applyDefinitionSuggestion(entity, model)"
            />
          </div>
        </li>
      </ul>

      <DsfrPagination
        v-if="pageCount > 1"
        :pages="pages"
        v-model:current-page="currentPage"
        class="entities-editor__pagination"
      />
    </template>

    <div class="entities-editor__actions">
      <DsfrButton label="Ajouter une entité" tertiary icon="ri-add-line" size="sm" @click="addEntity" />
      <LlmAssistButton :loading="isSuggestingList" @click="applySuggestions" />
      <DsfrButton label="Enregistrer" :disabled="!isDirty" size="sm" @click="save" />
    </div>

    <VersionHistory :versions="versions" :format-content="formatVersionContent" @restore="emit('restore', $event)" />
  </div>
</template>

<style scoped>
.entities-editor {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.entities-editor__title {
  margin: 0;
}

.entities-editor__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.entities-editor__row {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1.25rem;
  background: var(--background-default-grey);
  border: 1px solid var(--border-default-grey);
  border-left: 3px solid #9d6cff;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  transition:
    box-shadow 0.15s ease,
    transform 0.15s ease;
}

.entities-editor__row:hover {
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.entities-editor__row-header {
  display: flex;
  align-items: end;
  gap: 0.75rem;
}

.entities-editor__name {
  flex: 1;
}

.entities-editor__type {
  min-width: 9rem;
}

.entities-editor__definition-row {
  display: flex;
  align-items: end;
  gap: 0.5rem;
}

.entities-editor__definition {
  flex: 1;
}

.entities-editor__pagination {
  display: flex;
  justify-content: center;
}

.entities-editor__actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}
</style>
