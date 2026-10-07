<script setup lang="ts">
import { ref } from "vue";

// Aide d'une colonne : petit bouton « i » dans l'en-tête qui ouvre une bulle
// avec la definition (clic ou clavier ; Échap ou sortie pour fermer).
const props = defineProps<{ label: string; definition: string }>();

const open = ref(false);
const id = `colhelp-${Math.random().toString(36).slice(2, 8)}`;
</script>

<template>
  <span v-if="props.definition" class="help" @keydown.esc="open = false" @focusout="open = false">
    <button
      type="button"
      class="help__btn"
      :aria-expanded="open"
      :aria-controls="id"
      :aria-label="`Aide sur la colonne ${label}`"
      @click.stop="open = !open"
    >
      <VIcon name="ri-information-line" />
    </button>
    <span v-show="open" :id="id" class="help__bubble" role="note">{{ definition }}</span>
  </span>
</template>

<style scoped>
.help {
  position: relative;
  display: inline-block;
  text-transform: none;
  letter-spacing: normal;
}

.help__btn {
  display: flex;
  padding: 0;
  border: none;
  background: none;
  color: var(--text-mention-grey);
  cursor: pointer;
}

.help__btn:hover {
  color: var(--text-default-grey);
}

.help__bubble {
  position: absolute;
  top: 1.5rem;
  left: -0.5rem;
  z-index: 10;
  width: 16rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 0.5rem;
  background: var(--background-default-grey);
  box-shadow: 0 4px 12px rgb(0 0 0 / 15%);
  color: var(--text-default-grey);
  font-size: 0.8125rem;
  font-weight: 400;
  white-space: normal;
}
</style>
