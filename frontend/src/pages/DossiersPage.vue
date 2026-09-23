<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import CreateDossierModal from "@/components/dossiers/CreateDossierModal.vue";
import { useAnalyses } from "@/composables/useAnalyses";
import { useDossiers } from "@/composables/useDossiers";
import { DOSSIER_STATUS_LABELS, type Dossier, type DossierStatus } from "@/types/dossier";

const { list: dossiers, pageCount, fetchList, launch, stop } = useDossiers();
const { list: analyses, fetchList: fetchAnalyses } = useAnalyses();

const isCreateModalOpened = ref(false);

const PAGE_SIZE = 10;
const currentPage = ref(1);

const pages = computed(() =>
  Array.from({ length: pageCount.value }, (_, i) => ({ label: String(i + 1), title: `Page ${i + 1}` })),
);

watch(currentPage, (page) => fetchList(page, PAGE_SIZE), { immediate: true });
// La table affiche le nom de l'analyse liée à chaque dossier : la liste
// paginée par défaut (6-20 éléments) ne couvre pas forcément toutes les
// analyses existantes, donc on en charge une fenêtre large dédiée à cette
// page plutôt que de dépendre de ce qu'une autre page a chargé en dernier.
onMounted(() => fetchAnalyses(1, 100));

const statusBadgeType: Record<DossierStatus, "new" | "info" | "success" | "warning" | "error"> = {
  en_attente: "new",
  en_cours: "info",
  terminé: "success",
  arrêté: "warning",
  échec: "error",
};

function analyseName(dossier: Dossier) {
  return analyses.value.find((a) => a.id === dossier.analyseId)?.name ?? "Analyse introuvable";
}

function formatDateTime(iso?: string) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
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
            <td><RouterLink :to="`/dossiers/${dossier.id}`">{{ dossier.name }}</RouterLink></td>
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
              <RouterLink :to="`/dossiers/${dossier.id}`" class="fr-btn fr-btn--tertiary fr-btn--sm fr-icon-file-text-line" title="Voir le résultat" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <DsfrPagination
      v-if="pageCount > 1"
      :pages="pages"
      v-model:current-page="currentPage"
      class="dossiers-page__pagination"
    />

    <CreateDossierModal v-model:opened="isCreateModalOpened" />
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

.dossiers-page__pagination {
  margin-top: 1.5rem;
  display: flex;
  justify-content: center;
}
</style>
