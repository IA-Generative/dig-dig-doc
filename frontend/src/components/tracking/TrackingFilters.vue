<script setup lang="ts">
import {
  STATUS_CATEGORY_LABELS,
  type Assignee,
  type CustomField,
  type FieldFilter,
  type MockAnalyse,
  type StatusCategory,
  type TrackingFilters,
  type TrackingStatus,
} from "@/types/tracking";

// Filtres du tableau : recherche, statut, affecté à, échéance, puis un
// filtre par champ personnalisé adapté à son type.
const props = defineProps<{
  modelValue: TrackingFilters;
  statuses: TrackingStatus[];
  assignees: Assignee[];
  analyses: MockAnalyse[];
  fields: CustomField[];
  /** Vue transversale : filtre « Analyse » et statuts regroupés par catégorie tant que plusieurs analyses sont concernées. */
  transversal: boolean;
}>();
const emit = defineEmits<{ "update:modelValue": [filters: TrackingFilters]; reset: [] }>();

function patch(change: Partial<TrackingFilters>) {
  emit("update:modelValue", { ...props.modelValue, ...change });
}

function toggleAnalyse(id: string, checked: boolean) {
  const current = props.modelValue.analyseIds;
  // Changer de périmètre peut rendre un statut précis ou un filtre de champ sans objet.
  patch({
    analyseIds: checked ? [...current, id] : current.filter((a) => a !== id),
    statusId: props.modelValue.statusId.startsWith("cat:") ? props.modelValue.statusId : "",
    fieldFilters: {},
  });
}

const categories = Object.entries(STATUS_CATEGORY_LABELS) as [StatusCategory, string][];
/** Un statut précis n'a de sens que pour une seule analyse ; sinon on filtre par catégorie commune. */
const singleAnalyse = () => !props.transversal || props.modelValue.analyseIds.length === 1;

function setField(id: string, value: FieldFilter) {
  patch({ fieldFilters: { ...props.modelValue.fieldFilters, [id]: value } });
}

const textOf = (id: string) => {
  const v = props.modelValue.fieldFilters[id];
  return typeof v === "string" ? v : "";
};
const rangeOf = (id: string) => {
  const v = props.modelValue.fieldFilters[id];
  return typeof v === "object" ? v : { min: "", max: "" };
};
</script>

<template>
  <div class="tf" role="search">
    <div class="tf__field tf__field--wide">
      <label for="tf-search">Rechercher</label>
      <input id="tf-search" class="fr-input" type="search" placeholder="Référence, valeur…" :value="modelValue.search" @input="patch({ search: ($event.target as HTMLInputElement).value })" />
    </div>
    <fieldset v-if="transversal" class="tf__field tf__field--analyses">
      <legend class="tf__label">Analyse</legend>
      <label v-for="a in analyses" :key="a.id" class="tf__check">
        <input type="checkbox" :checked="modelValue.analyseIds.includes(a.id)" @change="toggleAnalyse(a.id, ($event.target as HTMLInputElement).checked)" />
        {{ a.name }}
      </label>
    </fieldset>
    <div class="tf__field">
      <label for="tf-status">Statut</label>
      <select id="tf-status" class="fr-select" :value="modelValue.statusId" @change="patch({ statusId: ($event.target as HTMLSelectElement).value })">
        <option value="">Tous</option>
        <template v-if="singleAnalyse()">
          <option v-for="s in statuses" :key="s.id" :value="s.id">{{ s.label }}</option>
        </template>
        <template v-else>
          <!-- Lien profond vers un statut précis (ex. depuis le tableau de bord) : on le garde visible. -->
          <option v-if="modelValue.statusId && !modelValue.statusId.startsWith('cat:')" :value="modelValue.statusId">
            {{ statuses.find((s) => s.id === modelValue.statusId)?.label }}
          </option>
          <option v-for="[value, label] in categories" :key="value" :value="`cat:${value}`">{{ label }}</option>
        </template>
      </select>
    </div>
    <div class="tf__field">
      <label for="tf-assignee">Affecté à</label>
      <select id="tf-assignee" class="fr-select" :value="modelValue.assignee" @change="patch({ assignee: ($event.target as HTMLSelectElement).value })">
        <option value="">Tous</option>
        <option value="me">Moi</option>
        <option value="none">Non affectés</option>
        <option v-for="a in assignees" :key="a.id" :value="a.id">{{ a.name }}</option>
      </select>
    </div>
    <div class="tf__field">
      <label for="tf-due">Échéance</label>
      <select id="tf-due" class="fr-select" :value="modelValue.due" @change="patch({ due: ($event.target as HTMLSelectElement).value })">
        <option value="">Toutes</option>
        <option value="overdue">Dépassées</option>
        <option value="7">Dans 7 jours ou moins</option>
        <option value="30">Dans 30 jours ou moins</option>
        <option value="none">Sans échéance</option>
      </select>
    </div>

    <div class="tf__field">
      <label for="tf-access">Accès</label>
      <select id="tf-access" class="fr-select" :value="modelValue.access" @change="patch({ access: ($event.target as HTMLSelectElement).value })">
        <option value="">Tous</option>
        <option value="restricted">Restreints</option>
        <option value="analyse">Selon l'analyse</option>
      </select>
    </div>

    <div v-for="f in fields" :key="f.id" class="tf__field">
      <template v-if="f.type === 'number' || f.type === 'amount' || f.type === 'date'">
        <span class="tf__label">{{ f.name }}</span>
        <div class="tf__range">
          <input
            class="fr-input"
            :type="f.type === 'date' ? 'date' : 'number'"
            :aria-label="`${f.name}, minimum`"
            :value="rangeOf(f.id).min"
            @input="setField(f.id, { ...rangeOf(f.id), min: ($event.target as HTMLInputElement).value })"
          />
          <span aria-hidden="true">–</span>
          <input
            class="fr-input"
            :type="f.type === 'date' ? 'date' : 'number'"
            :aria-label="`${f.name}, maximum`"
            :value="rangeOf(f.id).max"
            @input="setField(f.id, { ...rangeOf(f.id), max: ($event.target as HTMLInputElement).value })"
          />
        </div>
      </template>
      <template v-else-if="f.type === 'choice' || f.type === 'boolean'">
        <label :for="`tf-${f.id}`">{{ f.name }}</label>
        <select :id="`tf-${f.id}`" class="fr-select" :value="textOf(f.id)" @change="setField(f.id, ($event.target as HTMLSelectElement).value)">
          <option value="">Tous</option>
          <template v-if="f.type === 'boolean'">
            <option value="true">Oui</option>
            <option value="false">Non</option>
          </template>
          <option v-else v-for="c in f.choices" :key="c" :value="c">{{ c }}</option>
        </select>
      </template>
      <template v-else>
        <label :for="`tf-${f.id}`">{{ f.name }}</label>
        <input :id="`tf-${f.id}`" class="fr-input" type="text" :value="textOf(f.id)" @input="setField(f.id, ($event.target as HTMLInputElement).value)" />
      </template>
    </div>

    <button type="button" class="tf__reset" @click="emit('reset')">Réinitialiser</button>
  </div>
</template>

<style scoped>
.tf {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  align-items: end;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 0.5rem;
  background: var(--background-alt-grey);
}

.tf__field--analyses {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 1rem;
  margin: 0;
  padding: 0;
  border: none;
}

.tf__check {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-weight: 400 !important;
}

.tf__field--wide {
  grid-column: span 2;
}

.tf__field label,
.tf__label {
  display: block;
  margin-bottom: 0.25rem;
  font-size: 0.8125rem;
  font-weight: 600;
}

.tf__range {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.tf__reset {
  justify-self: start;
  padding: 0;
  border: none;
  background: none;
  color: var(--text-action-high-blue-france);
  font: inherit;
  text-decoration: underline;
  cursor: pointer;
}
</style>
