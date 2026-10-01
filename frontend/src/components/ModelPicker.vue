<script setup lang="ts">
/**
 * Sélecteur de modèle LLM compact, façon ChatGPT : un bouton discret (nom du
 * modèle + chevron) qui ouvre une liste flottante avec le choix courant
 * coché. Construit avec les classes et jetons du DSFR (fr-btn, couleurs
 * --background-*, --border-*) plutôt qu'avec un <select> natif.
 */
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

interface ModelOption {
  value: string;
  text: string;
}

const props = defineProps<{
  modelValue: string;
  options: ModelOption[];
  label?: string;
  disabled?: boolean;
}>();
const emit = defineEmits<{ "update:modelValue": [value: string] }>();

const rootRef = ref<HTMLElement | null>(null);
const isOpen = ref(false);
const listId = `model-picker-${Math.random().toString(36).slice(2, 8)}`;

const selectedText = computed(
  () => props.options.find((option) => option.value === props.modelValue)?.text ?? "Modèle par défaut",
);

function toggle() {
  if (!props.disabled) isOpen.value = !isOpen.value;
}

function select(value: string) {
  isOpen.value = false;
  if (value !== props.modelValue) emit("update:modelValue", value);
}

function onDocumentClick(event: MouseEvent) {
  if (isOpen.value && rootRef.value && !rootRef.value.contains(event.target as Node)) isOpen.value = false;
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") isOpen.value = false;
}

onMounted(() => document.addEventListener("click", onDocumentClick));
onBeforeUnmount(() => document.removeEventListener("click", onDocumentClick));
</script>

<template>
  <div ref="rootRef" class="model-picker" @keydown="onKeydown">
    <button
      type="button"
      class="fr-btn fr-btn--tertiary-no-outline fr-btn--sm model-picker__trigger"
      :aria-label="label ?? 'Modèle'"
      aria-haspopup="listbox"
      :aria-expanded="isOpen"
      :aria-controls="listId"
      :disabled="disabled"
      @click="toggle"
    >
      <span class="model-picker__value">{{ selectedText }}</span>
      <VIcon name="ri-arrow-down-s-line" class="model-picker__chevron" :class="{ 'model-picker__chevron--open': isOpen }" />
    </button>

    <ul v-if="isOpen" :id="listId" class="model-picker__menu" role="listbox" :aria-label="label ?? 'Modèle'">
      <li
        v-for="option in options"
        :key="option.value"
        role="option"
        :aria-selected="option.value === modelValue"
        class="model-picker__option"
        :class="{ 'model-picker__option--selected': option.value === modelValue }"
        tabindex="0"
        @click="select(option.value)"
        @keydown.enter.prevent="select(option.value)"
        @keydown.space.prevent="select(option.value)"
      >
        <span class="model-picker__option-text">{{ option.text }}</span>
        <VIcon v-if="option.value === modelValue" name="ri-check-line" />
      </li>
    </ul>
  </div>
</template>

<style scoped>
.model-picker {
  position: relative;
  display: inline-block;
  max-width: 100%;
}

.model-picker__trigger {
  max-width: 100%;
  gap: 0.25rem;
  font-weight: 600;
  font-size: 1rem;
  color: var(--text-title-grey);
}

.model-picker__value {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.model-picker__chevron {
  flex-shrink: 0;
  transition: transform 0.15s ease;
}

.model-picker__chevron--open {
  transform: rotate(180deg);
}

.model-picker__menu {
  position: absolute;
  z-index: 20;
  top: calc(100% + 0.25rem);
  left: 0;
  min-width: 14rem;
  max-width: min(22rem, 90vw);
  max-height: 20rem;
  overflow-y: auto;
  margin: 0;
  padding: 0.375rem;
  list-style: none;
  background: var(--background-overlap-grey);
  border: 1px solid var(--border-default-grey);
  border-radius: 0.75rem;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16);
}

.model-picker__option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.5rem 0.625rem;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.9rem;
  color: var(--text-default-grey);
}

.model-picker__option:hover,
.model-picker__option:focus-visible {
  background: var(--background-overlap-grey-hover);
  outline: none;
}

.model-picker__option--selected {
  font-weight: 600;
}

.model-picker__option-text {
  overflow-wrap: anywhere;
}
</style>
