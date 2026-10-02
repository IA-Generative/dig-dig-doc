<script setup lang="ts">
import { computed } from "vue";

import {
  ELEMENT_KIND_LABELS,
  FIELD_TYPE_LABELS,
  METADATA_KEY_LABELS,
  SOURCE_KIND_LABELS,
  type ElementKind,
  type FieldDefinition,
  type FieldType,
  type MetadataKey,
  type SourceKind,
} from "@/types/documentTemplate";
import type { ValidationIssue } from "@/utils/documentTemplateValidation";

/** Écrit un placeholder comme dans le fichier : {{ nom }} (hors gabarit, où « }} » fermerait l'interpolation). */
const braces = (name: string) => `{{ ${name} }}`;

// Un champ d'un modèle de document : son libellé, son type, sa source et sa consigne de génération.
const props = defineProps<{
  modelValue: FieldDefinition;
  /** Le fichier contient le placeholder {{ nom }}. */
  inFile: boolean;
  issues: ValidationIssue[];
}>();
const emit = defineEmits<{ "update:modelValue": [FieldDefinition]; remove: [] }>();

function update(patch: Partial<FieldDefinition>) {
  emit("update:modelValue", { ...props.modelValue, ...patch });
}

const typeOptions = Object.entries(FIELD_TYPE_LABELS).map(([value, text]) => ({ value, text }));
const sourceOptions = Object.entries(SOURCE_KIND_LABELS).map(([value, text]) => ({ value, text }));
const elementKindOptions = Object.entries(ELEMENT_KIND_LABELS).map(([value, text]) => ({ value, text }));
const metadataOptions = Object.entries(METADATA_KEY_LABELS).map(([value, text]) => ({ value, text }));

const sourceKind = computed(() => props.modelValue.source.kind);

function changeSourceKind(kind: SourceKind) {
  if (kind === "analysis") update({ source: { kind, elementKind: "entity", definitionName: "" } });
  else if (kind === "dossier_metadata") update({ source: { kind, key: "dossier_name" } });
  else update({ source: { kind: "instruction" } });
}

const analysisSource = computed(() => (props.modelValue.source.kind === "analysis" ? props.modelValue.source : null));
const metadataSource = computed(() => (props.modelValue.source.kind === "dossier_metadata" ? props.modelValue.source : null));
</script>

<template>
  <li class="field-row" :class="{ 'field-row--invalid': issues.length > 0 }">
    <div class="field-row__header">
      <code class="field-row__name">{{ braces(modelValue.name) }}</code>
      <DsfrBadge v-if="!inFile" label="Absent du fichier" type="warning" small />
      <DsfrBadge :label="modelValue.required ? 'Obligatoire' : 'Facultatif'" :type="modelValue.required ? 'info' : 'new'" small />
      <DsfrButton
        v-if="!inFile"
        label="Supprimer"
        icon="ri-delete-bin-line"
        tertiary
        no-outline
        size="sm"
        class="field-row__remove"
        @click="emit('remove')"
      />
    </div>

    <!-- Chaque composant DSFR a plusieurs nœuds racine : sans <div>, ils deviendraient des cellules distinctes. -->
    <div class="field-row__grid">
      <div>
        <DsfrInput
          :model-value="modelValue.label"
          label="Libellé"
          label-visible
          hint="Affiché à l'instructeur"
          @update:model-value="update({ label: String($event) })"
        />
      </div>
      <div>
        <DsfrSelect
          :model-value="modelValue.type"
          label="Type"
          label-visible
          :options="typeOptions"
          @update:model-value="update({ type: $event as FieldType })"
        />
      </div>
      <div class="field-row__required">
        <DsfrCheckbox
          :model-value="modelValue.required"
          :name="`required-${modelValue.name}`"
          label="Champ obligatoire"
          @update:model-value="update({ required: Boolean($event) })"
        />
      </div>
    </div>

    <div class="field-row__grid">
      <div>
        <DsfrSelect
          :model-value="sourceKind"
          label="D'où vient la valeur"
          label-visible
          :options="sourceOptions"
          @update:model-value="changeSourceKind($event as SourceKind)"
        />
      </div>
      <template v-if="analysisSource">
        <div>
          <DsfrSelect
            :model-value="analysisSource.elementKind"
            label="Type d'élément"
            label-visible
            :options="elementKindOptions"
            @update:model-value="update({ source: { ...analysisSource, elementKind: $event as ElementKind } })"
          />
        </div>
        <div>
          <DsfrInput
            :model-value="analysisSource.definitionName"
            label="Nom de l'élément"
            label-visible
            hint="Nom de la définition dans l'analyse"
            @update:model-value="update({ source: { ...analysisSource, definitionName: String($event) } })"
          />
        </div>
      </template>
      <div v-else-if="metadataSource">
        <DsfrSelect
          :model-value="metadataSource.key"
          label="Métadonnée"
          label-visible
          :options="metadataOptions"
          @update:model-value="update({ source: { kind: 'dossier_metadata', key: $event as MetadataKey } })"
        />
      </div>
    </div>

    <div>
      <DsfrInput
        :model-value="modelValue.instruction"
        label="Consigne de génération"
        label-visible
        hint="Pour l'agent : format de date, longueur, ton… (facultatif)"
        is-textarea
        :rows="2"
        @update:model-value="update({ instruction: String($event) })"
      />
    </div>

    <ul v-if="issues.length" class="field-row__issues">
      <li v-for="issue in issues" :key="issue.kind + issue.message">{{ issue.message }}</li>
    </ul>
  </li>
</template>

<style scoped>
.field-row {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 0.375rem;
  background: var(--background-default-grey);
  list-style: none;
}

.field-row--invalid {
  border-color: var(--border-plain-error);
}

.field-row__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.field-row__name {
  font-weight: 700;
  font-size: 1rem;
}

.field-row__remove {
  margin-left: auto;
}

.field-row__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  gap: 0.75rem 1rem;
  align-items: start;
}

.field-row__required {
  align-self: center;
}

.field-row__issues {
  margin: 0;
  padding-left: 1.25rem;
  color: var(--text-default-error);
  font-size: 0.875rem;
}
</style>
