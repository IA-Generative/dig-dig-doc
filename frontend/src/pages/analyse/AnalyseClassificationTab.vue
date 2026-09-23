<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute } from "vue-router";

import LabelsEditor from "@/components/analyses/LabelsEditor.vue";
import PromptEditor from "@/components/analyses/PromptEditor.vue";
import { useAnalyses } from "@/composables/useAnalyses";
import { suggestClassificationPrompt } from "@/composables/useLlmAssist";

const route = useRoute();
const {
  getById,
  fetchAnalyse,
  updateClassificationPrompt,
  restoreClassificationPromptVersion,
  updateClassificationLabels,
  restoreClassificationLabelsVersion,
} = useAnalyses();

const analyse = computed(() => getById(String(route.params.id)));

// L'analyse peut ne pas être en cache si l'utilisateur accède directement
// à cet onglet par URL. On la charge au montage si nécessaire.
onMounted(() => {
  if (!analyse.value) fetchAnalyse(String(route.params.id));
});
</script>

<template>
  <div v-if="analyse">
    <PromptEditor
      :prompt="analyse.classification.prompt"
      :versions="analyse.classification.promptVersions"
      :suggest-prompt="suggestClassificationPrompt"
      @save="(prompt) => updateClassificationPrompt(analyse!.id, prompt)"
      @restore="(versionId) => restoreClassificationPromptVersion(analyse!.id, versionId)"
    />
    <hr class="analyse-tab__divider" />
    <LabelsEditor
      :labels="analyse.classification.labels"
      :versions="analyse.classification.labelsVersions"
      @save="(labels) => updateClassificationLabels(analyse!.id, labels)"
      @restore="(versionId) => restoreClassificationLabelsVersion(analyse!.id, versionId)"
    />
  </div>
  <div v-else>
    <p>Chargement…</p>
  </div>
</template>

<style scoped>
.analyse-tab__divider {
  border: none;
  border-top: 1px solid var(--border-default-grey);
  margin: 1.5rem 0;
}
</style>
