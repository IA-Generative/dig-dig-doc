<script setup lang="ts">
// Une métrique : libellé, grande valeur, précision. Cliquable si `interactive`.
defineProps<{
  label: string;
  value: string | number;
  hint?: string;
  tone?: "neutral" | "error" | "warning" | "success";
  interactive?: boolean;
}>();
defineEmits<{ select: [] }>();
</script>

<template>
  <component
    :is="interactive ? 'button' : 'div'"
    class="metric"
    :class="[`metric--${tone ?? 'neutral'}`, { 'metric--interactive': interactive }]"
    :type="interactive ? 'button' : undefined"
    @click="interactive && $emit('select')"
  >
    <span class="metric__value">{{ value }}</span>
    <span class="metric__text">
      <span class="metric__label">{{ label }}</span>
      <span v-if="hint" class="metric__hint">{{ hint }}</span>
    </span>
  </component>
</template>

<style scoped>
.metric {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  padding: 0.375rem 0.625rem;
  border: none;
  border-radius: 0.75rem;
  background: var(--background-alt-grey);
  color: var(--text-default-grey);
  font: inherit;
  text-align: left;
}

.metric--interactive {
  cursor: pointer;
}

.metric--interactive:hover {
  background: var(--background-alt-grey-hover);
}

.metric__text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.2;
}

.metric__label {
  overflow: hidden;
  font-size: 0.75rem;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric__value {
  flex-shrink: 0;
  font-size: 1.25rem;
  font-weight: 800;
  line-height: 1;
}

.metric--error .metric__value {
  color: var(--text-default-error);
}

.metric--warning .metric__value {
  color: var(--text-default-warning);
}

.metric--success .metric__value {
  color: var(--text-default-success);
}

.metric__hint {
  overflow: hidden;
  font-size: 0.6875rem;
  color: var(--text-mention-grey);
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
