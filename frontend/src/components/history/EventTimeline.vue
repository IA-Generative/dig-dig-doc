<script setup lang="ts">
import { computed } from "vue";

import type { DossierEvent } from "@/types/dossierEvent";
import { categoryOf, dayTitle, describeEvent } from "@/utils/dossierEvents";

// Chronologie du dossier : les événements groupés par jour, du plus récent au plus ancien. Chacun donne son
// type (icône et titre), son détail, son auteur et l'heure ; une action du système n'a pas d'auteur.
const props = defineProps<{
  events: DossierEvent[];
  /** Nom d'un document déposé, à partir de son identifiant (le journal ne garde pas les noms de fichiers). */
  documentName: (documentId: string) => string | undefined;
}>();

const timeOf = (iso: string) => new Date(iso).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
const fullDate = (iso: string) => new Date(iso).toLocaleString("fr-FR", { dateStyle: "full", timeStyle: "medium" });

const groups = computed(() => {
  const out: { title: string; items: { event: DossierEvent; view: ReturnType<typeof describeEvent> }[] }[] = [];
  for (const event of props.events) {
    const title = dayTitle(event.createdAt);
    const view = describeEvent(event, { documentName: props.documentName });
    const last = out[out.length - 1];
    if (last && last.title === title) last.items.push({ event, view });
    else out.push({ title, items: [{ event, view }] });
  }
  return out;
});

const authorOf = (event: DossierEvent) => event.actorName ?? event.actorId ?? "Système";
</script>

<template>
  <div class="tl">
    <section v-for="g in groups" :key="g.title" class="tl__day">
      <h2 class="tl__day-title">{{ g.title }}</h2>
      <ol class="tl__list">
        <li v-for="{ event, view } in g.items" :key="event.id" class="tl__item">
          <span class="tl__icon" aria-hidden="true"><VIcon :name="view.icon" /></span>
          <div class="tl__body">
            <p class="tl__title">
              {{ view.title }}
              <span v-if="categoryOf(event.type)" class="tl__cat">{{ categoryOf(event.type)?.label }}</span>
            </p>
            <p v-if="view.detail" class="tl__detail">{{ view.detail }}</p>
            <p class="tl__meta">
              <span :class="{ 'tl__system': !event.actorId }">{{ authorOf(event) }}</span>
              ·
              <time :datetime="event.createdAt" :title="fullDate(event.createdAt)">{{ timeOf(event.createdAt) }}</time>
            </p>
          </div>
        </li>
      </ol>
    </section>
  </div>
</template>

<style scoped>
.tl__day {
  margin-bottom: 1.5rem;
}

.tl__day-title {
  margin: 0 0 0.5rem;
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--text-mention-grey);
}

.tl__day-title::first-letter {
  text-transform: uppercase;
}

.tl__list {
  position: relative;
  margin: 0;
  padding: 0;
  list-style: none;
}

/* Le fil de la chronologie */
.tl__list::before {
  content: "";
  position: absolute;
  top: 0.5rem;
  bottom: 0.5rem;
  left: 1.0625rem;
  width: 2px;
  background: var(--border-default-grey);
}

.tl__item {
  position: relative;
  display: flex;
  gap: 0.875rem;
  padding: 0.5rem 0;
}

.tl__icon {
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 2.125rem;
  height: 2.125rem;
  border: 2px solid var(--border-default-grey);
  border-radius: 50%;
  background: var(--background-default-grey);
  color: var(--text-action-high-blue-france);
  font-size: 1rem;
}

.tl__body {
  min-width: 0;
}

.tl__title {
  margin: 0;
  font-weight: 700;
}

.tl__cat {
  margin-left: 0.5rem;
  padding: 0 0.5rem;
  border-radius: 0.5rem;
  background: var(--background-alt-grey);
  color: var(--text-mention-grey);
  font-size: 0.75rem;
  font-weight: 400;
}

.tl__detail {
  margin: 0.125rem 0 0;
  font-size: 0.875rem;
}

.tl__meta {
  margin: 0.125rem 0 0;
  font-size: 0.8125rem;
  color: var(--text-mention-grey);
}

.tl__system {
  font-style: italic;
}
</style>
