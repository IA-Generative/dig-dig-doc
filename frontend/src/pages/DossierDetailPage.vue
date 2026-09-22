<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { useAnalyses } from "@/composables/useAnalyses";
import { useDossiers } from "@/composables/useDossiers";
import { DOSSIER_STATUS_LABELS, type DossierStatus, type ExecutionStep, type ExecutionStepStatus } from "@/types/dossier";

const route = useRoute();
const { list: dossiers } = useDossiers();
const { getById: getAnalyseById } = useAnalyses();

const dossier = computed(() => dossiers.value.find((d) => d.id === String(route.params.id)));
const analyse = computed(() => (dossier.value ? getAnalyseById(dossier.value.analyseId) : undefined));

const statusBadgeType: Record<DossierStatus, "new" | "info" | "success" | "warning" | "error"> = {
  en_attente: "new",
  en_cours: "info",
  terminé: "success",
  arrêté: "warning",
  échec: "error",
};

const stepBadgeType: Record<ExecutionStepStatus, "info" | "success" | "error"> = {
  en_cours: "info",
  terminé: "success",
  échec: "error",
};

const classificationStep = computed(() => dossier.value?.executionSteps.find((s) => s.kind === "classification"));
const extractionStep = computed(() => dossier.value?.executionSteps.find((s) => s.kind === "extraction"));
const agentSteps = computed(
  () => dossier.value?.executionSteps.filter((s): s is ExecutionStep => s.kind === "agent" && !!s.output) ?? [],
);

function formatDateTime(iso?: string) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "medium" });
}
</script>

<template>
  <div v-if="dossier" class="dossier-detail">
    <RouterLink to="/dossiers" class="fr-link fr-icon-arrow-left-line fr-link--icon-left dossier-detail__back">
      Retour aux dossiers
    </RouterLink>

    <div class="dossier-detail__header">
      <div>
        <h1 class="fr-h2">{{ dossier.name }}</h1>
        <p class="fr-text--sm">
          Analyse : <RouterLink :to="`/analyses/${dossier.analyseId}`">{{ analyse?.name ?? "introuvable" }}</RouterLink>
          · Version {{ dossier.analyseVersion }}
        </p>
      </div>
      <DsfrBadge :label="DOSSIER_STATUS_LABELS[dossier.status]" :type="statusBadgeType[dossier.status]" />
    </div>

    <div class="dossier-detail__layout">
      <main class="dossier-detail__results">
        <h2 class="fr-h5">Résultat de l'analyse</h2>

        <div v-if="!classificationStep && !extractionStep && agentSteps.length === 0" class="dossier-detail__empty">
          <p class="fr-text--sm">Ce dossier n'a pas encore été exécuté. Lancez l'analyse pour voir un résultat.</p>
        </div>

        <template v-else>
          <section v-if="classificationStep" class="dossier-detail__card">
            <h3 class="fr-h6">Classification documentaire</h3>
            <p class="fr-text--sm">{{ classificationStep.output ?? "En cours..." }}</p>
          </section>

          <section v-if="extractionStep" class="dossier-detail__card">
            <h3 class="fr-h6">Entités extraites</h3>
            <p class="fr-text--sm">{{ extractionStep.output ?? "En cours..." }}</p>
          </section>

          <section v-for="step in agentSteps" :key="step.id" class="dossier-detail__card">
            <h3 class="fr-h6">{{ step.label }}</h3>
            <p class="fr-text--sm">{{ step.output }}</p>
          </section>
        </template>
      </main>

      <aside class="dossier-detail__discussion" aria-label="Suivi de l'exécution">
        <h2 class="fr-h6 dossier-detail__discussion-title">Exécution</h2>

        <p v-if="dossier.executionSteps.length === 0" class="fr-text--sm">Aucune exécution pour le moment.</p>

        <ul v-else class="dossier-detail__messages">
          <li v-for="step in dossier.executionSteps" :key="step.id" class="dossier-detail__message">
            <div class="dossier-detail__message-header">
              <span class="fr-text--sm dossier-detail__message-label">{{ step.label }}</span>
              <DsfrBadge :label="step.status" :type="stepBadgeType[step.status]" small />
            </div>
            <p class="fr-text--sm dossier-detail__message-time">{{ formatDateTime(step.startedAt) }}</p>
            <p v-if="step.output" class="fr-text--sm dossier-detail__message-content">{{ step.output }}</p>
          </li>
        </ul>
      </aside>
    </div>
  </div>
  <div v-else>
    <p>Dossier introuvable.</p>
    <RouterLink to="/dossiers" class="fr-link">Retour aux dossiers</RouterLink>
  </div>
</template>

<style scoped>
.dossier-detail__back {
  display: inline-flex;
  margin-bottom: 1.5rem;
}

.dossier-detail__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.dossier-detail__layout {
  display: flex;
  gap: 1.5rem;
  align-items: flex-start;
}

.dossier-detail__results {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.dossier-detail__empty,
.dossier-detail__card {
  background: var(--background-default-grey);
  border: 1px solid var(--border-default-grey);
  border-radius: 0.75rem;
  padding: 1.25rem;
}

.dossier-detail__card h3 {
  margin: 0 0 0.5rem;
}

.dossier-detail__discussion {
  width: 22rem;
  flex-shrink: 0;
  background: var(--background-alt-blue-france);
  border: 1px solid var(--border-default-grey);
  border-radius: 0.75rem;
  padding: 1.25rem;
  position: sticky;
  top: 1.5rem;
  max-height: calc(100vh - 3rem);
  overflow-y: auto;
}

.dossier-detail__discussion-title {
  margin: 0 0 1rem;
}

.dossier-detail__messages {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.dossier-detail__message {
  background: var(--background-default-grey);
  border-radius: 0.5rem;
  padding: 0.75rem;
}

.dossier-detail__message-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.dossier-detail__message-label {
  font-weight: bold;
}

.dossier-detail__message-time {
  margin: 0.25rem 0 0;
  color: var(--text-mention-grey);
}

.dossier-detail__message-content {
  margin: 0.5rem 0 0;
}

@media (max-width: 62rem) {
  .dossier-detail__layout {
    flex-direction: column;
  }

  .dossier-detail__discussion {
    width: 100%;
    position: static;
    max-height: none;
  }
}
</style>
