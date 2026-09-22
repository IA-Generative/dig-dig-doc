<script setup lang="ts">
import { computed, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";

import AgentCard from "@/components/AgentCard.vue";
import { suggestPrompt, useAnalyses } from "@/composables/useAnalyses";
import type { AgentCapability } from "@/types/analyse";

const route = useRoute();
const { getById, addAgent } = useAnalyses();

const analyse = computed(() => getById(String(route.params.id)));

const capabilities: AgentCapability[] = [
  "Classification documentaire",
  "Extraction d'entités nommées",
  "Contrôle de cohérence",
  "Agent généraliste",
];

const isAddAgentModalOpened = ref(false);
const newAgentName = ref("");
const newAgentCapability = ref<AgentCapability>(capabilities[0]);
const newAgentPrompt = ref("");

function openAddAgentModal() {
  newAgentName.value = "";
  newAgentCapability.value = capabilities[0];
  newAgentPrompt.value = "";
  isAddAgentModalOpened.value = true;
}

function applySuggestionToNewAgent() {
  newAgentPrompt.value = suggestPrompt(newAgentCapability.value);
}

function submitAddAgent() {
  if (!analyse.value || !newAgentName.value.trim() || !newAgentPrompt.value.trim()) return;
  addAgent(analyse.value.id, newAgentName.value.trim(), newAgentCapability.value, newAgentPrompt.value.trim());
  isAddAgentModalOpened.value = false;
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
        <p class="fr-text--lead">{{ analyse.description }}</p>
      </div>
      <DsfrButton label="Ajouter un agent" icon="ri-robot-line" @click="openAddAgentModal" />
    </div>

    <p v-if="analyse.agents.length === 0" class="fr-text--sm">
      Aucun agent configuré pour cette analyse. Ajoutez-en un pour définir son prompt et sa capacité.
    </p>

    <div v-else class="analyse-detail__agents">
      <AgentCard v-for="agent in analyse.agents" :key="agent.id" :analyse-id="analyse.id" :agent="agent" />
    </div>

    <DsfrModal
      v-model:opened="isAddAgentModalOpened"
      title="Ajouter un agent"
      size="lg"
      :actions="[
        { label: 'Annuler', secondary: true, onClick: () => (isAddAgentModalOpened = false) },
        { label: 'Ajouter', onClick: submitAddAgent },
      ]"
    >
      <DsfrInput v-model="newAgentName" label="Nom de l'agent" label-visible required />
      <DsfrSelect
        v-model="newAgentCapability"
        label="Capacité"
        class="fr-mt-2w"
        :options="capabilities"
      />
      <DsfrInput
        v-model="newAgentPrompt"
        label="Prompt"
        label-visible
        is-textarea
        required
        class="fr-mt-2w"
      />
      <DsfrButton
        label="Aide à la rédaction du prompt"
        secondary
        icon="ri-magic-line"
        size="sm"
        class="fr-mt-2w"
        @click="applySuggestionToNewAgent"
      />
    </DsfrModal>
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
