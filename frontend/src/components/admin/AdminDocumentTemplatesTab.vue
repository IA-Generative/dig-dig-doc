<script setup lang="ts">
import { computed, ref } from "vue";

import GenerationPromptPanel from "@/components/admin/GenerationPromptPanel.vue";
import DocumentTemplateEditor from "@/components/admin/documentTemplates/DocumentTemplateEditor.vue";
import { errorMessage, useDocumentTemplates } from "@/composables/useDocumentTemplates";
import type { AnalyseOption, DocumentTemplate } from "@/types/documentTemplate";

/** Écrit un placeholder comme dans le fichier : {{ nom }} (hors gabarit, où « }} » fermerait l'interpolation). */
const braces = (name: string) => `{{ ${name} }}`;

// Administration des modèles de document (backend issues #138 et #141) : liste, création, édition des champs
// avec rapport de validation, historique des versions, et prompt de l'agent de génération.
const api = useDocumentTemplates();

const analyses = ref<AnalyseOption[]>([]);
// Les modèles se gèrent **par analyse** : tout part de l'analyse choisie.
const analyseId = ref("");
const templates = ref<DocumentTemplate[]>([]);
const includeArchived = ref(false);
const loading = ref(false);
const error = ref("");
const editing = ref<DocumentTemplate | null>(null);
const creating = ref(false);
const promptPanel = ref<InstanceType<typeof GenerationPromptPanel>>();

const analyseName = computed(() => analyses.value.find((a) => a.id === analyseId.value)?.name ?? "");
const analyseOptions = computed(() => [
  { value: "", text: analyses.value.length ? "Choisir une analyse…" : "Aucune analyse" },
  ...analyses.value.map((a) => ({ value: a.id, text: a.name })),
]);

async function loadTemplates() {
  if (!analyseId.value) {
    templates.value = [];
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    templates.value = await api.fetchTemplates(analyseId.value, includeArchived.value);
  } catch (e) {
    error.value = errorMessage(e, "Impossible de charger les modèles de document.");
  } finally {
    loading.value = false;
  }
}

async function reload() {
  loading.value = true;
  error.value = "";
  try {
    analyses.value = await api.fetchAnalyses();
    if (!analyses.value.some((a) => a.id === analyseId.value)) analyseId.value = analyses.value[0]?.id ?? "";
    templates.value = analyseId.value ? await api.fetchTemplates(analyseId.value, includeArchived.value) : [];
  } catch (e) {
    error.value = errorMessage(e, "Impossible de charger les modèles de document.");
  } finally {
    loading.value = false;
  }
  void promptPanel.value?.reload();
}

function closeEditor() {
  editing.value = null;
  creating.value = false;
  void reload();
}

const dateFormatter = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" });

defineExpose({ reload });
</script>

<template>
  <section class="templates-admin">
    <DocumentTemplateEditor
      v-if="creating || editing"
      :key="editing?.id ?? 'new'"
      :template="editing"
      :analyse-id="editing?.analyseId ?? analyseId"
      :analyse-name="analyseName"
      @cancel="closeEditor"
      @changed="reload"
      @saved="reload"
    />

    <template v-else>
      <div class="templates-admin__header">
        <h2 class="fr-h4">Modèles de document</h2>
        <DsfrButton label="Nouveau modèle" icon="ri-add-line" :disabled="!analyseId" @click="creating = true" />
      </div>
      <p class="fr-text--sm">
        Un modèle est un fichier ODT avec des champs <code>{{ braces("nom") }}</code> et la définition de ces champs. Il
        appartient à <strong>une analyse</strong> : il ne sert qu'aux dossiers de cette analyse, et ses champs puisent dans
        ce qu'elle définit (entités, labels, agents).
      </p>

      <DsfrSelect
        v-model="analyseId"
        label="Analyse"
        label-visible
        :options="analyseOptions"
        @update:model-value="loadTemplates"
      />

      <DsfrAlert v-if="error" type="error" :description="error" small />
      <DsfrCheckbox
        v-model="includeArchived"
        name="include-archived"
        label="Afficher les modèles archivés"
        @update:model-value="loadTemplates"
      />

      <p v-if="loading" class="fr-text--sm">Chargement…</p>
      <p v-else-if="!analyseId" class="fr-text--sm">Choisissez une analyse pour voir ses modèles.</p>
      <p v-else-if="templates.length === 0" class="fr-text--sm">Cette analyse n'a pas encore de modèle de document.</p>
      <ul v-else class="templates-admin__list">
        <li v-for="t in templates" :key="t.id" class="templates-admin__item">
          <div class="templates-admin__item-main">
            <div class="templates-admin__item-title">
              <strong>{{ t.name }}</strong>
              <DsfrBadge :label="`Version ${t.versionNumber}`" small />
              <DsfrBadge v-if="t.archived" label="Archivé" type="warning" small />
            </div>
            <p v-if="t.description" class="fr-text--sm templates-admin__item-desc">{{ t.description }}</p>
            <p class="fr-text--sm templates-admin__item-meta">
              {{ t.fields.length }} champ(s) · {{ t.fileName }} · modifié le {{ dateFormatter.format(new Date(t.updatedAt)) }}
            </p>
          </div>
          <DsfrButton label="Modifier" secondary size="sm" @click="editing = t" />
        </li>
      </ul>

      <hr class="templates-admin__separator" />
      <GenerationPromptPanel ref="promptPanel" />
    </template>
  </section>
</template>

<style scoped>
.templates-admin {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.templates-admin__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.templates-admin__header h2 {
  margin: 0;
}

.templates-admin__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.templates-admin__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 0.375rem;
}

.templates-admin__item-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.templates-admin__item-desc,
.templates-admin__item-meta {
  margin: 0.25rem 0 0;
}

.templates-admin__item-meta {
  color: var(--text-mention-grey);
}

.templates-admin__separator {
  width: 100%;
  margin: 0.5rem 0;
}
</style>
