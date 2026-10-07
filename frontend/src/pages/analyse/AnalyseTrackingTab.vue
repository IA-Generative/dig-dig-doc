<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import BulkAccessModal from "@/components/access/BulkAccessModal.vue";
import BulkAssignBar from "@/components/tracking/BulkAssignBar.vue";
import ColumnsModal from "@/components/tracking/ColumnsModal.vue";
import CustomFieldsModal from "@/components/tracking/CustomFieldsModal.vue";
import TrackingFiltersPanel from "@/components/tracking/TrackingFilters.vue";
import TrackingTable from "@/components/tracking/TrackingTable.vue";
import TrackingViewsBar from "@/components/tracking/TrackingViewsBar.vue";
import { useAuth } from "@/composables/useAuth";
import { useDossierAccess } from "@/composables/useDossierAccess";
import { useTracking } from "@/composables/useTracking";
import { BUILT_IN_VIEWS, useTrackingPrefs } from "@/composables/useTrackingPrefs";
import type { DossierAccess } from "@/types/access";
import {
  emptyFilters,
  type ColumnId,
  type CustomValue,
  type TrackingFilters,
  type TrackingRow,
  type TrackingSort,
} from "@/types/tracking";
import { downloadCsv, toCsv } from "@/utils/csv";
import { dueInfo } from "@/utils/due";
import { formatValue } from "@/utils/trackingFields";

// Onglet « Suivi » d'une analyse : tableau de pilotage des dossiers
// (affectations, statuts, échéance, colonnes personnalisées). Données
// simulées (useTracking) en attendant l'API (#168, #172, #173).

const route = useRoute();
const { isAdmin } = useAuth();
const analyseId = computed(() => String(route.params.id));

const { fields, statuses, assignees, query, queryAll, assign, setValue, assigneeName } = useTracking();
const prefs = useTrackingPrefs(analyseId, fields);
const { memberHasAccess, setAccess } = useDossierAccess();

const PAGE_SIZE = 10;

const activeViewId = ref("all");
const filters = ref<TrackingFilters>(emptyFilters());
const sort = ref<TrackingSort>({ key: "due", dir: "asc" });
const page = ref(1);

const rows = ref<TrackingRow[]>([]);
const total = ref(0);
const loading = ref(false);
const selected = ref<string[]>([]);

const filtersOpen = ref(false);
const columnsOpen = ref(false);
const bulkAccessOpen = ref(false);
const fieldsOpen = ref(false);
const notice = ref("");

const activeView = computed(() => prefs.views.value.find((v) => v.id === activeViewId.value) ?? BUILT_IN_VIEWS[0]);
const modified = computed(
  () =>
    JSON.stringify(filters.value) !== JSON.stringify(activeView.value.filters) ||
    JSON.stringify(sort.value) !== JSON.stringify(activeView.value.sort),
);

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)));
const pages = computed(() => Array.from({ length: pageCount.value }, (_, i) => ({ label: String(i + 1), title: `Page ${i + 1}` })));

let requestSeq = 0;
async function load() {
  const seq = ++requestSeq;
  loading.value = true;
  const result = await query(filters.value, sort.value, page.value, PAGE_SIZE);
  if (seq !== requestSeq) return; // une requête plus récente est partie
  rows.value = result.rows;
  total.value = result.total;
  loading.value = false;
}

watch([filters, sort, page], load, { deep: true });
// Un changement de filtre ou de tri ramène à la première page.
watch([filters, sort], () => (page.value = 1), { deep: true });

function applyView(id: string) {
  const view = prefs.views.value.find((v) => v.id === id);
  if (!view) return;
  activeViewId.value = id;
  filters.value = JSON.parse(JSON.stringify(view.filters));
  sort.value = { ...view.sort };
  selected.value = [];
}

onMounted(() => {
  // Liens profonds (ex. depuis le tableau de bord) : ?status=…&due=…&assignee=me
  const q = route.query;
  const fromUrl: Partial<TrackingFilters> = {};
  if (typeof q.status === "string") fromUrl.statusId = q.status;
  if (typeof q.due === "string") fromUrl.due = q.due;
  if (typeof q.assignee === "string") fromUrl.assignee = q.assignee;
  if (Object.keys(fromUrl).length) filters.value = { ...emptyFilters(), ...fromUrl };
  load();
});

function resetFilters() {
  filters.value = emptyFilters();
}

function saveView(name: string) {
  const view = prefs.saveView(name, filters.value, sort.value);
  activeViewId.value = view.id;
  announce(`Vue « ${view.name} » enregistrée.`);
}

function deleteView(id: string) {
  prefs.deleteView(id);
  if (activeViewId.value === id) applyView("all");
}

let noticeTimer: ReturnType<typeof setTimeout> | undefined;
function announce(message: string) {
  notice.value = message;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => (notice.value = ""), 5000);
}

function onAssign(ids: string[], assigneeId: string | null) {
  // On n'affecte qu'une personne qui a accès au dossier (#177).
  if (assigneeId) {
    const refused = ids.filter((id) => !memberHasAccess(id, assigneeId));
    if (refused.length) {
      announce(`${refused.length} dossier${refused.length > 1 ? "s" : ""} non affecté${refused.length > 1 ? "s" : ""} : ${assigneeName(assigneeId)} n'y a pas accès.`);
      ids = ids.filter((id) => !refused.includes(id));
      if (ids.length === 0) return;
    }
  }
  assign(ids, assigneeId);
  announce(
    `${ids.length} dossier${ids.length > 1 ? "s" : ""} ${assigneeId ? `affecté${ids.length > 1 ? "s" : ""} à ${assigneeName(assigneeId)}` : "désaffecté" + (ids.length > 1 ? "s" : "")}. Tracé dans l'historique.`,
  );
  selected.value = [];
  load();
}

function onSetValue(rowId: string, fieldId: string, value: CustomValue, done: (error: string | null) => void) {
  const error = setValue(rowId, fieldId, value);
  done(error);
  if (!error) {
    announce("Valeur enregistrée. Tracée dans l'historique du dossier.");
    load();
  }
}

/** Applique un accès à la sélection ; les affectations des personnes qui perdent l'accès sont annulées. */
function onBulkAccess(next: DossierAccess) {
  let cancelled = 0;
  for (const id of selected.value) {
    setAccess(id, next);
    const row = rows.value.find((r) => r.id === id);
    if (row?.assigneeId && !memberHasAccess(id, row.assigneeId)) {
      assign([id], null);
      cancelled++;
    }
  }
  announce(
    `Accès défini pour ${selected.value.length} dossier${selected.value.length > 1 ? "s" : ""}.${cancelled ? ` ${cancelled} affectation${cancelled > 1 ? "s" : ""} annulée${cancelled > 1 ? "s" : ""}.` : ""} Tracé dans l'historique.`,
  );
  bulkAccessOpen.value = false;
  selected.value = [];
  load();
}

function onColumnsSaved(order: ColumnId[], hidden: ColumnId[]) {
  prefs.setColumns(order, hidden);
  columnsOpen.value = false;
}

function onColumnsReset() {
  prefs.resetColumns();
  columnsOpen.value = false;
}

/** Export CSV de la vue courante (filtres et tri appliqués, colonnes visibles). */
function exportCsv() {
  const cols = prefs.visibleColumns.value;
  const all = queryAll(filters.value, sort.value);
  const cell = (r: TrackingRow, id: ColumnId): string => {
    switch (id) {
      case "reference":
        return r.reference;
      case "status":
        return statuses.find((s) => s.id === r.statusId)?.label ?? "";
      case "assignee":
        return assigneeName(r.assigneeId);
      case "due":
        return r.dueAt ? `${new Date(r.dueAt).toLocaleDateString("fr-FR")} (${dueInfo(r.dueAt).label})` : "";
      case "createdAt":
        return new Date(r.createdAt).toLocaleDateString("fr-FR");
      case "lastActivityAt":
        return new Date(r.lastActivityAt).toLocaleDateString("fr-FR");
      default: {
        const f = fields.value.find((x) => `field:${x.id}` === id);
        return f ? formatValue(f, r.values[f.id]).replace("—", "") : "";
      }
    }
  };
  downloadCsv(
    `suivi-dossiers-${new Date().toISOString().slice(0, 10)}.csv`,
    toCsv(cols.map((c) => c.label), all.map((r) => cols.map((c) => cell(r, c.id)))),
  );
  announce(`${all.length} ligne${all.length > 1 ? "s" : ""} exportée${all.length > 1 ? "s" : ""}.`);
}
</script>

<template>
  <div class="track">
    <div class="track__top">
      <TrackingViewsBar
        :views="prefs.views.value"
        :active-id="activeViewId"
        :modified="modified"
        @select="applyView"
        @save="saveView"
        @delete="deleteView"
      />

      <div class="track__tools">
        <button type="button" class="track__tool" :aria-expanded="filtersOpen" @click="filtersOpen = !filtersOpen">
          <VIcon name="ri-filter-3-line" /> Filtres
        </button>
        <button type="button" class="track__tool" @click="columnsOpen = true"><VIcon name="ri-layout-column-line" /> Colonnes</button>
        <button v-if="isAdmin" type="button" class="track__tool" @click="fieldsOpen = true">
          <VIcon name="ri-table-line" /> Champs personnalisés
        </button>
        <button type="button" class="track__tool" @click="exportCsv"><VIcon name="ri-download-2-line" /> Exporter en CSV</button>
      </div>
    </div>

    <TrackingFiltersPanel
      v-if="filtersOpen"
      v-model="filters"
      :statuses="statuses"
      :assignees="assignees"
      :fields="fields"
      @reset="resetFilters"
    />

    <BulkAssignBar
      v-if="selected.length"
      :count="selected.length"
      :assignees="assignees"
      :can-set-access="isAdmin"
      @assign="(id) => onAssign(selected, id)"
      @set-access="bulkAccessOpen = true"
      @clear="selected = []"
    />

    <p class="track__count" aria-live="polite">{{ total }} dossier{{ total > 1 ? "s" : "" }}</p>

    <TrackingTable
      v-model:sort="sort"
      v-model:selected="selected"
      :rows="rows"
      :columns="prefs.visibleColumns.value"
      :fields="fields"
      :assignees="assignees"
      :loading="loading"
      :can-assign="memberHasAccess"
      @assign="(id, assigneeId) => onAssign([id], assigneeId)"
      @set-value="onSetValue"
    />

    <DsfrPagination v-if="pageCount > 1" v-model:current-page="page" :pages="pages" class="track__pagination" />

    <p class="track__notice" role="status">{{ notice }}</p>

    <ColumnsModal
      v-if="columnsOpen"
      :columns="prefs.allColumns.value"
      :hidden="prefs.hiddenColumns.value"
      @save="onColumnsSaved"
      @reset="onColumnsReset"
      @close="columnsOpen = false"
    />
    <BulkAccessModal v-if="bulkAccessOpen" :count="selected.length" @apply="onBulkAccess" @close="bulkAccessOpen = false" />
    <CustomFieldsModal v-if="fieldsOpen" @close="fieldsOpen = false" @saved="announce" />
  </div>
</template>

<style scoped>
.track {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.track__top {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.track__tools {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 1rem;
}

.track__tool {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0;
  border: none;
  background: none;
  color: var(--text-action-high-blue-france);
  font: inherit;
  font-size: 0.875rem;
  cursor: pointer;
}

.track__count {
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-mention-grey);
}

.track__pagination {
  margin-top: 0.5rem;
}

.track__notice {
  min-height: 1.25rem;
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-default-success);
}
</style>
