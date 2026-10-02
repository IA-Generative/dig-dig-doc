<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue";

import { draftErrorMessage } from "@/composables/useDocumentDrafts";

// Aperçu fidèle du document : le modèle rempli avec les valeurs courantes, rendu en PDF par le même moteur que le
// fichier final (la mise en page est conservée). Non éditable : on modifie les valeurs des champs, l'aperçu suit —
// après une courte pause suivant la dernière modification, ou au clic. Le serveur met en cache sur les valeurs.
const props = defineProps<{
  /** Change à chaque modification des valeurs : déclenche (avec une pause) la mise à jour de l'aperçu. */
  signature: string;
  load: () => Promise<Blob>;
}>();

const DEBOUNCE_MS = 700;
const url = ref("");
const loading = ref(false);
const error = ref("");
let timer: ReturnType<typeof setTimeout> | undefined;
let sequence = 0;

async function refresh() {
  const mine = ++sequence;
  loading.value = true;
  error.value = "";
  try {
    const blob = await props.load();
    if (mine !== sequence) return; // une mise à jour plus récente a pris le relais
    if (url.value) URL.revokeObjectURL(url.value.split("#")[0]);
    // Le visionneur du navigateur, ajusté à la largeur et sans panneau de vignettes (un document, quelques pages).
    url.value = `${URL.createObjectURL(blob)}#navpanes=0&view=FitH`;
  } catch (e) {
    if (mine === sequence) error.value = draftErrorMessage(e, "L'aperçu n'est pas disponible.");
  } finally {
    if (mine === sequence) loading.value = false;
  }
}

watch(
  () => props.signature,
  () => {
    if (timer) clearTimeout(timer);
    // La première fois, sans attendre ; ensuite après une pause (l'utilisateur peut enchaîner les modifications).
    timer = setTimeout(refresh, url.value ? DEBOUNCE_MS : 0);
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  if (timer) clearTimeout(timer);
  sequence++;
  if (url.value) URL.revokeObjectURL(url.value.split("#")[0]);
});

defineExpose({ refresh });
</script>

<template>
  <section class="pdf-preview" aria-label="Aperçu du document">
    <div class="pdf-preview__bar">
      <strong>Aperçu</strong>
      <span v-if="loading" class="fr-text--sm pdf-preview__state" role="status">Mise à jour…</span>
      <DsfrButton label="Actualiser" icon="ri-refresh-line" tertiary no-outline size="sm" :disabled="loading" @click="refresh" />
    </div>
    <DsfrAlert v-if="error" type="warning" :description="error" small />
    <iframe v-if="url" :src="url" class="pdf-preview__frame" title="Aperçu PDF du document" />
    <p v-else-if="!error" class="fr-text--sm pdf-preview__placeholder">Préparation de l'aperçu…</p>
    <p class="fr-text--xs pdf-preview__note">
      Les valeurs seulement proposées y figurent ; le document final n'utilise que les valeurs validées.
    </p>
  </section>
</template>

<style scoped>
.pdf-preview {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  height: 100%;
}

.pdf-preview__bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.pdf-preview__state {
  color: var(--text-mention-grey);
}

.pdf-preview__bar :deep(.fr-btn) {
  margin-left: auto;
}

.pdf-preview__frame {
  flex: 1;
  min-height: 32rem;
  width: 100%;
  border: 1px solid var(--border-default-grey);
  border-radius: 0.375rem;
  background: #fff;
}

.pdf-preview__placeholder,
.pdf-preview__note {
  margin: 0;
  color: var(--text-mention-grey);
}
</style>
