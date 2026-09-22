<script setup lang="ts">
defineProps<{ title: string; icon: string }>();
</script>

<template>
  <div class="analyse-section-card">
    <div class="analyse-section-card__header">
      <span class="analyse-section-card__icon"><VIcon :name="icon" /></span>
      <h2 class="fr-h5 analyse-section-card__title">{{ title }}</h2>
    </div>
    <slot />
  </div>
</template>

<style scoped>
.analyse-section-card {
  background: var(--background-default-grey);
  border: 1px solid var(--border-default-grey);
  border-radius: 1rem;
  padding: 1.75rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.analyse-section-card__header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.analyse-section-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.75rem;
  background: linear-gradient(135deg, #6a5cff1a 0%, #ff6ca01a 100%);
  color: #4b3fd9;
  flex-shrink: 0;
}

.analyse-section-card__title {
  margin: 0;
}
</style>
