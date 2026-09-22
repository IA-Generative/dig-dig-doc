<script setup lang="ts">
import {
  DOSSIER_STATUS_LABELS,
  EXECUTION_STEP_STATUS_LABELS,
  type Dossier,
  type ExecutionStepStatus,
} from "@/types/dossier";

defineProps<{ dossier?: Dossier }>();
const opened = defineModel<boolean>("opened", { default: false });

const stepBadgeType: Record<ExecutionStepStatus, "info" | "success" | "error"> = {
  en_cours: "info",
  terminé: "success",
  échec: "error",
};

function formatDateTime(iso?: string) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "medium" });
}

function formatSize(bytes: number) {
  return bytes < 1_000_000 ? `${Math.round(bytes / 1000)} Ko` : `${(bytes / 1_000_000).toFixed(1)} Mo`;
}
</script>

<template>
  <Teleport to="body">
    <Transition name="execution-panel-fade">
      <div v-if="opened" class="execution-panel__backdrop" @click="opened = false" />
    </Transition>
    <Transition name="execution-panel-slide">
      <aside v-if="opened && dossier" class="execution-panel" aria-label="Exécution du dossier">
        <div class="execution-panel__header">
          <div>
            <h2 class="fr-h5 execution-panel__title">{{ dossier.name }}</h2>
            <p class="fr-text--sm execution-panel__subtitle">
              Statut : {{ DOSSIER_STATUS_LABELS[dossier.status] }} · Version {{ dossier.analyseVersion }}
            </p>
          </div>
          <DsfrButton label="Fermer" icon-only tertiary icon="ri-close-line" @click="opened = false" />
        </div>

        <dl class="execution-panel__meta">
          <div>
            <dt class="fr-text--sm">Lancée le</dt>
            <dd class="fr-text--sm">{{ formatDateTime(dossier.startedAt) }}</dd>
          </div>
          <div>
            <dt class="fr-text--sm">Terminée le</dt>
            <dd class="fr-text--sm">{{ formatDateTime(dossier.endedAt) }}</dd>
          </div>
        </dl>

        <div class="execution-panel__section">
          <h3 class="fr-h6 execution-panel__section-title">Documents ({{ dossier.documents.length }})</h3>
          <p v-if="dossier.documents.length === 0" class="fr-text--sm">Aucun document déposé.</p>
          <ul v-else class="execution-panel__documents">
            <li v-for="document in dossier.documents" :key="document.id" class="execution-panel__document">
              <VIcon name="ri-file-line" />
              <span>{{ document.name }}</span>
              <span class="execution-panel__document-size">{{ formatSize(document.size) }}</span>
            </li>
          </ul>
        </div>

        <p v-if="dossier.executionSteps.length === 0" class="fr-text--sm">Aucune exécution pour le moment.</p>

        <ol v-else class="execution-panel__steps">
          <li v-for="step in dossier.executionSteps" :key="step.id" class="execution-panel__step">
            <div class="execution-panel__step-header">
              <span class="fr-text--md execution-panel__step-label">{{ step.label }}</span>
              <DsfrBadge
                :label="EXECUTION_STEP_STATUS_LABELS[step.status]"
                :type="stepBadgeType[step.status]"
                small
              />
            </div>
            <p class="fr-text--sm execution-panel__step-time">
              {{ formatDateTime(step.startedAt) }}<template v-if="step.endedAt"> → {{ formatDateTime(step.endedAt) }}</template>
            </p>
          </li>
        </ol>
      </aside>
    </Transition>
  </Teleport>
</template>

<style scoped>
.execution-panel__backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 1750;
}

.execution-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: min(28rem, 100vw);
  background: var(--background-default-grey);
  box-shadow: -4px 0 16px rgba(0, 0, 0, 0.15);
  z-index: 1751;
  padding: 1.5rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.execution-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.execution-panel__title {
  margin: 0;
}

.execution-panel__subtitle {
  margin: 0.25rem 0 0;
  color: var(--text-mention-grey);
}

.execution-panel__meta {
  display: flex;
  gap: 2rem;
  margin: 0;
}

.execution-panel__meta dt {
  color: var(--text-mention-grey);
}

.execution-panel__meta dd {
  margin: 0;
  font-weight: bold;
}

.execution-panel__section-title {
  margin: 0 0 0.75rem;
}

.execution-panel__documents {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.execution-panel__document {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 0.25rem;
}

.execution-panel__document-size {
  margin-left: auto;
  color: var(--text-mention-grey);
}

.execution-panel__steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.execution-panel__step {
  padding: 1rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 0.5rem;
}

.execution-panel__step-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.execution-panel__step-label {
  font-weight: bold;
}

.execution-panel__step-time {
  margin: 0.5rem 0 0;
  color: var(--text-mention-grey);
}

.execution-panel-slide-enter-active,
.execution-panel-slide-leave-active {
  transition: transform 0.2s ease;
}

.execution-panel-slide-enter-from,
.execution-panel-slide-leave-to {
  transform: translateX(100%);
}

.execution-panel-fade-enter-active,
.execution-panel-fade-leave-active {
  transition: opacity 0.2s ease;
}

.execution-panel-fade-enter-from,
.execution-panel-fade-leave-to {
  opacity: 0;
}
</style>
