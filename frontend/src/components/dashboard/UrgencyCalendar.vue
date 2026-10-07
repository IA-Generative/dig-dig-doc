<script setup lang="ts">
import { computed, ref } from "vue";
import UrgencyRow from "@/components/dashboard/UrgencyRow.vue";
import type { DashboardUrgency } from "@/types/dashboard";
import SlotEditorModal from "@/components/dashboard/SlotEditorModal.vue";
import type { SlotDraft } from "@/types/schedule";
import { occurrenceStarts, slotOfUrgency } from "@/utils/recurrence";

const props = defineProps<{ urgencies: DashboardUrgency[]; view: "day" | "month" }>();
const emit = defineEmits<{
  schedule: [dossierId: string, slot: SlotDraft | null];
  "update:view": [view: "day" | "month"];
}>();

const timeOf = (d: Date) => d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });

const MAX_CHIPS = 2;
const HOUR_START = 8;
const HOUR_END = 20;
const HOUR_REM = 2.75;
const HOURS = Array.from({ length: HOUR_END - HOUR_START }, (_, i) => HOUR_START + i);

/** « Jour » (journée heure par heure) ou « Mois » : choisi par le parent. */
const mode = computed(() => props.view);

/** Entrée en cours d'édition (clic sur un bloc de la chronologie). */
const editing = ref<Entry | null>(null);

function onSave(slot: SlotDraft) {
  if (editing.value) emit("schedule", editing.value.u.dossierId, slot);
  editing.value = null;
}

function onRemove() {
  if (editing.value) emit("schedule", editing.value.u.dossierId, null);
  editing.value = null;
}

function openDay(key: string) {
  selectedKey.value = key;
  emit("update:view", "day");
}

/** Ligne rouge de l'heure courante (aujourd'hui seulement, dans la plage affichée). */
const nowTop = computed(() => {
  if (selectedKey.value !== todayKey) return null;
  const h = today.getHours() + today.getMinutes() / 60;
  return h >= HOUR_START && h <= HOUR_END ? `${(h - HOUR_START) * HOUR_REM}rem` : null;
});
const WEEKDAYS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."];

const dayKey = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

const today = new Date();
const todayKey = dayKey(today);

/** Premier jour du mois affiché. */
const month = ref(new Date(today.getFullYear(), today.getMonth(), 1));
const selectedKey = ref(todayKey);

const monthLabel = computed(() =>
  month.value.toLocaleDateString("fr-FR", { month: "long", year: "numeric" }),
);

function shiftMonth(delta: number) {
  month.value = new Date(month.value.getFullYear(), month.value.getMonth() + delta, 1);
}

function goToToday() {
  month.value = new Date(today.getFullYear(), today.getMonth(), 1);
  selectedKey.value = todayKey;
}

/** Une ligne de l'agenda : un dossier, à une occurrence de son créneau ou à son échéance. */
interface Entry {
  u: DashboardUrgency;
  /** Début / fin de l'occurrence ; `null` si le dossier n'est pas planifié. */
  start: Date | null;
  end: Date | null;
  /** Clé stable (un créneau récurrent a une entrée par jour). */
  key: string;
}

/** Plage à couvrir : grille du mois affiché + jour sélectionné (qui peut en sortir). */
const range = computed(() => {
  const first = month.value;
  const offset = (first.getDay() + 6) % 7;
  const gridStart = new Date(first.getFullYear(), first.getMonth(), 1 - offset);
  const gridEnd = new Date(first.getFullYear(), first.getMonth() + 1, 7, 23, 59, 59);
  const [y, m, d] = selectedKey.value.split("-").map(Number);
  const sel = new Date(y, m - 1, d);
  const selEnd = new Date(y, m - 1, d, 23, 59, 59);
  return { from: sel < gridStart ? sel : gridStart, to: selEnd > gridEnd ? selEnd : gridEnd };
});

const byDay = computed(() => {
  const map = new Map<string, Entry[]>();
  const add = (key: string, entry: Entry) => map.set(key, [...(map.get(key) ?? []), entry]);

  for (const u of props.urgencies) {
    if (u.plannedStart && u.plannedEnd) {
      const duration = new Date(u.plannedEnd).getTime() - new Date(u.plannedStart).getTime();
      // Un dossier planifié se place à chaque occurrence de son créneau (une seule s'il ne se répète pas).
      for (const occ of occurrenceStarts(new Date(u.plannedStart), u.recurrence, range.value.from, range.value.to)) {
        add(dayKey(occ), { u, start: occ, end: new Date(occ.getTime() + duration), key: `${u.dossierId}|${occ.toISOString()}` });
      }
    } else {
      add(dayKey(new Date(u.dueAt)), { u, start: null, end: null, key: u.dossierId });
    }
  }
  // Dans une journée : créneaux horaires d'abord (par heure), puis le reste.
  for (const items of map.values()) {
    items.sort((a, b) => (a.start?.getTime() ?? Infinity) - (b.start?.getTime() ?? Infinity));
  }
  return map;
});

/** Grille lundi → dimanche couvrant tout le mois, jours des mois voisins inclus. */
const cells = computed(() => {
  const first = month.value;
  const offset = (first.getDay() + 6) % 7; // lundi = 0
  const daysInMonth = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate();
  const total = Math.ceil((offset + daysInMonth) / 7) * 7;
  return Array.from({ length: total }, (_, i) => {
    const date = new Date(first.getFullYear(), first.getMonth(), i - offset + 1);
    const key = dayKey(date);
    return {
      key,
      day: date.getDate(),
      inMonth: date.getMonth() === first.getMonth(),
      isToday: key === todayKey,
      isPast: key < todayKey,
      items: byDay.value.get(key) ?? [],
      label: date.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" }),
    };
  });
});

const selectedItems = computed(() => byDay.value.get(selectedKey.value) ?? []);
const selectedLabel = computed(() => {
  const [y, m, d] = selectedKey.value.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" });
});

const isSelectedToday = computed(() => selectedKey.value === todayKey);

function selectedDate() {
  const [y, m, d] = selectedKey.value.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function shiftDay(delta: number) {
  const d = selectedDate();
  d.setDate(d.getDate() + delta);
  selectedKey.value = dayKey(d);
  month.value = new Date(d.getFullYear(), d.getMonth(), 1);
}

const plannedItems = computed(() => selectedItems.value.filter((e) => e.start));
const unplannedItems = computed(() => selectedItems.value.filter((e) => !e.start));

/** Aujourd'hui : dossiers en retard et sans créneau, à replanifier en priorité. */
const overdueToReplan = computed(() =>
  isSelectedToday.value
    ? props.urgencies.filter((u) => !u.plannedStart && dayKey(new Date(u.dueAt)) < todayKey)
    : [],
);

/** À planifier : dossiers sans créneau ce jour-là, plus ceux en retard (aujourd'hui). */
const toPlan = computed(() => [...overdueToReplan.value, ...unplannedItems.value.map((e) => e.u)]);
const toPlanOverdue = computed(() => toPlan.value.filter((u) => u.level === "overdue").length);

/** Blocs de la journée : position verticale selon l'heure, colonnes si chevauchement. */
const blocks = computed(() => {
  const laneEnds: number[] = [];
  const placed = plannedItems.value.map((e) => {
    const u = e;
    const start = e.start!;
    const end = e.end!;
    const startH = Math.max(HOUR_START, start.getHours() + start.getMinutes() / 60);
    const endH = Math.min(HOUR_END, end.getHours() + end.getMinutes() / 60);
    let lane = laneEnds.findIndex((e) => e <= startH);
    if (lane === -1) lane = laneEnds.length;
    laneEnds[lane] = endH;
    return { u, startH, endH, lane };
  });
  return placed.map(({ u, startH, endH, lane }) => ({
    e: u,
    style: {
      top: `${(startH - HOUR_START) * HOUR_REM}rem`,
      height: `${Math.max(endH - startH, 0.5) * HOUR_REM}rem`,
      left: `${(lane / laneEnds.length) * 100}%`,
      width: `${100 / laneEnds.length}%`,
    },
  }));
});

function cellLabel(c: (typeof cells.value)[number]) {
  const n = c.items.length;
  return n === 0 ? c.label : `${c.label} : ${n} dossier${n > 1 ? "s" : ""} à traiter`;
}
</script>

<template>
  <div class="cal">
    <div class="cal__toolbar">
      <div v-if="mode === 'month'" class="cal__nav">
        <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary" @click="shiftMonth(-1)">
          <VIcon name="ri-arrow-left-s-line" />
          <span class="fr-sr-only">Mois précédent</span>
        </button>
        <h3 class="cal__month" aria-live="polite">{{ monthLabel }}</h3>
        <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary" @click="shiftMonth(1)">
          <VIcon name="ri-arrow-right-s-line" />
          <span class="fr-sr-only">Mois suivant</span>
        </button>
      </div>
      <div v-else class="cal__nav">
        <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary" @click="shiftDay(-1)">
          <VIcon name="ri-arrow-left-s-line" />
          <span class="fr-sr-only">Jour précédent</span>
        </button>
        <h3 class="cal__month" aria-live="polite">{{ isSelectedToday ? "Aujourd'hui" : selectedLabel }}</h3>
        <button type="button" class="fr-btn fr-btn--sm fr-btn--tertiary" @click="shiftDay(1)">
          <VIcon name="ri-arrow-right-s-line" />
          <span class="fr-sr-only">Jour suivant</span>
        </button>
      </div>
      <button type="button" class="fr-btn fr-btn--sm fr-btn--secondary" @click="goToToday">Aujourd'hui</button>
    </div>

    <!-- Vue Jour : la journée heure par heure -->
    <div v-if="mode === 'day'" class="cal__day-view">
      <div class="cal__timeline" :style="{ height: `${HOURS.length * HOUR_REM}rem` }">
        <div v-for="h in HOURS" :key="h" class="cal__hour" :style="{ height: `${HOUR_REM}rem` }">
          <span class="cal__hour-label">{{ String(h).padStart(2, "0") }}:00</span>
        </div>
        <div v-if="nowTop" class="cal__now" :style="{ top: nowTop }" aria-hidden="true" />
        <div class="cal__blocks">
          <button
            v-for="b in blocks"
            :key="b.e.key"
            type="button"
            class="cal__block"
            :class="b.e.u.level === 'overdue' ? 'cal__block--overdue' : 'cal__block--soon'"
            :style="b.style"
            @click="editing = b.e"
          >
            <span class="cal__block-title">{{ b.e.u.dossierName }}</span>
            <span class="cal__block-time">
              {{ timeOf(b.e.start!) }}–{{ timeOf(b.e.end!) }}
              <VIcon v-if="b.e.u.recurrence" name="ri-repeat-line" aria-label="Se répète" />
            </span>
          </button>
        </div>
      </div>

      <details v-if="toPlan.length" class="cal__toplan">
        <summary>
          À planifier · {{ toPlan.length }}
          <span v-if="toPlanOverdue" class="cal__toplan-late">dont {{ toPlanOverdue }} en retard</span>
        </summary>
        <ul class="cal__list">
          <li v-for="u in toPlan" :key="u.dossierId">
            <UrgencyRow :urgency="u" :default-date="selectedKey" @schedule="(id, slot) => emit('schedule', id, slot)" />
          </li>
        </ul>
      </details>
    </div>

    <!-- Vue Mois -->
    <template v-else>
    <div class="cal__grid" role="grid" :aria-label="`Calendrier de ${monthLabel}`">
      <div v-for="w in WEEKDAYS" :key="w" class="cal__weekday" role="columnheader">{{ w }}</div>
      <button
        v-for="c in cells"
        :key="c.key"
        type="button"
        role="gridcell"
        class="cal__cell"
        :class="{
          'cal__cell--out': !c.inMonth,
          'cal__cell--today': c.isToday,
          'cal__cell--selected': c.key === selectedKey,
        }"
        :aria-label="cellLabel(c)"
        :aria-selected="c.key === selectedKey"
        @click="openDay(c.key)"
      >
        <span class="cal__day">{{ c.day }}</span>
        <span v-if="c.items.length" class="cal__chips" aria-hidden="true">
          <span
            v-for="e in c.items.slice(0, MAX_CHIPS)"
            :key="e.key"
            class="cal__chip"
            :class="e.u.level === 'overdue' ? 'cal__chip--overdue' : 'cal__chip--soon'"
          ><span v-if="e.start" class="cal__chip-time">{{ timeOf(e.start) }}</span>{{ e.u.dossierName }}</span>
          <span v-if="c.items.length > MAX_CHIPS" class="cal__more">+{{ c.items.length - MAX_CHIPS }} autre{{ c.items.length - MAX_CHIPS > 1 ? "s" : "" }}</span>
        </span>
        <span v-if="c.items.length" class="cal__dot" aria-hidden="true">{{ c.items.length }}</span>
      </button>
    </div>

    </template>

    <SlotEditorModal
      v-if="editing"
      :dossier-name="editing.u.dossierName"
      :dossier-id="editing.u.dossierId"
      :initial="slotOfUrgency(editing.u)"
      :default-date="selectedKey"
      @save="onSave"
      @remove="onRemove"
      @close="editing = null"
    />
  </div>
</template>

<style scoped>
.cal__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.cal__timeline {
  position: relative;
  border-top: 1px solid var(--border-default-grey);
}

.cal__hour {
  box-sizing: border-box;
  border-bottom: 1px solid var(--border-default-grey);
}

.cal__hour-label {
  display: inline-block;
  width: 3.25rem;
  padding: 0.125rem 0.25rem;
  font-size: 0.75rem;
  color: var(--text-mention-grey);
}

.cal__blocks {
  position: absolute;
  inset: 0 0 0 3.5rem;
}

.cal__block {
  position: absolute;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
  padding: 0.25rem 0.5rem;
  border: none;
  border-left: 4px solid;
  border-radius: 0.375rem;
  color: var(--text-default-grey);
  font: inherit;
  font-size: 0.8125rem;
  text-align: left;
  cursor: pointer;
}

.cal__now {
  position: absolute;
  left: 3.25rem;
  right: 0;
  height: 2px;
  background: var(--background-flat-error);
  z-index: 2;
  pointer-events: none;
}

.cal__now::before {
  content: "";
  position: absolute;
  left: -0.3125rem;
  top: -0.25rem;
  width: 0.625rem;
  height: 0.625rem;
  border-radius: 50%;
  background: var(--background-flat-error);
}

.cal__toplan {
  margin-top: 1.25rem;
}

.cal__toplan > summary {
  cursor: pointer;
  font-weight: 600;
}

.cal__toplan-late {
  margin-left: 0.5rem;
  font-weight: 400;
  color: var(--text-default-error);
}

.cal__toplan .cal__list {
  margin-top: 0.5rem;
}

.cal__block--overdue {
  border-color: var(--background-flat-error);
  background: var(--background-contrast-error);
}

.cal__block--soon {
  border-color: var(--background-flat-warning);
  background: var(--background-contrast-warning);
}

.cal__block-time {
  font-size: 0.75rem;
  font-weight: 700;
}

.cal__block-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cal__nav {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.cal__month {
  min-width: 10rem;
  margin: 0;
  font-size: 1.125rem;
  text-align: center;
}

.cal__month::first-letter {
  text-transform: uppercase;
}

.cal__grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  border-top: 1px solid var(--border-default-grey);
  border-left: 1px solid var(--border-default-grey);
}

.cal__weekday {
  padding: 0.375rem;
  border-right: 1px solid var(--border-default-grey);
  border-bottom: 1px solid var(--border-default-grey);
  background: var(--background-alt-grey);
  font-size: 0.75rem;
  font-weight: 700;
  text-align: center;
  text-transform: uppercase;
  color: var(--text-mention-grey);
}

.cal__cell {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.25rem;
  min-height: 6.5rem;
  padding: 0.375rem;
  border: none;
  border-right: 1px solid var(--border-default-grey);
  border-bottom: 1px solid var(--border-default-grey);
  background: var(--background-default-grey);
  color: var(--text-default-grey);
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  min-width: 0;
}

.cal__cell:hover {
  background: var(--background-alt-grey-hover);
}

.cal__cell--out {
  background: var(--background-alt-grey);
  color: var(--text-disabled-grey);
}

.cal__cell--selected {
  outline: 2px solid var(--border-active-blue-france);
  outline-offset: -2px;
  z-index: 1;
}

.cal__day {
  align-self: flex-start;
  min-width: 1.5rem;
  padding: 0 0.25rem;
  border-radius: 0.75rem;
  font-size: 0.8125rem;
  font-weight: 600;
  line-height: 1.5rem;
  text-align: center;
}

.cal__cell--today .cal__day {
  background: var(--background-action-high-blue-france);
  color: var(--text-inverted-blue-france);
}

.cal__chips {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
}

.cal__chip {
  overflow: hidden;
  padding: 0.0625rem 0.375rem;
  border-left: 3px solid;
  border-radius: 0.25rem;
  font-size: 0.6875rem;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cal__chip--overdue {
  border-color: var(--background-flat-error);
  background: var(--background-contrast-error);
}

.cal__chip--soon {
  border-color: var(--background-flat-warning);
  background: var(--background-contrast-warning);
}

.cal__chip-time {
  margin-right: 0.375rem;
  font-weight: 700;
}

.cal__more {
  font-size: 0.6875rem;
  color: var(--text-mention-grey);
}

/* Petits écrans : le nombre remplace les pastilles */
.cal__dot {
  display: none;
  align-self: center;
  min-width: 1.25rem;
  border-radius: 0.625rem;
  background: var(--background-flat-info);
  color: var(--text-inverted-info);
  font-size: 0.6875rem;
  font-weight: 700;
  line-height: 1.25rem;
  text-align: center;
}

@media (max-width: 48em) {
  .cal__cell {
    min-height: 3.5rem;
  }

  .cal__chips {
    display: none;
  }

  .cal__dot {
    display: block;
  }
}

.cal__list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
</style>
