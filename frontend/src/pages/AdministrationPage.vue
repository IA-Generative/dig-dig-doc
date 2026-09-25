<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import MarkdownText from "@/components/MarkdownText.vue";
import { useAdminStats } from "@/composables/useAdminStats";
import { useAdminTasks } from "@/composables/useAdminTasks";
import { useReportsAdmin } from "@/composables/useReportsAdmin";
import { useCgu } from "@/composables/useCgu";
import { REPORT_STATUS_LABELS, REPORT_TYPE_LABELS, type ReportStatus, type ReportType } from "@/types/report";
import { API_BASE_URL } from "@/utils/api";
import { renderMarkdown } from "@/utils/markdown";

const { reports, pageCount, fetchList, updateReport } = useReportsAdmin();
const { versions, fetchVersions, createVersion, updateVersion, activateVersion } = useCgu();
const { stats: adminStats, loading: statsLoading, error: statsError, fetchStats } = useAdminStats();
const { tasks: adminTasks, loading: tasksLoading, error: tasksError, fetchTasks } = useAdminTasks();

const PAGE_SIZE = 10;
const currentPage = ref(1);
const statusFilter = ref<ReportStatus | "">("");
const typeFilter = ref<ReportType | "">("");

const statusFilterOptions = [
  { value: "", text: "Tous les statuts" },
  ...(Object.keys(REPORT_STATUS_LABELS) as ReportStatus[]).map((value) => ({
    value,
    text: REPORT_STATUS_LABELS[value],
  })),
];
const typeFilterOptions = [
  { value: "", text: "Tous les types" },
  ...(Object.keys(REPORT_TYPE_LABELS) as ReportType[]).map((value) => ({ value, text: REPORT_TYPE_LABELS[value] })),
];

function reload() {
  fetchList(currentPage.value, PAGE_SIZE, statusFilter.value || undefined, typeFilter.value || undefined);
}

watch(currentPage, reload, { immediate: true });
watch([statusFilter, typeFilter], () => {
  currentPage.value = 1;
  reload();
});

const pages = computed(() =>
  Array.from({ length: pageCount.value }, (_, i) => ({ label: String(i + 1), title: `Page ${i + 1}` })),
);

const statusBadgeType: Record<ReportStatus, "new" | "info" | "success" | "warning" | "error"> = {
  new: "new",
  in_progress: "info",
  resolved: "success",
  wont_fix: "warning",
};

// Brouillon de réponse par signalement, tant qu'il n'a pas été envoyé.
const draftResponses = ref<Record<string, string>>({});

function draftFor(reportId: string, current: string | null) {
  return draftResponses.value[reportId] ?? current ?? "";
}

async function setStatus(reportId: string, status: ReportStatus) {
  await updateReport(reportId, status, null);
}

async function submitResponse(reportId: string) {
  const response = (draftResponses.value[reportId] ?? "").trim();
  if (!response) return;
  await updateReport(reportId, "resolved", response);
  delete draftResponses.value[reportId];
}

const dateFormatter = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" });
function formatDate(iso: string) {
  return dateFormatter.format(new Date(iso));
}

const dayFormatter = new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short" });
function formatDay(iso: string) {
  return dayFormatter.format(new Date(iso));
}

const DOSSIER_STATUS_LABELS: Record<string, string> = {
  en_attente: "En attente",
  en_cours: "En cours",
  termine: "Terminé",
  echec: "Échec",
};

const statCards = computed(() => {
  if (!adminStats.value) return [];
  return [
    { label: "Analyses", value: adminStats.value.analyses_count, icon: "ri-file-search-line" },
    { label: "Dossiers", value: adminStats.value.dossiers_count, icon: "ri-folder-line" },
    { label: "Conversations", value: adminStats.value.conversations_count, icon: "ri-chat-3-line" },
    { label: "Messages", value: adminStats.value.messages_count, icon: "ri-mail-send-line" },
    { label: "Conversations assistant", value: adminStats.value.agent_conversations_count, icon: "ri-robot-2-line" },
    { label: "Messages assistant", value: adminStats.value.agent_messages_count, icon: "ri-message-3-line" },
    { label: "Signalements", value: adminStats.value.reports_count, icon: "ri-bug-line" },
    { label: "Utilisateurs (préférences)", value: adminStats.value.users_count, icon: "ri-user-line" },
  ];
});

const maxDailyCount = computed(() => {
  if (!adminStats.value) return 0;
  return Math.max(1, ...adminStats.value.daily_creations.map((d) => d.count));
});

onMounted(reload);
onMounted(() => {
  fetchStats();
  fetchTasks();
});

// ── CGU admin ────────────────────────────────────────────────────────────
const cguDraft = ref("");
const cguPreviewHtml = ref("");
const cguShowPreview = ref(false);
const cguSaving = ref(false);
const cguError = ref("");
const cguSuccess = ref("");

async function reloadCgu() {
  try {
    await fetchVersions();
  } catch {
    cguError.value = "Impossible de charger les versions des CGU.";
  }
}

watch(cguDraft, (value) => {
  if (cguShowPreview.value) cguPreviewHtml.value = renderMarkdown(value);
});

function togglePreview() {
  cguShowPreview.value = !cguShowPreview.value;
  if (cguShowPreview.value) cguPreviewHtml.value = renderMarkdown(cguDraft.value);
}

async function handleCreateVersion() {
  const content = cguDraft.value.trim();
  if (!content) return;
  cguSaving.value = true;
  cguError.value = "";
  cguSuccess.value = "";
  try {
    await createVersion(content);
    cguDraft.value = "";
    cguPreviewHtml.value = "";
    cguSuccess.value = "Nouvelle version créée. Pensez à l'activer pour la publier.";
    await reloadCgu();
  } catch {
    cguError.value = "Erreur lors de la création de la version.";
  } finally {
    cguSaving.value = false;
  }
}

async function handleActivate(id: string) {
  if (!confirm("Activer cette version ? Tous les utilisateurs devront l'accepter à nouveau.")) return;
  cguError.value = "";
  cguSuccess.value = "";
  try {
    await activateVersion(id);
    cguSuccess.value = "Version activée. Les utilisateurs devront l'accepter à leur prochaine connexion.";
    await reloadCgu();
  } catch {
    cguError.value = "Erreur lors de l'activation de la version.";
  }
}

async function handleUpdate(id: string) {
  const content = cguDraft.value.trim();
  if (!content) return;
  cguSaving.value = true;
  cguError.value = "";
  cguSuccess.value = "";
  try {
    await updateVersion(id, content);
    cguDraft.value = "";
    cguPreviewHtml.value = "";
    cguSuccess.value = "Version mise à jour.";
    await reloadCgu();
  } catch {
    cguError.value = "Erreur lors de la mise à jour. Une version active ne peut pas être modifiée.";
  } finally {
    cguSaving.value = false;
  }
}

function loadVersionIntoEditor(version: typeof versions.value[number]) {
  cguDraft.value = version.content;
  if (cguShowPreview.value) cguPreviewHtml.value = renderMarkdown(version.content);
}

onMounted(reloadCgu);
</script>

<template>
  <div class="administration-page">
    <h1 class="fr-h2">Administration</h1>

    <section class="administration-page__section">
      <h2 class="fr-h4">Signalements</h2>

      <div class="administration-page__filters">
        <DsfrSelect v-model="statusFilter" label="Statut" label-visible :options="statusFilterOptions" />
        <DsfrSelect v-model="typeFilter" label="Type" label-visible :options="typeFilterOptions" />
      </div>

      <p v-if="reports.length === 0" class="fr-text--sm">Aucun signalement.</p>

      <ul v-else class="administration-page__list">
        <li v-for="report in reports" :key="report.id" class="administration-page__item">
          <div class="administration-page__item-header">
            <div>
              <span class="administration-page__item-title">{{ report.title }}</span>
              <p class="fr-text--sm administration-page__item-meta">
                {{ REPORT_TYPE_LABELS[report.type] }} · {{ report.userDisplay }} · {{ formatDate(report.createdAt) }}
              </p>
            </div>
            <DsfrBadge :label="REPORT_STATUS_LABELS[report.status]" :type="statusBadgeType[report.status]" />
          </div>

          <MarkdownText :content="report.description" :lines="3" class="administration-page__item-description" />

          <a
            v-if="report.hasScreenshot"
            :href="`${API_BASE_URL}/api/reports/${report.id}/screenshot`"
            target="_blank"
            rel="noopener noreferrer"
            class="fr-link fr-text--sm"
          >
            Voir la capture d'écran jointe
          </a>

          <div class="administration-page__item-response">
            <DsfrInput
              :model-value="draftFor(report.id, report.adminResponse)"
              label="Réponse"
              label-visible
              is-textarea
              @update:model-value="(value: string) => (draftResponses[report.id] = value)"
            />
            <div class="administration-page__item-actions">
              <DsfrButton label="Envoyer la réponse (marque comme résolu)" size="sm" @click="submitResponse(report.id)" />
              <DsfrButton
                v-if="report.status !== 'in_progress'"
                label="Marquer en cours"
                tertiary
                size="sm"
                @click="setStatus(report.id, 'in_progress')"
              />
              <DsfrButton
                v-if="report.status !== 'wont_fix'"
                label="Refuser"
                tertiary
                size="sm"
                @click="setStatus(report.id, 'wont_fix')"
              />
            </div>
          </div>
        </li>
      </ul>

      <DsfrPagination
        v-if="pageCount > 1"
        :pages="pages"
        v-model:current-page="currentPage"
        class="administration-page__pagination"
      />
    </section>

    <section class="administration-page__section">
      <h2 class="fr-h4">
        <VIcon name="ri-bar-chart-2-line" class="fr-mr-1w" />
        Statistiques
      </h2>

      <div v-if="statsError" class="fr-alert fr-alert--error fr-mb-2w">{{ statsError }}</div>
      <div v-if="statsLoading" class="fr-text--sm">Chargement des statistiques…</div>

      <template v-else-if="adminStats">
        <div class="admin-stats__cards">
          <div v-for="card in statCards" :key="card.label" class="admin-stats__card">
            <VIcon :name="card.icon" class="admin-stats__card-icon" />
            <div>
              <div class="admin-stats__card-value">{{ card.value }}</div>
              <div class="admin-stats__card-label">{{ card.label }}</div>
            </div>
          </div>
        </div>

        <div class="admin-stats__grid">
          <div class="admin-stats__panel">
            <h3 class="fr-text--lg fr-mb-1w">Dossiers par statut</h3>
            <ul class="admin-stats__status-list">
              <li v-for="(count, key) in adminStats.dossiers_by_status" :key="key" class="admin-stats__status-item">
                <span class="admin-stats__status-label">{{ DOSSIER_STATUS_LABELS[key] ?? key }}</span>
                <span class="admin-stats__status-count">{{ count }}</span>
              </li>
            </ul>
          </div>

          <div class="admin-stats__panel">
            <h3 class="fr-text--lg fr-mb-1w">Créations de dossiers (7 derniers jours)</h3>
            <div v-if="adminStats.daily_creations.length === 0" class="fr-text--sm">Aucune création récente.</div>
            <div v-else class="admin-stats__chart">
              <div
                v-for="day in adminStats.daily_creations"
                :key="day.date"
                class="admin-stats__chart-bar"
                :title="`${formatDay(day.date)}: ${day.count}`"
              >
                <div
                  class="admin-stats__chart-fill"
                  :style="{ height: `${(day.count / maxDailyCount) * 100}%` }"
                />
                <span class="admin-stats__chart-label">{{ formatDay(day.date) }}</span>
                <span class="admin-stats__chart-value">{{ day.count }}</span>
              </div>
            </div>
          </div>

          <div class="admin-stats__panel">
            <h3 class="fr-text--lg fr-mb-1w">Top modèles LLM</h3>
            <div v-if="adminStats.top_models.length === 0" class="fr-text--sm">Aucun modèle utilisé.</div>
            <ul v-else class="admin-stats__models">
              <li v-for="(model, i) in adminStats.top_models" :key="model.model" class="admin-stats__model">
                <span class="admin-stats__model-rank">{{ i + 1 }}</span>
                <span class="admin-stats__model-name">{{ model.model }}</span>
                <span class="admin-stats__model-count">{{ model.count }}</span>
              </li>
            </ul>
          </div>
        </div>
      </template>
    </section>

    <section class="administration-page__section">
      <div class="admin-tasks__header">
        <h2 class="fr-h4">
          <VIcon name="ri-list-check-2" class="fr-mr-1w" />
          Tâches Celery
        </h2>
        <DsfrButton label="Rafraîchir" tertiary size="sm" @click="fetchTasks" />
      </div>

      <div v-if="tasksError" class="fr-alert fr-alert--error fr-mb-2w">{{ tasksError }}</div>
      <div v-if="tasksLoading" class="fr-text--sm">Chargement des tâches…</div>

      <template v-else-if="adminTasks">
        <p v-if="adminTasks.workers.length === 0" class="fr-text--sm">
          Aucun worker Celery actuellement en ligne.
        </p>
        <div v-else class="admin-tasks__workers">
          <DsfrBadge
            v-for="worker in adminTasks.workers"
            :key="worker"
            :label="worker"
            type="success"
          />
        </div>

        <div class="admin-tasks__grid">
          <div class="admin-tasks__panel">
            <h3 class="fr-text--lg fr-mb-1w">
              Actives
              <span class="admin-tasks__count">({{ adminTasks.active.length }})</span>
            </h3>
            <p v-if="adminTasks.active.length === 0" class="fr-text--sm">Aucune tâche active.</p>
            <ul v-else class="admin-tasks__list">
              <li v-for="task in adminTasks.active" :key="task.id ?? task.name" class="admin-tasks__item">
                <span class="admin-tasks__item-name">{{ task.name }}</span>
                <span class="admin-tasks__item-worker">{{ task.worker }}</span>
              </li>
            </ul>
          </div>

          <div class="admin-tasks__panel">
            <h3 class="fr-text--lg fr-mb-1w">
              Réservées
              <span class="admin-tasks__count">({{ adminTasks.reserved.length }})</span>
            </h3>
            <p v-if="adminTasks.reserved.length === 0" class="fr-text--sm">Aucune tâche réservée.</p>
            <ul v-else class="admin-tasks__list">
              <li v-for="task in adminTasks.reserved" :key="task.id ?? task.name" class="admin-tasks__item">
                <span class="admin-tasks__item-name">{{ task.name }}</span>
                <span class="admin-tasks__item-worker">{{ task.worker }}</span>
              </li>
            </ul>
          </div>

          <div class="admin-tasks__panel">
            <h3 class="fr-text--lg fr-mb-1w">
              Enregistrées
              <span class="admin-tasks__count">({{ adminTasks.registered.length }})</span>
            </h3>
            <p v-if="adminTasks.registered.length === 0" class="fr-text--sm">Aucune tâche enregistrée.</p>
            <ul v-else class="admin-tasks__list admin-tasks__list--scroll">
              <li v-for="task in adminTasks.registered" :key="task.name" class="admin-tasks__item">
                <span class="admin-tasks__item-name">{{ task.name }}</span>
                <span class="admin-tasks__item-worker">{{ task.worker }}</span>
              </li>
            </ul>
          </div>
        </div>
      </template>
    </section>

    <section class="administration-page__section">
      <h2 class="fr-h4">Conditions d'utilisation (CGU)</h2>

      <div v-if="cguError" class="fr-alert fr-alert--error fr-mb-2w">{{ cguError }}</div>
      <div v-if="cguSuccess" class="fr-alert fr-alert--success fr-mb-2w">{{ cguSuccess }}</div>

      <div class="cgu-admin__editor">
        <div class="cgu-admin__editor-toolbar">
          <DsfrButton label="Aperçu" tertiary size="sm" @click="togglePreview" />
        </div>
        <div v-if="cguShowPreview" class="cgu-admin__preview markdown" v-html="cguPreviewHtml" />
        <DsfrInput
          v-else
          v-model="cguDraft"
          label="Nouveau contenu (Markdown)"
          label-visible
          is-textarea
          :rows="12"
        />
        <div class="cgu-admin__editor-actions">
          <DsfrButton
            label="Créer une version"
            :disabled="cguSaving || !cguDraft.trim()"
            size="sm"
            @click="handleCreateVersion"
          />
        </div>
      </div>

      <p v-if="versions.length === 0" class="fr-text--sm">Aucune version des CGU pour le moment.</p>
      <ul v-else class="cgu-admin__list">
        <li v-for="v in versions" :key="v.id" class="cgu-admin__item">
          <div class="cgu-admin__item-header">
            <span class="cgu-admin__item-version">Version {{ v.version }}</span>
            <DsfrBadge
              v-if="v.isActive"
              label="Active"
              type="success"
            />
            <span v-else class="cgu-admin__item-status">Inactive</span>
          </div>
          <p class="fr-text--sm cgu-admin__item-meta">
            Créée le {{ formatDate(v.createdAt) }}<span v-if="v.publishedAt"> · Publiée le {{ formatDate(v.publishedAt) }}</span>
          </p>
          <div class="cgu-admin__item-actions">
            <DsfrButton label="Éditer" tertiary size="sm" @click="loadVersionIntoEditor(v)" />
            <DsfrButton
              v-if="!v.isActive"
              label="Activer"
              size="sm"
              @click="handleActivate(v.id)"
            />
            <DsfrButton
              v-if="!v.isActive"
              label="Mettre à jour"
              tertiary
              size="sm"
              :disabled="cguSaving || !cguDraft.trim()"
              @click="handleUpdate(v.id)"
            />
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.administration-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.administration-page__section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.administration-page__filters {
  display: flex;
  gap: 1rem;
  max-width: 30rem;
}

.administration-page__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.administration-page__item {
  padding: 1.25rem;
  background: var(--background-default-grey);
  border: 1px solid var(--border-default-grey);
  border-radius: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.administration-page__item-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.administration-page__item-title {
  font-weight: 600;
}

.administration-page__item-meta {
  margin: 0.25rem 0 0;
  color: var(--text-mention-grey);
}

.administration-page__item-description {
  margin: 0;
  white-space: pre-wrap;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.administration-page__item-response {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.administration-page__item-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.administration-page__pagination {
  display: flex;
  justify-content: center;
}

/* CGU admin */
.cgu-admin__editor {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.cgu-admin__editor-toolbar {
  display: flex;
  gap: 0.5rem;
}

.cgu-admin__preview {
  min-height: 12rem;
  max-height: 24rem;
  overflow-y: auto;
  padding: 1rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 0.375rem;
  background: var(--background-alt-grey);
}

.cgu-admin__editor-actions {
  display: flex;
  gap: 0.5rem;
}

.cgu-admin__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.cgu-admin__item {
  padding: 1rem;
  background: var(--background-default-grey);
  border: 1px solid var(--border-default-grey);
  border-radius: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.cgu-admin__item-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.cgu-admin__item-version {
  font-weight: 600;
}

.cgu-admin__item-status {
  font-size: 0.75rem;
  color: var(--text-mention-grey);
}

.cgu-admin__item-meta {
  margin: 0;
  color: var(--text-mention-grey);
}

.cgu-admin__item-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

/* Stats admin */
.admin-stats__cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
  gap: 1rem;
}

.admin-stats__card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 0.5rem;
  background: var(--background-default-grey);
}

.admin-stats__card-icon {
  font-size: 1.75rem;
  color: var(--text-action-high-blue-france);
}

.admin-stats__card-value {
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1;
}

.admin-stats__card-label {
  font-size: 0.8rem;
  color: var(--text-mention-grey);
  margin-top: 0.25rem;
}

.admin-stats__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
  gap: 1rem;
}

.admin-stats__panel {
  padding: 1.25rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 0.5rem;
  background: var(--background-default-grey);
}

.admin-stats__status-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.admin-stats__status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.admin-stats__status-label {
  color: var(--text-mention-grey);
}

.admin-stats__status-count {
  font-weight: 600;
}

.admin-stats__chart {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
  height: 8rem;
}

.admin-stats__chart-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  flex: 1;
  min-width: 2.5rem;
}

.admin-stats__chart-fill {
  width: 60%;
  min-height: 2px;
  background: var(--background-action-high-blue-france);
  border-radius: 0.25rem 0.25rem 0 0;
  transition: height 0.3s ease;
}

.admin-stats__chart-label {
  font-size: 0.7rem;
  color: var(--text-mention-grey);
}

.admin-stats__chart-value {
  font-size: 0.75rem;
  font-weight: 600;
}

.admin-stats__models {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.admin-stats__model {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.admin-stats__model-rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  background: var(--background-contrast-grey);
  font-size: 0.75rem;
  font-weight: 700;
}

.admin-stats__model-name {
  flex: 1;
  font-family: monospace;
  font-size: 0.85rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.admin-stats__model-count {
  font-weight: 600;
}

/* Tasks admin */
.admin-tasks__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.admin-tasks__workers {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.admin-tasks__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
  gap: 1rem;
}

.admin-tasks__panel {
  padding: 1.25rem;
  border: 1px solid var(--border-default-grey);
  border-radius: 0.5rem;
  background: var(--background-default-grey);
}

.admin-tasks__count {
  color: var(--text-mention-grey);
  font-weight: 400;
}

.admin-tasks__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.admin-tasks__list--scroll {
  max-height: 12rem;
  overflow-y: auto;
}

.admin-tasks__item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 0.25rem;
  background: var(--background-alt-grey);
}

.admin-tasks__item-name {
  font-family: monospace;
  font-size: 0.8rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.admin-tasks__item-worker {
  font-size: 0.75rem;
  color: var(--text-mention-grey);
  white-space: nowrap;
}
</style>
