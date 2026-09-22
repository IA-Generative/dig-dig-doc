<script setup lang="ts">
import { ref, watch } from "vue";

import { useAnalyses } from "@/composables/useAnalyses";
import { suggestEntities } from "@/composables/useLlmAssist";
import type { Agent, EntityDefinition, EntityType } from "@/types/analyse";

const props = defineProps<{ analyseId: string; agent: Agent }>();

const { updateAgentEntities } = useAnalyses();

const entityTypes: EntityType[] = ["texte", "date", "nombre", "booléen", "identifiant"];

const draftEntities = ref<EntityDefinition[]>(cloneEntities(props.agent.entities));
const isDirty = ref(false);

function cloneEntities(entities: EntityDefinition[]): EntityDefinition[] {
  return entities.map((entity) => ({ ...entity }));
}

watch(
  () => props.agent.entities,
  (entities) => {
    draftEntities.value = cloneEntities(entities);
    isDirty.value = false;
  },
);

watch(
  draftEntities,
  (entities) => {
    isDirty.value = JSON.stringify(entities) !== JSON.stringify(props.agent.entities);
  },
  { deep: true },
);

function addEntity() {
  draftEntities.value.push({ id: `entity-${Date.now()}`, name: "", definition: "", type: "texte" });
}

function removeEntity(id: string) {
  draftEntities.value = draftEntities.value.filter((entity) => entity.id !== id);
}

function applySuggestions() {
  draftEntities.value = suggestEntities();
}

function save() {
  updateAgentEntities(props.analyseId, props.agent.id, draftEntities.value);
}
</script>

<template>
  <div class="entities-editor">
    <h4 class="fr-h6 entities-editor__title">Entités à extraire</h4>

    <p v-if="draftEntities.length === 0" class="fr-text--sm">Aucune entité définie pour cet agent.</p>

    <ul v-else class="entities-editor__list">
      <li v-for="entity in draftEntities" :key="entity.id" class="entities-editor__row">
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
        <DsfrInput v-model="entity.definition" label="Définition" label-visible />
      </li>
    </ul>

    <div class="entities-editor__actions">
      <DsfrButton label="Ajouter une entité" tertiary icon="ri-add-line" size="sm" @click="addEntity" />
      <DsfrButton label="Aide LLM" secondary icon="ri-magic-line" size="sm" @click="applySuggestions" />
      <DsfrButton label="Enregistrer" :disabled="!isDirty" size="sm" @click="save" />
    </div>
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
  padding: 1rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 0.25rem;
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

.entities-editor__actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}
</style>
