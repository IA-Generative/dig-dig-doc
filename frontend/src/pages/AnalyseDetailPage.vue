<script setup lang="ts">
import { computed, onMounted } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";

import MarkdownText from "@/components/MarkdownText.vue";
import { useAnalyses } from "@/composables/useAnalyses";

const route = useRoute();
const router = useRouter();
const { getById, fetchAnalyse } = useAnalyses();

const analyse = computed(() => getById(String(route.params.id)));

onMounted(() => {
  if (!analyse.value) fetchAnalyse(String(route.params.id));
});

// Les onglets sont pilotés par la route : chaque onglet correspond à une
// route enfant (classification, extraction, agents). L'index actif est
// déduit du nom de la route courante. Les champs tabId/panelId sont
// requis par DsfrTabs pour les attributs ARIA.
const tabs = [
  { title: "Classification documentaire", icon: "ri-price-tag-3-line", tabId: "tab-classification", panelId: "panel-classification", routeName: "analyse-classification" },
  { title: "Extraction d'entités nommées", icon: "ri-braces-line", tabId: "tab-extraction", panelId: "panel-extraction", routeName: "analyse-extraction" },
  { title: "Agents", icon: "ri-robot-line", tabId: "tab-agents", panelId: "panel-agents", routeName: "analyse-agents" },
] as const;

const activeTabIndex = computed(() => {
  const index = tabs.findIndex((tab) => tab.routeName === route.name);
  return index === -1 ? 0 : index;
});

const activeTab = computed(() => tabs[activeTabIndex.value]);

function selectTab(index: number) {
  const tab = tabs[index];
  if (tab) {
    router.push({ name: tab.routeName, params: route.params });
  }
}
</script>

<template>
  <div v-if="analyse">
    <RouterLink to="/analyses" class="fr-link fr-icon-arrow-left-line fr-link--icon-left analyse-detail__back">
      Retour aux analyses
    </RouterLink>

    <div class="analyse-detail__header">
      <div>
        <h1 class="fr-h2">{{ analyse.name }}</h1>
        <MarkdownText :content="analyse.description" class="fr-text--lead" />
      </div>
    </div>

    <DsfrTabs
      :model-value="activeTabIndex"
      tab-list-name="Sections de l'analyse"
      :tab-titles="tabs"
      @update:model-value="selectTab"
    >
      <DsfrTabContent :panel-id="activeTab.panelId" :tab-id="activeTab.tabId">
        <RouterView />
      </DsfrTabContent>
    </DsfrTabs>
  </div>
  <div v-else>
    <p>Chargement…</p>
    <RouterLink to="/analyses" class="fr-link">Retour aux analyses</RouterLink>
  </div>
</template>

<style scoped>
.analyse-detail__back {
  display: inline-flex;
  margin-bottom: 1.5rem;
}

.analyse-detail__header {
  margin-bottom: 2rem;
}
</style>
