<script setup lang="ts">
import { computed } from "vue";

import { TEXT_EXTRACTION_STATUS_LABELS, type DossierDocument, type TextExtractionStatus } from "@/types/dossier";

const props = defineProps<{ documents: DossierDocument[] }>();

const statusBadgeType: Record<TextExtractionStatus, "new" | "info" | "success" | "error"> = {
  en_attente: "new",
  en_cours: "info",
  terminé: "success",
  échec: "error",
};

const statusIcon: Record<TextExtractionStatus, string> = {
  en_attente: "ri-time-line",
  en_cours: "ri-loader-4-line",
  terminé: "ri-check-line",
  échec: "ri-error-warning-line",
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

function fileIcon(mimetype: string): string {
  if (mimetype.startsWith("image/")) return "ri-image-line";
  if (mimetype === "application/pdf") return "ri-file-pdf-line";
  return "ri-file-line";
}

const hasActiveExtraction = computed(() =>
  props.documents.some((d) => d.textExtractionStatus === "en_cours" || d.textExtractionStatus === "en_attente"),
);
</script>

<template>
  <section v-if="documents.length > 0" class="dossier-documents">
    <div class="dossier-documents__header">
      <h2 class="fr-h6">Documents</h2>
      <span v-if="hasActiveExtraction" class="dossier-documents__hint fr-text--xs">
        Extraction de texte en cours…
      </span>
    </div>

    <ul class="dossier-documents__list">
      <li v-for="document in documents" :key="document.id" class="dossier-documents__item">
        <span class="dossier-documents__icon">
          <VIcon :name="fileIcon(document.mimetype)" />
        </span>

        <div class="dossier-documents__info">
          <span class="dossier-documents__name">{{ document.name }}</span>
          <span class="fr-text--xs dossier-documents__meta">{{ formatSize(document.size) }}</span>
          <DsfrBadge
            v-if="document.label"
            :label="document.label"
            type="info"
            small
            class="dossier-documents__label"
          />
        </div>

        <div class="dossier-documents__status">
          <VIcon
            :name="statusIcon[document.textExtractionStatus]"
            :class="{ 'dossier-documents__spinner': document.textExtractionStatus === 'en_cours' }"
          />
          <DsfrBadge
            :label="TEXT_EXTRACTION_STATUS_LABELS[document.textExtractionStatus]"
            :type="statusBadgeType[document.textExtractionStatus]"
            small
          />
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.dossier-documents {
  margin-bottom: 1.5rem;
}

.dossier-documents__header {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.dossier-documents__header h2 {
  margin: 0;
}

.dossier-documents__hint {
  color: var(--text-mention-grey);
}

.dossier-documents__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.dossier-documents__item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 0.5rem;
  background: var(--background-default-grey);
}

.dossier-documents__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.375rem;
  background: var(--background-alt-grey);
  color: var(--text-default-grey);
  flex-shrink: 0;
  font-size: 1.25rem;
}

.dossier-documents__info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
}

.dossier-documents__name {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dossier-documents__meta {
  color: var(--text-mention-grey);
}

.dossier-documents__label {
  align-self: flex-start;
}

.dossier-documents__status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.dossier-documents__spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
