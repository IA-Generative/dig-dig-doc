<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, type RouteLocationRaw } from "vue-router";

// Barres horizontales simples (libellé, barre, valeur) : la valeur est
// toujours écrite, la barre n'est qu'un repère visuel.
// `to` : lien optionnel du libellé (par exemple vers le suivi filtré).
const props = defineProps<{ items: { label: string; value: number; to?: RouteLocationRaw }[] }>();

const max = computed(() => Math.max(1, ...props.items.map((i) => i.value)));
</script>

<template>
  <ul class="bars">
    <li v-for="i in items" :key="i.label" class="bars__row">
      <RouterLink v-if="i.to" :to="i.to" class="bars__label bars__link">{{ i.label }}</RouterLink>
      <span v-else class="bars__label">{{ i.label }}</span>
      <span class="bars__track" aria-hidden="true">
        <span class="bars__fill" :style="{ width: `${(i.value / max) * 100}%` }" />
      </span>
      <span class="bars__value">{{ i.value }}</span>
    </li>
  </ul>
</template>

<style scoped>
.bars {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.bars__row {
  display: grid;
  grid-template-columns: minmax(6rem, 10rem) 1fr 2rem;
  align-items: center;
  gap: 0.625rem;
  font-size: 0.875rem;
}

.bars__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bars__link {
  background-image: none;
  color: var(--text-action-high-blue-france);
}

.bars__track {
  height: 0.5rem;
  border-radius: 0.25rem;
  background: var(--background-alt-grey);
  overflow: hidden;
}

.bars__fill {
  display: block;
  height: 100%;
  border-radius: 0.25rem;
  background: var(--background-action-high-blue-france);
}

.bars__value {
  font-weight: 700;
  text-align: right;
}
</style>
