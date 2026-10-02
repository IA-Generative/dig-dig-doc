<script setup lang="ts">
import { computed, ref, watch } from "vue";

import FieldValueEditor from "@/components/documents/FieldValueEditor.vue";
import {
  FIELD_ORIGIN_LABELS,
  FIELD_STATUS_LABELS,
  textToValue,
  valueToText,
  type DraftField,
  type FieldValue,
} from "@/types/documentDraft";
import { METADATA_KEY_LABELS, SOURCE_KIND_LABELS, type MetadataKey } from "@/types/documentTemplate";

// Un champ du brouillon, pour la revue : sa valeur courante, son statut, d'où elle vient (sources lisibles), et ce
// qu'on peut en faire : valider telle quelle, modifier, rejeter, régénérer (consigne facultative), voir l'historique.
// Une valeur validée n'est jamais réécrite par l'agent : elle ne se change qu'à la main.
const props = defineProps<{
  field: DraftField;
  /** Brouillon modifiable (ni archivé) et aucune écriture en cours. */
  editable: boolean;
  /** L'agent est en train de générer : régénérer est indisponible. */
  generating: boolean;
  /** Le champ est mis en avant (obligatoire et pas encore validé). */
  attention: boolean;
}>();

const emit = defineEmits<{
  validate: [];
  reject: [reason: string];
  save: [value: FieldValue, reason: string];
  regenerate: [instruction: string];
  history: [];
}>();

type Mode = "view" | "edit" | "reject" | "regenerate";
const mode = ref<Mode>("view");
const draft = ref("");
const reason = ref("");
const showSources = ref(false);

const status = computed(() => props.field.current.status);
const displayValue = computed(() => valueToText(props.field.current.value, props.field.type));
const isMetadata = computed(() => props.field.source.kind === "dossier_metadata");
// Posés à la génération du fichier (date du jour, numéro de version du document) : rien à relire ni à valider ici.
const setAtGeneration = computed(() => {
  const source = props.field.source as { kind: string; key?: string };
  return source.kind === "dossier_metadata" && (source.key === "generated_at" || source.key === "document_version");
});
const canRegenerate = computed(() => status.value !== "validé" && !isMetadata.value);

const badgeType = computed(() => ({ non_renseigné: "new", proposé: "info", validé: "success" })[status.value] as "new" | "info" | "success");

const originText = computed(() => {
  const version = props.field.current;
  if (status.value === "non_renseigné" && version.versionNumber === 1) return "Aucune valeur pour l'instant";
  // « Donnée de l'analyse » dit déjà d'où elle vient pour un champ tiré de l'analyse ; un fait du dossier ou une
  // valeur déjà renseignée par un autre document se disent autrement.
  if (version.origin === "analysis") {
    const kind = props.field.source.kind;
    if (kind === "dossier_metadata") return "Métadonnée du dossier";
    if (kind === "instruction") return "Déjà renseignée pour ce dossier";
    return FIELD_ORIGIN_LABELS.analysis;
  }
  let text = FIELD_ORIGIN_LABELS[version.origin];
  if (version.origin === "agent" && (version.promptVersion || version.model)) {
    text += ` (prompt ${version.promptVersion ?? "?"}${version.model ? `, ${version.model}` : ""})`;
  }
  return text;
});

const sourceSentence = computed(() => {
  const source = props.field.source as { kind: string; key?: MetadataKey };
  if (source.kind === "dossier_metadata" && source.key) return `${SOURCE_KIND_LABELS.dossier_metadata} : ${METADATA_KEY_LABELS[source.key]}`;
  return SOURCE_KIND_LABELS[source.kind as keyof typeof SOURCE_KIND_LABELS] ?? source.kind;
});

function startEdit() {
  draft.value = displayValue.value;
  reason.value = "";
  mode.value = "edit";
}

function save() {
  emit("save", textToValue(draft.value, props.field.type), reason.value.trim());
  mode.value = "view";
}

function confirmReject() {
  emit("reject", reason.value.trim());
  mode.value = "view";
}

function confirmRegenerate() {
  emit("regenerate", reason.value.trim());
  mode.value = "view";
}

// Une mise à jour du champ venue du serveur (validation, régénération terminée…) referme tout formulaire ouvert.
watch(
  () => props.field.current.id,
  () => (mode.value = "view"),
);
</script>

<template>
  <li class="draft-field" :class="{ 'draft-field--attention': attention }">
    <div class="draft-field__header">
      <strong class="draft-field__label">{{ field.label }}</strong>
      <DsfrBadge v-if="setAtGeneration" label="Posé à la génération" type="new" small />
      <template v-else>
        <DsfrBadge :label="FIELD_STATUS_LABELS[status]" :type="badgeType" small />
        <DsfrBadge v-if="field.required" label="Obligatoire" type="info" small />
      </template>
      <DsfrBadge v-if="field.stale" label="Source modifiée depuis la révision" type="warning" small />
    </div>

    <!-- Valeur courante -->
    <template v-if="mode === 'view'">
      <p v-if="setAtGeneration" class="draft-field__value draft-field__value--empty">
        Écrit automatiquement quand le document est généré.
      </p>
      <p v-else-if="displayValue" class="draft-field__value">{{ displayValue }}</p>
      <p v-else class="draft-field__value draft-field__value--empty">Pas de valeur</p>
      <p class="fr-text--sm draft-field__origin">
        {{ originText }}<template v-if="field.current.origin !== 'analysis'"> · {{ sourceSentence }}</template>
        <button
          v-if="field.sourceDetails.length"
          type="button"
          class="fr-link fr-link--sm draft-field__sources-toggle"
          :aria-expanded="showSources"
          @click="showSources = !showSources"
        >
          {{ showSources ? "Masquer les sources" : `Sources (${field.sourceDetails.length})` }}
        </button>
      </p>
      <ul v-if="showSources" class="draft-field__sources">
        <li v-for="(source, index) in field.sourceDetails" :key="index">
          <strong>{{ source.label }}</strong
          ><span v-if="source.page"> · page {{ source.page }}</span>
          <span v-if="source.text"> : {{ source.text }}</span>
        </li>
      </ul>
      <p v-if="field.instruction" class="fr-text--xs draft-field__instruction">Consigne : {{ field.instruction }}</p>
    </template>

    <!-- Modifier -->
    <div v-else-if="mode === 'edit'" class="draft-field__form">
      <FieldValueEditor v-model="draft" :type="field.type" label="Valeur" />
      <DsfrInput v-model="reason" label="Motif (facultatif)" label-visible />
      <div class="draft-field__actions">
        <DsfrButton label="Enregistrer et valider" size="sm" @click="save" />
        <DsfrButton label="Annuler" tertiary size="sm" @click="mode = 'view'" />
      </div>
    </div>

    <!-- Rejeter -->
    <div v-else-if="mode === 'reject'" class="draft-field__form">
      <DsfrInput v-model="reason" label="Pourquoi rejeter cette valeur ? (facultatif)" label-visible />
      <div class="draft-field__actions">
        <DsfrButton label="Rejeter la valeur" size="sm" @click="confirmReject" />
        <DsfrButton label="Annuler" tertiary size="sm" @click="mode = 'view'" />
      </div>
    </div>

    <!-- Régénérer -->
    <div v-else class="draft-field__form">
      <DsfrInput
        v-model="reason"
        label="Consigne pour l'agent (facultative)"
        label-visible
        hint="Par exemple : plus court, ton plus neutre. Les autres champs ne changent pas."
      />
      <div class="draft-field__actions">
        <DsfrButton label="Régénérer ce champ" size="sm" @click="confirmRegenerate" />
        <DsfrButton label="Annuler" tertiary size="sm" @click="mode = 'view'" />
      </div>
    </div>

    <div v-if="mode === 'view' && !setAtGeneration" class="draft-field__actions">
      <DsfrButton v-if="status === 'proposé'" label="Valider" size="sm" :disabled="!editable" @click="emit('validate')" />
      <DsfrButton :label="status === 'validé' ? 'Modifier' : 'Modifier / saisir'" secondary size="sm" :disabled="!editable" @click="startEdit" />
      <DsfrButton v-if="status === 'proposé'" label="Rejeter" tertiary size="sm" :disabled="!editable" @click="mode = 'reject'" />
      <DsfrButton
        v-if="canRegenerate"
        label="Régénérer"
        tertiary
        size="sm"
        icon="ri-sparkling-2-fill"
        :disabled="!editable || generating"
        @click="mode = 'regenerate'"
      />
      <DsfrButton label="Historique" tertiary no-outline size="sm" icon="ri-history-line" @click="emit('history')" />
    </div>
  </li>
</template>

<style scoped>
.draft-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 0.375rem;
  background: var(--background-default-grey);
  list-style: none;
}

.draft-field--attention {
  border-left: 4px solid var(--border-plain-warning, #b34000);
}

.draft-field__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.draft-field__label {
  font-size: 1rem;
}

.draft-field__value {
  margin: 0;
  white-space: pre-wrap;
  font-size: 1rem;
}

.draft-field__value--empty {
  color: var(--text-mention-grey);
  font-style: italic;
}

.draft-field__origin,
.draft-field__instruction {
  margin: 0;
  color: var(--text-mention-grey);
}

.draft-field__sources-toggle {
  margin-left: 0.5rem;
  background: none;
  border: none;
  cursor: pointer;
}

.draft-field__sources {
  margin: 0;
  padding: 0.5rem 0.75rem 0.5rem 1.5rem;
  background: var(--background-alt-grey);
  border-radius: 0.25rem;
  font-size: 0.875rem;
}

.draft-field__form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.draft-field__actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
</style>
