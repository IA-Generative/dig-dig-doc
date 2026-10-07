<script setup lang="ts">
import { computed, ref, watch } from "vue";

import GroupPicker from "@/components/access/GroupPicker.vue";
import { useAnalyses } from "@/composables/useAnalyses";
import { useDossierAccess } from "@/composables/useDossierAccess";
import { useDossiers } from "@/composables/useDossiers";

const opened = defineModel<boolean>("opened", { default: false });
const emit = defineEmits<{ created: [] }>();

const { list: analyses, fetchList: fetchAnalyses } = useAnalyses();
const { create, addDocuments } = useDossiers();
const { myGroups, initAccess } = useDossierAccess();

// MOCK (#177) : un nouveau dossier est restreint par défaut ; il faut au moins
// un des groupes de l'utilisateur, sinon le créateur lui-même ne pourrait plus l'ouvrir.
const restricted = ref(true);
const accessGroups = ref<string[]>([]);
const accessInvalid = computed(() => restricted.value && accessGroups.value.length === 0);

const analyseOptions = computed(() => analyses.value.map((analyse) => ({ value: analyse.id, text: analyse.name })));

const name = ref("");
const analyseId = ref<string | undefined>(undefined);
const aRanger = ref(false);
const files = ref<File[]>([]);

watch(opened, async (isOpened) => {
  if (isOpened) {
    name.value = "";
    files.value = [];
    aRanger.value = false;
    restricted.value = true;
    accessGroups.value = myGroups.value.length === 1 ? [...myGroups.value] : [];
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
  if (!name.value.trim()) return;
  if (!aRanger.value && !analyseId.value) return;
  if (accessInvalid.value) return;
  const dossier = await create(name.value.trim(), aRanger.value ? undefined : analyseId.value);
  initAccess(dossier.id, restricted.value ? { visibility: "restricted", groups: accessGroups.value } : { visibility: "analyse", groups: [] });
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
      { label: 'Créer', onClick: submit, disabled: !name.trim() || (!aRanger && !analyseId) || accessInvalid },
    ]"
  >
    <DsfrInput v-model="name" label="Nom du dossier" label-visible required />

    <div class="fr-mt-2w">
      <DsfrToggleSwitch
        v-model="aRanger"
        label="Dossier à ranger (sans analyse)"
        hint="Crée le dossier sans analyse rattachée. Des suggestions d'analyse seront générées automatiquement à partir des résumés des documents."
        inline
      />
    </div>

    <DsfrSelect
      v-if="!aRanger"
      v-model="analyseId"
      label="Analyse"
      hint="Obligatoire : un dossier doit être lié à une analyse."
      required
      class="fr-mt-2w"
      :options="analyseOptions"
    />

    <div class="fr-mt-2w">
      <DsfrToggleSwitch
        v-model="restricted"
        label="Dossier restreint"
        hint="Seuls les groupes choisis (et les administrateurs) voient ce dossier. Sinon, toute personne ayant accès à l'analyse le voit."
        inline
      />
      <GroupPicker
        v-if="restricted"
        v-model="accessGroups"
        :options="myGroups"
        legend="Groupes ayant accès"
        hint="Au moins un groupe est obligatoire : vos propres groupes uniquement."
      />
      <p v-if="accessInvalid" class="fr-error-text" role="alert">Choisissez au moins un groupe.</p>
    </div>

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
