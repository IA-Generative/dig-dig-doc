<script setup lang="ts">
import { useRoute } from "vue-router";

import TrackingView from "@/components/tracking/TrackingView.vue";

// Onglet « Suivi » d'une analyse : le tableau de suivi limité à cette analyse.
const route = useRoute();
</script>

<template>
  <TrackingView :key="String(route.params.id)" :analyse-id="String(route.params.id)" />
</template>
