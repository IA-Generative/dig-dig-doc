<script setup lang="ts">
import { ref } from "vue";

import GenerationPromptPanel from "@/components/admin/GenerationPromptPanel.vue";

// Génération des documents (backend issue #141) : ce qui est **commun à toutes les analyses**, le prompt de l'agent
// qui propose les valeurs des champs. Les modèles de document, eux, se gèrent dans chaque analyse (onglet Documents).
const promptPanel = ref<InstanceType<typeof GenerationPromptPanel>>();

defineExpose({ reload: () => promptPanel.value?.reload() });
</script>

<template>
  <section class="generation-admin">
    <h2 class="fr-h4">Génération des documents</h2>
    <p class="fr-text--sm">
      Les <strong>modèles de document</strong> appartiennent chacun à une analyse : ils se gèrent dans l'onglet
      « Documents » de l'analyse. Ce qui suit est commun à toutes les analyses.
    </p>
    <GenerationPromptPanel ref="promptPanel" />
  </section>
</template>

<style scoped>
.generation-admin {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.generation-admin h2 {
  margin: 0;
}
</style>
