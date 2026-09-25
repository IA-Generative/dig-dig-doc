<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRouter } from "vue-router";

import CreateDossierModal from "@/components/dossiers/CreateDossierModal.vue";
import { useAnalyses } from "@/composables/useAnalyses";
import { useDossiers } from "@/composables/useDossiers";
import {
  DOSSIER_STATUS_LABELS,
  SUGGESTION_STATUS_LABELS,
  type Dossier,
  type DossierStatus,
  type SuggestionStatus,
} from "@/types/dossier";

const router = useRouter();
const { list: dossiers, pageCount, fetchList, launch, stop, suggestAnalyse } = useDossiers();
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
  if (!dossier.analyseId) return "À ranger";
  return analyses.value.find((a) => a.id === dossier.analyseId)?.name ?? "Analyse introuvable";
}

function formatDate(iso?: string) {
  if (!iso) return "-";
  return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function formatTime(iso?: string) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

/** Date la plus pertinente selon le statut : terminé → endedAt, en cours → startedAt, sinon createdAt. */
function relevantDate(dossier: Dossier) {
  if (dossier.endedAt) return dossier.endedAt;
  if (dossier.startedAt) return dossier.startedAt;
  return dossier.createdAt;
}

const suggestionBadgeType: Record<SuggestionStatus, "new" | "info" | "success" | "warning" | "error"> = {
  en_attente: "new",
  en_cours: "info",
  terminé: "success",
  échec: "error",
};

function goToDossier(dossier: Dossier) {
  router.push(`/dossiers/${dossier.id}`);
}

function isUnassigned(dossier: Dossier) {
  return !dossier.analyseId;
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

    <div v-else class="fr-table">
      <div class="fr-table__wrapper">
        <div class="fr-table__container">
          <div class="fr-table__content">
            <table class="dossiers-page__table">
              <thead>
                <tr>
                  <th scope="col">Dossier</th>
                  <th scope="col">Analyse</th>
                  <th scope="col">Statut</th>
                  <th scope="col">Date</th>
                  <th scope="col" class="dossiers-page__actions-col">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="dossier in dossiers"
                  :key="dossier.id"
                  class="dossiers-page__row"
                  @click="goToDossier(dossier)"
                >
                  <td>
                    <RouterLink :to="`/dossiers/${dossier.id}`" class="dossiers-page__name-link" @click.stop>
                      {{ dossier.name }}
                    </RouterLink>
                  </td>
                  <td>
                    <div class="dossiers-page__analyse-cell">
                      <span class="dossiers-page__analyse-name">{{ analyseName(dossier) }}</span>
                      <span v-if="!isUnassigned(dossier)" class="fr-text--xs dossiers-page__version">v{{ dossier.analyseVersion }}</span>
                      <DsfrBadge
                        v-if="isUnassigned(dossier)"
                        :label="SUGGESTION_STATUS_LABELS[dossier.suggestionStatus]"
                        :type="suggestionBadgeType[dossier.suggestionStatus]"
                        small
                        class="dossiers-page__suggestion-badge"
                      />
                    </div>
                  </td>
                  <td><DsfrBadge :label="DOSSIER_STATUS_LABELS[dossier.status]" :type="statusBadgeType[dossier.status]" small /></td>
                  <td>
                    <div class="dossiers-page__date-cell">
                      <span>{{ formatDate(relevantDate(dossier)) }}</span>
                      <span class="fr-text--xs dossiers-page__time">{{ formatTime(relevantDate(dossier)) }}</span>
                    </div>
                  </td>
                  <td @click.stop>
                    <div class="dossiers-page__actions">
                      <DsfrButton
                        v-if="isUnassigned(dossier)"
                        label="Suggérer"
                        secondary
                        icon="ri-lightbulb-flash-line"
                        size="sm"
                        :disabled="dossier.suggestionStatus === 'en_cours'"
                        @click="suggestAnalyse(dossier.id)"
                      />
                      <DsfrButton
                        v-else-if="dossier.status === 'en_cours'"
                        label="Arrêter"
                        secondary
                        icon="ri-stop-circle-line"
                        size="sm"
                        @click="stop(dossier.id)"
                      />
                      <DsfrButton
                        v-else-if="(dossier.status === 'en_attente' || dossier.status === 'arrêté') && !isUnassigned(dossier)"
                        label="Lancer"
                        icon="ri-play-circle-line"
                        size="sm"
                        @click="launch(dossier.id)"
                      />
                      <RouterLink
                        v-if="dossier.status === 'terminé' || dossier.status === 'échec'"
                        :to="`/dossiers/${dossier.id}`"
                        class="fr-btn fr-btn--tertiary fr-btn--sm fr-icon-eye-line"
                        title="Voir le résultat"
                      />
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
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

.dossiers-page__table {
  width: 100%;
}

.dossiers-page__row {
  cursor: pointer;
  transition: background-color 0.1s ease;
}

.dossiers-page__row:hover {
  background-color: var(--background-alt-grey);
}

.dossiers-page__name-link {
  font-weight: 500;
}

.dossiers-page__table :deep(td),
.dossiers-page__table :deep(th) {
  vertical-align: middle;
}

.dossiers-page__analyse-cell {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.dossiers-page__analyse-name {
  font-weight: 500;
}

.dossiers-page__version {
  color: var(--text-mention-grey);
}

.dossiers-page__suggestion-badge {
  margin-top: 0.25rem;
}

.dossiers-page__date-cell {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.dossiers-page__time {
  color: var(--text-mention-grey);
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
