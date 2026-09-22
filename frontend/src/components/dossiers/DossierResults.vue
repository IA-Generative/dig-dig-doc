<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";

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
  if (!match) return { label: output, confidence: undefined };
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
</script>

<template>
  <div class="dossier-results">
    <div class="dossier-results__card">
      <div class="dossier-results__card-header">
        <span class="dossier-results__icon"><VIcon name="ri-price-tag-3-line" /></span>
        <h2 class="fr-h6 dossier-results__card-title">Classification documentaire</h2>
      </div>

      <p v-if="!classificationStep" class="fr-text--sm dossier-results__pending">
        En attente de l'exécution de l'analyse.
      </p>
      <template v-else-if="classificationResult">
        <p class="dossier-results__classification-label">{{ classificationResult.label }}</p>
        <div v-if="classificationResult.confidence !== undefined" class="dossier-results__gauge">
          <div class="dossier-results__gauge-track">
            <div class="dossier-results__gauge-fill" :style="{ width: `${classificationResult.confidence}%` }" />
          </div>
          <span class="fr-text--sm dossier-results__gauge-value">{{ classificationResult.confidence }}%</span>
        </div>
      </template>
      <p v-else class="fr-text--sm">{{ classificationStep.output }}</p>

      <RouterLink :to="`/analyses/${dossier.analyseId}`" class="fr-link fr-text--sm dossier-results__config-link">
        Voir la configuration
      </RouterLink>
    </div>

    <div class="dossier-results__card">
      <div class="dossier-results__card-header">
        <span class="dossier-results__icon"><VIcon name="ri-braces-line" /></span>
        <h2 class="fr-h6 dossier-results__card-title">Entités extraites</h2>
      </div>

      <p v-if="!extractionStep" class="fr-text--sm dossier-results__pending">
        En attente de l'exécution de l'analyse.
      </p>
      <dl v-else-if="extractionResult" class="dossier-results__entities">
        <div v-for="entity in extractionResult" :key="entity.name" class="dossier-results__entity">
          <dt class="fr-text--sm dossier-results__entity-name">{{ entity.name }}</dt>
          <dd class="dossier-results__entity-value">{{ entity.value }}</dd>
        </div>
      </dl>
      <p v-else class="fr-text--sm">{{ extractionStep.output }}</p>

      <RouterLink :to="`/analyses/${dossier.analyseId}`" class="fr-link fr-text--sm dossier-results__config-link">
        Voir la configuration
      </RouterLink>
    </div>

    <div v-for="step in agentSteps" :key="step.id" class="dossier-results__card dossier-results__card--agent">
      <div class="dossier-results__card-header">
        <span class="dossier-results__icon dossier-results__icon--agent"><VIcon name="ri-robot-line" /></span>
        <h2 class="fr-h6 dossier-results__card-title">{{ step.label }}</h2>
      </div>
      <p class="fr-text--sm dossier-results__agent-output">{{ step.output }}</p>
    </div>
  </div>
</template>

<style scoped>
.dossier-results {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.dossier-results__card {
  background: var(--background-default-grey);
  border: 1px solid var(--border-default-grey);
  border-radius: 1rem;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.dossier-results__card--agent {
  border-left: 3px solid #5b4fd1;
}

.dossier-results__card-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
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
  color: #4b3fd9;
}

.dossier-results__card-title {
  margin: 0;
}

.dossier-results__pending {
  color: var(--text-mention-grey);
  margin: 0;
}

.dossier-results__classification-label {
  font-size: 1.25rem;
  font-weight: bold;
  margin: 0;
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
  margin-top: auto;
  align-self: flex-start;
}
</style>
