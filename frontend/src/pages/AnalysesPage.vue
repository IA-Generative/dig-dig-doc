<script setup lang="ts">
import { computed, ref } from "vue";

import { useAnalyses } from "@/composables/useAnalyses";

const { list, create } = useAnalyses();

const searchQuery = ref("");
const currentPage = ref(1);
const pageSize = 6;

const isCreateModalOpened = ref(false);
const newAnalyseName = ref("");
const newAnalyseDescription = ref("");

const filteredAnalyses = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  if (!query) return list.value;
  return list.value.filter(
    (analyse) => analyse.name.toLowerCase().includes(query) || analyse.description.toLowerCase().includes(query),
  );
});

const pageCount = computed(() => Math.max(1, Math.ceil(filteredAnalyses.value.length / pageSize)));

const paginatedAnalyses = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  return filteredAnalyses.value.slice(start, start + pageSize);
});

const pages = computed(() =>
  Array.from({ length: pageCount.value }, (_, i) => ({
    label: String(i + 1),
    title: `Page ${i + 1}`,
  })),
);

function onSearch(query: string) {
  searchQuery.value = query;
  currentPage.value = 1;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric" });
}

function openCreateModal() {
  newAnalyseName.value = "";
  newAnalyseDescription.value = "";
  isCreateModalOpened.value = true;
}

function submitCreateAnalyse() {
  if (!newAnalyseName.value.trim()) return;
  create(newAnalyseName.value.trim(), newAnalyseDescription.value.trim());
  isCreateModalOpened.value = false;
  currentPage.value = 1;
}
</script>

<template>
  <div>
    <div class="analyses-page__header">
      <div>
        <h1 class="fr-h2">Analyses</h1>
        <p class="fr-text--lead">Retrouvez vos analyses ou créez-en une nouvelle.</p>
      </div>
      <DsfrButton label="Créer une analyse" icon="ri-add-line" @click="openCreateModal" />
    </div>

    <DsfrSearchBar
      label="Rechercher une analyse"
      placeholder="Nom ou description..."
      :model-value="searchQuery"
      class="analyses-page__search"
      @update:model-value="onSearch"
      @search="onSearch"
    />

    <p v-if="filteredAnalyses.length === 0" class="fr-text--sm">Aucune analyse ne correspond à cette recherche.</p>

    <div v-else class="analyses-page__grid">
      <DsfrCard
        v-for="analyse in paginatedAnalyses"
        :key="analyse.id"
        :title="analyse.name"
        :description="analyse.description"
        :link="{ name: 'analyse-detail', params: { id: analyse.id } }"
        :detail="formatDate(analyse.createdAt)"
        detail-icon="ri-calendar-line"
        :end-detail="`${analyse.agents.length} agent${analyse.agents.length > 1 ? 's' : ''}`"
        end-detail-icon="ri-robot-line"
      />
    </div>

    <DsfrPagination
      v-if="pageCount > 1"
      :pages="pages"
      v-model:current-page="currentPage"
      class="analyses-page__pagination"
    />

    <DsfrModal
      v-model:opened="isCreateModalOpened"
      title="Créer une analyse"
      :actions="[
        { label: 'Annuler', secondary: true, onClick: () => (isCreateModalOpened = false) },
        { label: 'Créer', onClick: submitCreateAnalyse },
      ]"
    >
      <DsfrInput v-model="newAnalyseName" label="Nom de l'analyse" label-visible required />
      <DsfrInput
        v-model="newAnalyseDescription"
        label="Description"
        label-visible
        is-textarea
        class="fr-mt-2w"
      />
    </DsfrModal>
  </div>
</template>

<style scoped>
.analyses-page__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.analyses-page__search {
  max-width: 32rem;
  margin: 1.5rem 0 2rem;
}

.analyses-page__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
  gap: 1.5rem;
}

.analyses-page__pagination {
  margin-top: 2rem;
  display: flex;
  justify-content: center;
}
</style>
