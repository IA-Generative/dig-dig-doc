<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { useAnalyses } from "@/composables/useAnalyses";
import { useDossiers } from "@/composables/useDossiers";

const opened = defineModel<boolean>("opened", { default: false });
const emit = defineEmits<{ created: [] }>();

const { list: analyses, fetchList: fetchAnalyses } = useAnalyses();
const { create, addDocuments } = useDossiers();

const analyseOptions = computed(() => analyses.value.map((analyse) => ({ value: analyse.id, text: analyse.name })));

const name = ref("");
const analyseId = ref<string | undefined>(undefined);
const files = ref<File[]>([]);

watch(opened, async (isOpened) => {
  if (isOpened) {
    name.value = "";
    files.value = [];
    // La liste par défaut (useAnalyses) est paginée pour l'affichage ;
    // ce select doit lister toutes les analyses disponibles, donc on
    // recharge avec la taille de page maximale plutôt que de dépendre de
    // la page actuellement affichée sur AnalysesPage.
    await fetchAnalyses(1, 100);
    analyseId.value = analyses.value[0]?.id;
  }
});

function onFilesSelected(fileList: FileList) {
  files.value.push(...Array.from(fileList));
}

function removeFile(index: number) {
  files.value.splice(index, 1);
}

function formatSize(bytes: number) {
  return bytes < 1_000_000 ? `${Math.round(bytes / 1000)} Ko` : `${(bytes / 1_000_000).toFixed(1)} Mo`;
}

async function submit() {
  if (!name.value.trim() || !analyseId.value) return;
  const dossier = await create(name.value.trim(), analyseId.value);
  if (files.value.length > 0) await addDocuments(dossier.id, files.value);
  opened.value = false;
  emit("created");
}
</script>

<template>
  <DsfrModal
    :opened="opened"
    @close="opened = false"
    title="Créer un dossier"
    size="lg"
    :actions="[
      { label: 'Annuler', secondary: true, onClick: () => (opened = false) },
      { label: 'Créer', onClick: submit, disabled: !analyseId },
    ]"
  >
    <DsfrInput v-model="name" label="Nom du dossier" label-visible required />
    <DsfrSelect
      v-model="analyseId"
      label="Analyse"
      hint="Obligatoire : un dossier doit être lié à une analyse."
      required
      class="fr-mt-2w"
      :options="analyseOptions"
    />

    <DsfrFileUpload
      id="dossier-documents"
      label="Documents et images du dossier"
      hint="PDF, JPG ou PNG."
      accept=".pdf,image/*"
      class="fr-mt-2w"
      @change="onFilesSelected"
    />

    <ul v-if="files.length > 0" class="create-dossier-modal__files">
      <li v-for="(file, index) in files" :key="`${file.name}-${index}`" class="create-dossier-modal__file">
        <span>{{ file.name }} ({{ formatSize(file.size) }})</span>
        <DsfrButton
          label="Retirer le fichier"
          icon-only
          tertiary
          icon="ri-close-line"
          size="sm"
          @click="removeFile(index)"
        />
      </li>
    </ul>
  </DsfrModal>
</template>

<style scoped>
.create-dossier-modal__files {
  list-style: none;
  margin: 1rem 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.create-dossier-modal__file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 0.25rem;
}
</style>
