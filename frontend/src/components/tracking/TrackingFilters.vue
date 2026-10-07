<script setup lang="ts">
import type { Assignee, CustomField, FieldFilter, TrackingFilters, TrackingStatus } from "@/types/tracking";

// Filtres du tableau : recherche, statut, affecté à, péremption, puis un
// filtre par champ personnalisé adapté à son type.
const props = defineProps<{
  modelValue: TrackingFilters;
  statuses: TrackingStatus[];
  assignees: Assignee[];
  fields: CustomField[];
}>();
const emit = defineEmits<{ "update:modelValue": [filters: TrackingFilters]; reset: [] }>();

function patch(change: Partial<TrackingFilters>) {
  emit("update:modelValue", { ...props.modelValue, ...change });
}

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
    <div class="tf__field">
      <label for="tf-status">Statut</label>
      <select id="tf-status" class="fr-select" :value="modelValue.statusId" @change="patch({ statusId: ($event.target as HTMLSelectElement).value })">
        <option value="">Tous</option>
        <option v-for="s in statuses" :key="s.id" :value="s.id">{{ s.label }}</option>
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
      <label for="tf-due">Péremption</label>
      <select id="tf-due" class="fr-select" :value="modelValue.due" @change="patch({ due: ($event.target as HTMLSelectElement).value })">
        <option value="">Toutes</option>
        <option value="expired">Expirés</option>
        <option value="7">Dans 7 jours ou moins</option>
        <option value="30">Dans 30 jours ou moins</option>
        <option value="none">Sans date</option>
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
