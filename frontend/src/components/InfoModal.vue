<script setup lang="ts">
/**
 * Modal générique façon Muffin : overlay plein écran + carte centrée.
 * Utilisé pour afficher le changelog, les CGU, le signalement de bug, etc.
 */
defineProps<{
  title: string;
  open: boolean;
}>();

const emit = defineEmits<{
  close: [];
}>();
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="info-modal__overlay" @click.self="emit('close')">
      <div class="info-modal" role="dialog" aria-modal="true" :aria-label="title">
        <div class="info-modal__header">
          <h2 class="info-modal__title">{{ title }}</h2>
          <button
            type="button"
            class="info-modal__close"
            aria-label="Fermer"
            @click="emit('close')"
          >
            <VIcon name="ri-close-line" />
          </button>
        </div>
        <div class="info-modal__body">
          <slot />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.info-modal__overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.4);
}

.info-modal {
  width: 100%;
  max-width: 48rem;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  background: var(--background-default-grey);
  border-radius: 0.5rem;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  overflow: hidden;
}

.info-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border-default-grey);
}

.info-modal__title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-title-grey);
}

.info-modal__close {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: none;
  border-radius: 0.375rem;
  background: transparent;
  color: var(--text-mention-grey);
  cursor: pointer;
  font-size: 1.25rem;
}

.info-modal__close:hover {
  background: var(--background-alt-grey-hover);
  color: var(--text-default-grey);
}

.info-modal__body {
  padding: 1.5rem;
  overflow-y: auto;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--text-default-grey);
}

.info-modal__body :deep(h2) {
  font-size: 1.1rem;
  font-weight: 700;
  margin: 1.5rem 0 0.5rem;
  color: var(--text-title-grey);
}

.info-modal__body :deep(h3) {
  font-size: 1rem;
  font-weight: 600;
  margin: 1rem 0 0.25rem;
  color: var(--text-title-grey);
}

.info-modal__body :deep(ul) {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}

.info-modal__body :deep(li) {
  margin: 0.25rem 0;
}

.info-modal__body :deep(a) {
  color: var(--text-action-high-blue-france);
}

.info-modal__body :deep(code) {
  padding: 0.125rem 0.375rem;
  background: var(--background-alt-grey);
  border-radius: 0.25rem;
  font-size: 0.85em;
}

.info-modal__body :deep(pre) {
  padding: 0.75rem;
  background: var(--background-alt-grey);
  border-radius: 0.375rem;
  overflow-x: auto;
}
</style>
