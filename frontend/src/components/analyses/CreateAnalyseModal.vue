<script setup lang="ts">
import { ref, watch } from "vue";

import { useAnalyses } from "@/composables/useAnalyses";

const opened = defineModel<boolean>("opened", { default: false });
const emit = defineEmits<{ created: [] }>();

const { create } = useAnalyses();

const name = ref("");
const description = ref("");

watch(opened, (isOpened) => {
  if (isOpened) {
    name.value = "";
    description.value = "";
  }
});

async function submit() {
  if (!name.value.trim()) return;
  await create(name.value.trim(), description.value.trim());
  opened.value = false;
  emit("created");
}
</script>

<template>
  <DsfrModal
    :opened="opened"
    @close="opened = false"
    title="Créer une analyse"
    :actions="[
      { label: 'Annuler', secondary: true, onClick: () => (opened = false) },
      { label: 'Créer', onClick: submit },
    ]"
  >
    <DsfrInput v-model="name" label="Nom de l'analyse" label-visible required />
    <DsfrInput v-model="description" label="Description" label-visible is-textarea class="fr-mt-2w" />
  </DsfrModal>
</template>
