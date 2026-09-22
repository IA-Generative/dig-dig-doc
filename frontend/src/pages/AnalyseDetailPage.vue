<script setup lang="ts">
import { computed, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";

import AddAgentModal from "@/components/analyses/AddAgentModal.vue";
import AgentCard from "@/components/analyses/AgentCard.vue";
import { useAnalyses } from "@/composables/useAnalyses";

const route = useRoute();
const { getById } = useAnalyses();

const analyse = computed(() => getById(String(route.params.id)));
const isAddAgentModalOpened = ref(false);
</script>

<template>
  <div v-if="analyse">
    <RouterLink to="/analyses" class="fr-link fr-icon-arrow-left-line fr-link--icon-left analyse-detail__back">
      Retour aux analyses
    </RouterLink>

    <div class="analyse-detail__header">
      <div>
        <h1 class="fr-h2">{{ analyse.name }}</h1>
        <p class="fr-text--lead">{{ analyse.description }}</p>
      </div>
      <DsfrButton label="Ajouter un agent" icon="ri-robot-line" @click="isAddAgentModalOpened = true" />
    </div>

    <p v-if="analyse.agents.length === 0" class="fr-text--sm">
      Aucun agent configuré pour cette analyse. Ajoutez-en un pour définir son prompt et sa capacité.
    </p>

    <div v-else class="analyse-detail__agents">
      <AgentCard v-for="agent in analyse.agents" :key="agent.id" :analyse-id="analyse.id" :agent="agent" />
    </div>

    <AddAgentModal :analyse-id="analyse.id" v-model:opened="isAddAgentModalOpened" />
  </div>
  <div v-else>
    <p>Analyse introuvable.</p>
    <RouterLink to="/analyses" class="fr-link">Retour aux analyses</RouterLink>
  </div>
</template>

<style scoped>
.analyse-detail__back {
  display: inline-flex;
  margin-bottom: 1.5rem;
}

.analyse-detail__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 2rem;
}

.analyse-detail__agents {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}
</style>
