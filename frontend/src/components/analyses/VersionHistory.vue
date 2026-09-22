<script setup lang="ts" generic="T">
import type { Version } from "@/types/analyse";

defineProps<{
  versions: Version<T>[];
  formatContent: (content: T) => string;
}>();

const emit = defineEmits<{ restore: [versionId: string] }>();

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });
}
</script>

<template>
  <DsfrAccordion v-if="versions.length > 0" :title="`Historique des versions (${versions.length})`">
    <ul class="version-history__list">
      <li v-for="version in versions" :key="version.id" class="version-history__item">
        <div>
          <p class="fr-text--sm version-history__date">{{ formatDate(version.createdAt) }}</p>
          <p class="fr-text--sm version-history__content">{{ formatContent(version.content) }}</p>
        </div>
        <DsfrButton label="Restaurer" tertiary size="sm" @click="emit('restore', version.id)" />
      </li>
    </ul>
  </DsfrAccordion>
</template>

<style scoped>
.version-history__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.version-history__item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  border-top: 1px solid var(--border-default-grey);
  padding-top: 1rem;
}

.version-history__item:first-child {
  border-top: none;
  padding-top: 0;
}

.version-history__date {
  color: var(--text-mention-grey);
  margin: 0 0 0.25rem;
}

.version-history__content {
  margin: 0;
}
</style>
