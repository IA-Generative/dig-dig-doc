<script setup lang="ts">
import { computed, ref } from "vue";

import GroupPicker from "@/components/access/GroupPicker.vue";
import { ASSIGNEES, ME } from "@/composables/useTracking";
import { useDossierAccess } from "@/composables/useDossierAccess";
import { VISIBILITY_HINTS, VISIBILITY_LABELS, type DossierAccess, type Visibility } from "@/types/access";

// Accès d'un dossier : visibilité et groupes associés. Lecture pour tous ceux
// qui y ont accès ; modification réservée aux administrateurs.
const props = defineProps<{ dossierId: string; dossierName: string }>();
const emit = defineEmits<{ close: []; saved: [message: string] }>();

const { isAdmin, myGroups, accessOf, lostMembers, groupsLostBy, setAccess, changesOf } = useDossierAccess();

const before = accessOf(props.dossierId);
const visibility = ref<Visibility>(before.visibility);
const groups = ref<string[]>([...before.groups]);
const confirmed = ref(false);

const draft = computed<DossierAccess>(() => ({ visibility: visibility.value, groups: groups.value }));
const dirty = computed(() => JSON.stringify(draft.value) !== JSON.stringify(before));

const nameOf = (id: string) => ASSIGNEES.find((a) => a.id === id)?.name ?? id;
const lost = computed(() => lostMembers(before, draft.value).filter((id) => id !== ME || !isAdmin.value));
const removedGroups = computed(() => groupsLostBy(before, draft.value));
const needsConfirmation = computed(() => dirty.value && lost.value.length > 0);

const errors = computed(() => {
  const list: string[] = [];
  if (visibility.value === "restricted" && groups.value.length === 0) {
    list.push("Un dossier restreint doit avoir au moins un groupe, sinon personne (hors administrateurs) ne pourrait l'ouvrir.");
  }
  return list;
});

const canSave = computed(
  () => isAdmin.value && dirty.value && errors.value.length === 0 && (!needsConfirmation.value || confirmed.value),
);

function save() {
  if (!canSave.value) return;
  setAccess(props.dossierId, draft.value);
  emit("saved", "Accès enregistré. Le changement est tracé dans l'historique du dossier.");
  emit("close");
}

const actions = computed(() => [
  ...(isAdmin.value ? [{ label: "Enregistrer", disabled: !canSave.value, onClick: save }] : []),
  { label: isAdmin.value ? "Annuler" : "Fermer", secondary: isAdmin.value, onClick: () => emit("close") },
]);

const dateLabel = (iso: string) => new Date(iso).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });
const visibilityOptions: Visibility[] = ["restricted", "analyse"];
</script>

<template>
  <DsfrModal :opened="true" title="Accès au dossier" icon="ri-lock-line" size="lg" :actions="actions" @close="emit('close')">
    <p class="am__name">{{ dossierName }}</p>

    <p v-if="!isAdmin" class="am__readonly" role="note">
      <VIcon name="ri-information-line" /> Seuls les administrateurs modifient l'accès à un dossier.
    </p>

    <fieldset class="am__group" :disabled="!isAdmin">
      <legend class="am__legend">Qui peut voir ce dossier ?</legend>
      <label v-for="v in visibilityOptions" :key="v" class="am__radio">
        <input v-model="visibility" type="radio" :value="v" />
        <span>
          <strong>{{ VISIBILITY_LABELS[v] }}</strong>
          <span class="am__hint">{{ VISIBILITY_HINTS[v] }}</span>
        </span>
      </label>
    </fieldset>

    <div v-if="visibility === 'restricted'" class="am__group">
      <GroupPicker
        v-model="groups"
        :options="myGroups"
        :disabled="!isAdmin"
        legend="Groupes ayant accès"
        hint="Vous ne pouvez associer que vos propres groupes. Un groupe ne donne pas accès à ses sous-groupes."
      />
    </div>

    <div v-if="needsConfirmation" class="am__impact" role="alert">
      <p class="am__impact-title"><VIcon name="ri-alert-line" /> Ces personnes perdront l'accès au dossier :</p>
      <ul>
        <li v-for="id in lost" :key="id">{{ nameOf(id) }}</li>
      </ul>
      <p class="am__impact-note">Leurs affectations à ce dossier seront annulées et tracées. L'historique du dossier et les documents générés restent en place.</p>
      <label class="am__confirm"><input v-model="confirmed" type="checkbox" /> J'ai compris</label>
    </div>
    <p v-else-if="dirty && removedGroups.length" class="am__hint">Aucune personne ne perd l'accès avec ce retrait.</p>

    <ul v-if="errors.length" class="am__errors" role="alert">
      <li v-for="e in errors" :key="e">{{ e }}</li>
    </ul>

    <section v-if="changesOf(dossierId).length" class="am__history" aria-labelledby="am-history">
      <h3 id="am-history" class="am__legend">Changements d'accès récents</h3>
      <ul>
        <li v-for="(c, i) in changesOf(dossierId)" :key="i">
          {{ c.text }} <span class="am__hint">— {{ c.by }}, {{ dateLabel(c.at) }}</span>
        </li>
      </ul>
    </section>
  </DsfrModal>
</template>

<style scoped>
.am__name {
  margin: 0 0 0.75rem;
  font-weight: 700;
}

.am__readonly {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  background: var(--background-alt-grey);
  font-size: 0.875rem;
}

.am__group {
  margin: 0 0 1rem;
  padding: 0;
  border: none;
}

.am__legend {
  margin: 0 0 0.5rem;
  font-size: 1rem;
  font-weight: 600;
}

.am__radio {
  display: flex;
  align-items: flex-start;
  gap: 0.625rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 0.5rem;
  margin-bottom: 0.5rem;
  cursor: pointer;
}

.am__radio span {
  display: flex;
  flex-direction: column;
}

.am__hint {
  font-size: 0.8125rem;
  font-weight: 400;
  color: var(--text-mention-grey);
}

.am__impact {
  margin: 0 0 1rem;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  background: var(--background-contrast-warning);
}

.am__impact-title {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  margin: 0 0 0.25rem;
  font-weight: 700;
}

.am__impact ul {
  margin: 0 0 0.5rem;
}

.am__impact-note {
  margin: 0 0 0.5rem;
  font-size: 0.875rem;
}

.am__confirm {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
}

.am__errors {
  margin: 0 0 1rem;
  padding-left: 1.25rem;
  color: var(--text-default-error);
  font-size: 0.875rem;
}

.am__history ul {
  margin: 0;
  padding-left: 1.25rem;
  font-size: 0.875rem;
}
</style>
