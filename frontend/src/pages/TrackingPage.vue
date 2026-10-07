<script setup lang="ts">
import TrackingView from "@/components/tracking/TrackingView.vue";

// Vue transversale du tableau de suivi (#186) : les dossiers de toutes les
// analyses accessibles. « Mes dossiers » est la vue ouverte par défaut ; les
// liens du tableau de bord arrivent ici avec leurs filtres dans l'URL.
</script>

<template>
  <div class="tracking-page">
    <header class="tracking-page__header">
      <h1 class="fr-h2">Suivi</h1>
      <p class="tracking-page__lead">Vos dossiers et ceux de toutes les analyses auxquelles vous avez accès.</p>
    </header>
    <TrackingView />
  </div>
</template>

<style scoped>
.tracking-page__header {
  margin-bottom: 1rem;
}

.tracking-page__header h1 {
  margin-bottom: 0.25rem;
}

.tracking-page__lead {
  margin: 0;
  color: var(--text-mention-grey);
}
</style>
