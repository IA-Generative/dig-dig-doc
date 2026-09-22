<script setup lang="ts">
withDefaults(defineProps<{ label?: string; compact?: boolean }>(), { label: "Aide LLM", compact: false });
</script>

<template>
  <button
    type="button"
    class="llm-assist-button"
    :class="{ 'llm-assist-button--compact': compact }"
    :title="compact ? label : undefined"
  >
    <VIcon name="ri-sparkling-2-fill" class="llm-assist-button__icon" />
    <span v-if="!compact">{{ label }}</span>
    <span v-else class="fr-sr-only">{{ label }}</span>
  </button>
</template>

<style scoped>
.llm-assist-button {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 1.5rem;
  background: linear-gradient(135deg, #5b4fd1 0%, #8b4fd6 50%, #d1477a 100%);
  color: #fff;
  font-weight: bold;
  font-size: 0.875rem;
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(91, 79, 209, 0.35);
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease,
    filter 0.15s ease;
}

.llm-assist-button--compact {
  padding: 0.4rem;
  border-radius: 50%;
}

.llm-assist-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(91, 79, 209, 0.45);
  filter: brightness(1.05);
}

.llm-assist-button:active {
  transform: translateY(0);
  box-shadow: 0 1px 4px rgba(91, 79, 209, 0.35);
}

.llm-assist-button:focus-visible {
  outline: 2px solid #5b4fd1;
  outline-offset: 2px;
}

.llm-assist-button__icon {
  font-size: 1rem;
}
</style>
