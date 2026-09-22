<script setup lang="ts">
import { computed, ref } from "vue";

import type { Analyse } from "@/types/analyse";
import type { Dossier } from "@/types/dossier";

const props = defineProps<{ dossier: Dossier; analyse?: Analyse }>();

const classificationStep = computed(() => props.dossier.executionSteps.find((s) => s.kind === "classification"));
const extractionStep = computed(() => props.dossier.executionSteps.find((s) => s.kind === "extraction"));
const agentSteps = computed(() => props.dossier.executionSteps.filter((s) => s.kind === "agent" && !!s.output));

const classificationResult = computed(() => {
  const output = classificationStep.value?.output;
  if (!output) return undefined;
  const match = output.match(/^(.*) \(confiance : (\d+)%\)$/);
  if (!match) return { label: output, confidence: undefined as number | undefined };
  return { label: match[1], confidence: Number(match[2]) };
});

const extractionResult = computed(() => {
  const output = extractionStep.value?.output;
  if (!output || !output.includes(" : ")) return undefined;
  return output.split(" · ").map((pair) => {
    const [name, value] = pair.split(" : ");
    return { name, value };
  });
});

type ResultCardKind = "classification" | "extraction" | "agent";

interface ResultCard {
  id: string;
  kind: ResultCardKind;
  icon: string;
  title: string;
  preview: string;
  pending: boolean;
}

function extractionPreview(): string {
  if (extractionResult.value) {
    const count = extractionResult.value.length;
    return `${count} ${count > 1 ? "entités" : "entité"}`;
  }
  return extractionStep.value?.output ?? "En attente";
}

function classificationPreview(): string {
  if (classificationResult.value) return classificationResult.value.label;
  return classificationStep.value?.output ?? "En attente";
}

const cards = computed<ResultCard[]>(() => {
  const items: ResultCard[] = [
    {
      id: "classification",
      kind: "classification",
      icon: "ri-price-tag-3-line",
      title: "Classification",
      pending: !classificationStep.value,
      preview: classificationPreview(),
    },
    {
      id: "extraction",
      kind: "extraction",
      icon: "ri-braces-line",
      title: "Entités",
      pending: !extractionStep.value,
      preview: extractionPreview(),
    },
  ];
  agentSteps.value.forEach((step) => {
    items.push({
      id: step.id,
      kind: "agent",
      icon: "ri-robot-line",
      title: step.label,
      pending: false,
      preview: step.output ?? "",
    });
  });
  return items;
});

const selectedCardId = ref<string | undefined>(undefined);
const isDetailOpened = ref(false);
const selectedCard = computed(() => cards.value.find((c) => c.id === selectedCardId.value));

function openDetail(card: ResultCard) {
  if (card.pending) return;
  selectedCardId.value = card.id;
  isDetailOpened.value = true;
}

const carouselRef = ref<HTMLElement | null>(null);
function scrollCarousel(direction: 1 | -1) {
  carouselRef.value?.scrollBy({ left: direction * 240, behavior: "smooth" });
}
</script>

<template>
  <div class="dossier-results">
    <button
      type="button"
      class="dossier-results__nav dossier-results__nav--prev"
      aria-label="Résultats précédents"
      @click="scrollCarousel(-1)"
    >
      <VIcon name="ri-arrow-left-s-line" />
    </button>

    <div ref="carouselRef" class="dossier-results__carousel">
      <button
        v-for="card in cards"
        :key="card.id"
        type="button"
        class="dossier-results__card"
        :class="{
          'dossier-results__card--agent': card.kind === 'agent',
          'dossier-results__card--pending': card.pending,
        }"
        :disabled="card.pending"
        @click="openDetail(card)"
      >
        <span class="dossier-results__icon" :class="{ 'dossier-results__icon--agent': card.kind === 'agent' }">
          <VIcon :name="card.icon" />
        </span>
        <span class="dossier-results__card-title">{{ card.title }}</span>
        <span class="fr-text--sm dossier-results__card-preview">{{ card.preview }}</span>
      </button>
    </div>

    <button
      type="button"
      class="dossier-results__nav dossier-results__nav--next"
      aria-label="Résultats suivants"
      @click="scrollCarousel(1)"
    >
      <VIcon name="ri-arrow-right-s-line" />
    </button>

    <DsfrModal
      v-if="selectedCard"
      v-model:opened="isDetailOpened"
      :title="selectedCard.title"
      :icon="selectedCard.icon"
    >
      <template v-if="selectedCard.kind === 'classification'">
        <p class="dossier-results__detail-label">{{ classificationResult?.label }}</p>
        <div v-if="classificationResult?.confidence !== undefined" class="dossier-results__gauge">
          <div class="dossier-results__gauge-track">
            <div class="dossier-results__gauge-fill" :style="{ width: `${classificationResult.confidence}%` }" />
          </div>
          <span class="fr-text--sm dossier-results__gauge-value">{{ classificationResult.confidence }}%</span>
        </div>
      </template>

      <dl v-else-if="selectedCard.kind === 'extraction' && extractionResult" class="dossier-results__entities">
        <div v-for="entity in extractionResult" :key="entity.name" class="dossier-results__entity">
          <dt class="fr-text--sm dossier-results__entity-name">{{ entity.name }}</dt>
          <dd class="dossier-results__entity-value">{{ entity.value }}</dd>
        </div>
      </dl>

      <p v-else class="dossier-results__agent-output">{{ selectedCard.preview }}</p>

      <RouterLink
        v-if="selectedCard.kind !== 'agent'"
        :to="`/analyses/${dossier.analyseId}`"
        class="fr-link fr-text--sm dossier-results__config-link"
      >
        Voir la configuration
      </RouterLink>
    </DsfrModal>
  </div>
</template>

<style scoped>
.dossier-results {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.dossier-results__nav {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 50%;
  background: var(--background-default-grey);
  cursor: pointer;
}

.dossier-results__nav:hover {
  background: var(--background-alt-grey-hover);
}

.dossier-results__carousel {
  flex: 1;
  display: flex;
  gap: 1rem;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  padding: 0.25rem;
}

.dossier-results__card {
  scroll-snap-align: start;
  flex: 0 0 auto;
  width: 12rem;
  background: var(--background-default-grey);
  border: 1px solid var(--border-default-grey);
  border-radius: 0.75rem;
  padding: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
  cursor: pointer;
  text-align: left;
  transition:
    box-shadow 0.15s ease,
    transform 0.15s ease;
}

.dossier-results__card:hover:not(:disabled) {
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.dossier-results__card--pending {
  cursor: default;
  opacity: 0.6;
}

.dossier-results__card--agent {
  border-left: 3px solid #5b4fd1;
}

.dossier-results__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.65rem;
  background: linear-gradient(135deg, #6a5cff1a 0%, #ff6ca01a 100%);
  color: #4b3fd9;
  flex-shrink: 0;
}

.dossier-results__icon--agent {
  background: linear-gradient(135deg, #5b4fd11a 0%, #d1477a1a 100%);
}

.dossier-results__card-title {
  font-weight: bold;
}

.dossier-results__card-preview {
  color: var(--text-mention-grey);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.dossier-results__detail-label {
  font-size: 1.25rem;
  font-weight: bold;
  margin: 0 0 0.75rem;
}

.dossier-results__gauge {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.dossier-results__gauge-track {
  flex: 1;
  height: 0.5rem;
  border-radius: 999px;
  background: var(--background-alt-grey);
  overflow: hidden;
}

.dossier-results__gauge-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #5b4fd1 0%, #8b4fd6 50%, #d1477a 100%);
}

.dossier-results__gauge-value {
  font-weight: bold;
  white-space: nowrap;
}

.dossier-results__entities {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.dossier-results__entity {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border-default-grey);
}

.dossier-results__entity:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.dossier-results__entity-name {
  color: var(--text-mention-grey);
}

.dossier-results__entity-value {
  margin: 0;
  font-weight: bold;
  text-align: right;
}

.dossier-results__agent-output {
  margin: 0;
  white-space: pre-wrap;
}

.dossier-results__config-link {
  display: inline-block;
  margin-top: 1rem;
}
</style>
