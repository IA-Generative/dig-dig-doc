<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

import { useAnalyses } from "@/composables/useAnalyses";
import { useTracking } from "@/composables/useTracking";
import TrackingView from "@/components/tracking/TrackingView.vue";

// Onglet « Suivi » d'une analyse : le tableau de suivi limité à cette analyse.
// MOCK : l'analyse réelle est rapprochée d'une analyse simulée par son nom ;
// à défaut, la première analyse simulée sert d'exemple.
const route = useRoute();
const { getById } = useAnalyses();
const { analyses } = useTracking();

const mockAnalyseId = computed(() => {
  const name = getById(String(route.params.id))?.name;
  return (analyses.find((a) => a.name === name) ?? analyses[0]).id;
});
</script>

<template>
  <TrackingView :key="mockAnalyseId" :analyse-id="mockAnalyseId" />
</template>
