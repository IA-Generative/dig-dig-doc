<script setup lang="ts">
import { computed, ref } from "vue";

import CreateDossierModal from "@/components/dossiers/CreateDossierModal.vue";
import ExecutionPanel from "@/components/dossiers/ExecutionPanel.vue";
import { useAnalyses } from "@/composables/useAnalyses";
import { useDossiers } from "@/composables/useDossiers";
import { DOSSIER_STATUS_LABELS, type Dossier, type DossierStatus } from "@/types/dossier";

const { list: dossiers, launch, stop } = useDossiers();
const { getById: getAnalyseById } = useAnalyses();

const isCreateModalOpened = ref(false);
const isExecutionPanelOpened = ref(false);
const selectedDossierId = ref<string | undefined>(undefined);

const selectedDossier = computed(() => dossiers.value.find((d) => d.id === selectedDossierId.value));

const statusBadgeType: Record<DossierStatus, "new" | "info" | "success" | "warning" | "error"> = {
  en_attente: "new",
  en_cours: "info",
  terminé: "success",
  arrêté: "warning",
  échec: "error",
};

function analyseName(dossier: Dossier) {
  return getAnalyseById(dossier.analyseId)?.name ?? "Analyse introuvable";
}

function formatDateTime(iso?: string) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

function openExecution(dossier: Dossier) {
  selectedDossierId.value = dossier.id;
  isExecutionPanelOpened.value = true;
}
</script>

<template>
  <div>
    <div class="dossiers-page__header">
      <div>
        <h1 class="fr-h2">Dossiers</h1>
        <p class="fr-text--lead">Dossiers usagers liés à une analyse, et suivi de leur exécution.</p>
      </div>
      <DsfrButton label="Créer un dossier" icon="ri-add-line" @click="isCreateModalOpened = true" />
    </div>

    <p v-if="dossiers.length === 0" class="fr-text--sm">Aucun dossier pour le moment.</p>

    <div v-else class="dossiers-page__table-wrapper">
      <table class="fr-table dossiers-page__table">
        <thead>
          <tr>
            <th>Dossier</th>
            <th>Analyse</th>
            <th>Version</th>
            <th>Créé le</th>
            <th>Lancé le</th>
            <th>Terminé le</th>
            <th>Statut</th>
            <th class="dossiers-page__actions-col">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="dossier in dossiers" :key="dossier.id">
            <td>{{ dossier.name }}</td>
            <td>{{ analyseName(dossier) }}</td>
            <td>{{ dossier.analyseVersion }}</td>
            <td>{{ formatDateTime(dossier.createdAt) }}</td>
            <td>{{ formatDateTime(dossier.startedAt) }}</td>
            <td>{{ formatDateTime(dossier.endedAt) }}</td>
            <td><DsfrBadge :label="DOSSIER_STATUS_LABELS[dossier.status]" :type="statusBadgeType[dossier.status]" small /></td>
            <td class="dossiers-page__actions">
              <DsfrButton
                v-if="dossier.status === 'en_cours'"
                label="Arrêter"
                secondary
                icon="ri-stop-circle-line"
                size="sm"
                @click="stop(dossier.id)"
              />
              <DsfrButton
                v-else
                label="Lancer"
                icon="ri-play-circle-line"
                size="sm"
                @click="launch(dossier.id)"
              />
              <DsfrButton
                label="Voir l'exécution"
                icon-only
                tertiary
                icon="ri-list-check-2"
                size="sm"
                @click="openExecution(dossier)"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <CreateDossierModal v-model:opened="isCreateModalOpened" />
    <ExecutionPanel v-model:opened="isExecutionPanelOpened" :dossier="selectedDossier" />
  </div>
</template>

<style scoped>
.dossiers-page__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.dossiers-page__table-wrapper {
  overflow-x: auto;
}

.dossiers-page__table {
  width: 100%;
}

.dossiers-page__actions-col {
  white-space: nowrap;
}

.dossiers-page__actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  white-space: nowrap;
}
</style>
