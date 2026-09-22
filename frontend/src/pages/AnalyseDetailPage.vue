<script setup lang="ts">
import { computed, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";

import AddAgentModal from "@/components/analyses/AddAgentModal.vue";
import AgentCard from "@/components/analyses/AgentCard.vue";
import AnalyseSectionCard from "@/components/analyses/AnalyseSectionCard.vue";
import EntitiesEditor from "@/components/analyses/EntitiesEditor.vue";
import LabelsEditor from "@/components/analyses/LabelsEditor.vue";
import PromptEditor from "@/components/analyses/PromptEditor.vue";
import { useAnalyses } from "@/composables/useAnalyses";
import { suggestClassificationPrompt, suggestExtractionPrompt } from "@/composables/useLlmAssist";

const route = useRoute();
const {
  getById,
  updateClassificationPrompt,
  restoreClassificationPromptVersion,
  updateClassificationLabels,
  restoreClassificationLabelsVersion,
  updateExtractionPrompt,
  restoreExtractionPromptVersion,
  updateExtractionEntities,
  restoreExtractionEntitiesVersion,
} = useAnalyses();

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
    </div>

    <div class="analyse-detail__sections">
      <AnalyseSectionCard title="Classification documentaire" icon="ri-price-tag-3-line">
        <PromptEditor
          :prompt="analyse.classification.prompt"
          :versions="analyse.classification.promptVersions"
          :suggest-prompt="suggestClassificationPrompt"
          @save="(prompt) => updateClassificationPrompt(analyse!.id, prompt)"
          @restore="(versionId) => restoreClassificationPromptVersion(analyse!.id, versionId)"
        />
        <hr class="analyse-detail__divider" />
        <LabelsEditor
          :labels="analyse.classification.labels"
          :versions="analyse.classification.labelsVersions"
          @save="(labels) => updateClassificationLabels(analyse!.id, labels)"
          @restore="(versionId) => restoreClassificationLabelsVersion(analyse!.id, versionId)"
        />
      </AnalyseSectionCard>

      <AnalyseSectionCard title="Extraction d'entités nommées" icon="ri-braces-line">
        <PromptEditor
          :prompt="analyse.extraction.prompt"
          :versions="analyse.extraction.promptVersions"
          :suggest-prompt="suggestExtractionPrompt"
          @save="(prompt) => updateExtractionPrompt(analyse!.id, prompt)"
          @restore="(versionId) => restoreExtractionPromptVersion(analyse!.id, versionId)"
        />
        <hr class="analyse-detail__divider" />
        <EntitiesEditor
          :entities="analyse.extraction.entities"
          :versions="analyse.extraction.entitiesVersions"
          @save="(entities) => updateExtractionEntities(analyse!.id, entities)"
          @restore="(versionId) => restoreExtractionEntitiesVersion(analyse!.id, versionId)"
        />
      </AnalyseSectionCard>

      <section class="analyse-detail__agents-section">
        <div class="analyse-detail__agents-header">
          <div>
            <h2 class="fr-h5">Agents</h2>
            <p class="fr-text--sm">
              Agents créés pour un but métier propre à cette analyse (cohérence, rédaction, timeline...).
            </p>
          </div>
          <DsfrButton label="Créer un agent" icon="ri-robot-line" @click="isAddAgentModalOpened = true" />
        </div>

        <p v-if="analyse.agents.length === 0" class="fr-text--sm">Aucun agent créé pour cette analyse.</p>

        <div v-else class="analyse-detail__agents">
          <AgentCard v-for="agent in analyse.agents" :key="agent.id" :analyse-id="analyse.id" :agent="agent" />
        </div>
      </section>
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
  margin-bottom: 2rem;
}

.analyse-detail__sections {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.analyse-detail__divider {
  border: none;
  border-top: 1px solid var(--border-default-grey);
  margin: 0;
}

.analyse-detail__agents-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.analyse-detail__agents-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.analyse-detail__agents {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}
</style>
