<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

import UserMenu from "@/components/UserMenu.vue";
import CguGate from "@/components/CguGate.vue";
import TaskDrawer from "@/components/TaskDrawer.vue";
import { useAuth } from "@/composables/useAuth";
import { useMyConversations } from "@/composables/useMyConversations";
import { useUserTasks } from "@/composables/useUserTasks";

const route = useRoute();
const { fetchProfile } = useAuth();
const { list: conversations, fetchList: fetchConversations, deleteConversation } = useMyConversations();
const { hasActiveTasks, activeCount } = useUserTasks();

// Drawer des tâches (issue #62)
const showTaskDrawer = ref(false);

async function onDeleteConversation(dossierId: string, conversationId: string) {
  if (!confirm("Supprimer cette conversation ? Le dossier et ses documents ne seront pas affectés.")) return;
  await deleteConversation(dossierId, conversationId);
}

// Au démarrage de l'app, on vérifie si une session est déjà active (cookie
// HttpOnly). Le route guard attend que `loading` passe à false avant de
// décider de rediriger vers la page d'accueil.
onMounted(() => fetchProfile());
onMounted(fetchConversations);
// La conversation active peut changer de position (activité la plus
// récente en tête) ou apparaître pour la première fois : on rafraîchit à
// chaque navigation vers un dossier plutôt que de dépendre d'un event bus.
watch(
  () => route.params.id,
  () => {
    if (route.name === "dossier-detail") fetchConversations();
  },
);

function formatRelativeTime(iso: string) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(diffMs / 60_000);
  if (minutes < 1) return "à l'instant";
  if (minutes < 60) return `il y a ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `il y a ${hours} h`;
  const days = Math.round(hours / 24);
  return `il y a ${days} j`;
}

// La page d'accueil (/welcome) s'affiche en plein écran, sans sidebar.
const showShell = computed(() => !route.meta.public);

// État réduit/étendu de la sidebar, persisté en localStorage comme Muffin.
const COLLAPSE_STORAGE_KEY = "digdigdoc-sidebar-collapsed";
const isSidebarCollapsed = ref(false);
try {
  isSidebarCollapsed.value = localStorage.getItem(COLLAPSE_STORAGE_KEY) === "true";
} catch {
  // Navigation privée / storage bloqué — défaut étendu.
}
watch(isSidebarCollapsed, (value) => {
  try {
    localStorage.setItem(COLLAPSE_STORAGE_KEY, String(value));
  } catch {
    // Ignoré — au pire la préférence ne survit pas à un rechargement.
  }
});

const navItems = [
  { to: "/analyses", label: "Analyses", icon: "ri-file-list-3-line" },
  { to: "/dossiers", label: "Dossiers", icon: "ri-folder-line" },
];
</script>

<template>
  <!-- Portail CGU : bloque l'app tant que l'utilisateur n'a pas accepté les CGU -->
  <CguGate />

  <!-- Page d'accueil : plein écran, sans sidebar -->
  <RouterView v-if="!showShell" />

  <!-- Application (connecté) : sidebar façon Muffin + contenu -->
  <div v-else class="app-shell">
    <aside class="app-sidebar" :class="{ 'app-sidebar--collapsed': isSidebarCollapsed }">
      <!-- Brand : logo Marianne officiel DSFR + bouton collapse -->
      <div
        class="app-sidebar__brand"
        title="Creuser dans vos dossiers pour trouver de la valeur"
      >
        <div class="app-sidebar__logo">
          <DsfrLogo v-if="!isSidebarCollapsed" small logo-text="dig-dig-doc" />
          <img v-else class="app-sidebar__logo-marianne" src="/marianne-icone.png" alt="Logo Marianne" />
        </div>
        <button
          type="button"
          class="app-sidebar__collapse-toggle"
          :aria-label="isSidebarCollapsed ? 'Ouvrir la barre latérale' : 'Réduire la barre latérale'"
          @click="isSidebarCollapsed = !isSidebarCollapsed"
        >
          <VIcon :name="isSidebarCollapsed ? 'ri-menu-unfold-line' : 'ri-menu-fold-line'" />
        </button>
      </div>

      <!-- Navigation principale -->
      <nav class="app-sidebar__nav" aria-label="Navigation principale">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="app-sidebar__nav-item"
          :class="{ 'app-sidebar__nav-item--active': route.path.startsWith(item.to) }"
          :title="isSidebarCollapsed ? item.label : undefined"
        >
          <VIcon :name="item.icon" />
          <span v-if="!isSidebarCollapsed">{{ item.label }}</span>
        </RouterLink>
      </nav>

      <!-- Conversations (une par dossier ouvert), façon ChatGPT -->
      <div v-if="!isSidebarCollapsed" class="app-sidebar__conversations">
        <p class="app-sidebar__section-title">Conversations</p>
        <p v-if="conversations.length === 0" class="app-sidebar__empty">
          Ouvrez un dossier pour démarrer une conversation.
        </p>
        <nav v-else class="app-sidebar__nav" aria-label="Mes conversations">
          <RouterLink
            v-for="item in conversations"
            :key="item.id"
            :to="`/dossiers/${item.dossierId}`"
            class="app-sidebar__nav-item app-sidebar__conversation-item"
            :class="{ 'app-sidebar__nav-item--active': route.params.id === item.dossierId }"
          >
            <VIcon name="ri-chat-3-line" />
            <span class="app-sidebar__conversation-text">
              <span class="app-sidebar__conversation-title">{{ item.dossierName }}</span>
              <span class="app-sidebar__conversation-preview">
                {{ item.lastMessagePreview ?? "Aucun message pour l'instant" }}
              </span>
            </span>
            <span class="app-sidebar__conversation-time">{{ formatRelativeTime(item.lastActivityAt) }}</span>
            <button
              type="button"
              class="app-sidebar__conversation-delete"
              aria-label="Supprimer cette conversation"
              title="Supprimer cette conversation"
              @click.stop.prevent="onDeleteConversation(item.dossierId, item.id)"
            >
              <VIcon name="ri-delete-bin-line" />
            </button>
          </RouterLink>
        </nav>
      </div>
      <div v-else class="app-sidebar__spacer" />

      <!-- Menu utilisateur en bas (façon Muffin) -->
      <UserMenu :collapsed="isSidebarCollapsed" />
    </aside>

    <main class="app-shell__content">
      <RouterView />
    </main>

    <!-- Bouton flottant d'accès aux tâches (issue #62) -->
    <button
      v-if="showShell"
      type="button"
      class="app-shell__task-button"
      :class="{ 'app-shell__task-button--active': hasActiveTasks }"
      :aria-label="hasActiveTasks ? `${activeCount} tâche(s) en cours` : 'Tâches'"
      title="Tâches en cours"
      @click="showTaskDrawer = true"
    >
      <VIcon name="ri-task-line" />
      <span v-if="hasActiveTasks" class="app-shell__task-badge">{{ activeCount }}</span>
    </button>

    <!-- Drawer des tâches -->
    <TaskDrawer :open="showTaskDrawer" @close="showTaskDrawer = false" />
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
}

/* Sidebar façon Muffin */
.app-sidebar {
  display: flex;
  flex-direction: column;
  width: 260px;
  flex-shrink: 0;
  height: 100vh;
  position: sticky;
  top: 0;
  padding: 0.75rem;
  background: var(--background-alt-grey);
  color: var(--text-default-grey);
  border-right: 1px solid var(--border-default-grey);
  box-sizing: border-box;
  transition: width 0.15s ease;
  overflow: hidden;
}

.app-sidebar--collapsed {
  width: 4.5rem;
}

/* Brand : logo + bouton collapse */
.app-sidebar__brand {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem 1rem;
}

.app-sidebar__logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text-default-grey);
  margin: 0;
  min-width: 0;
  overflow: hidden;
}

.app-sidebar__logo-marianne {
  width: 2rem;
  height: 2rem;
  object-fit: contain;
}

.app-sidebar--collapsed .app-sidebar__logo {
  flex-direction: column;
  gap: 0.25rem;
}

.app-sidebar__collapse-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 1.75rem;
  height: 1.75rem;
  padding: 0;
  border: none;
  border-radius: 0.375rem;
  background: transparent;
  color: var(--text-mention-grey);
  cursor: pointer;
  font-size: 1.125rem;
}

.app-sidebar__collapse-toggle:hover {
  background: var(--background-alt-grey-hover);
  color: var(--text-default-grey);
}

/* Navigation */
.app-sidebar__nav {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border-default-grey);
}

.app-sidebar__nav-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
  text-align: left;
  padding: 0.625rem 0.75rem;
  border-radius: 0.5rem;
  border: none;
  background: transparent;
  color: var(--text-default-grey);
  cursor: pointer;
  font-size: 0.875rem;
  font-family: inherit;
  text-decoration: none;
  transition: background-color 0.15s ease;
}

.app-sidebar__nav-item:hover {
  background: var(--background-alt-grey-hover);
}

.app-sidebar__nav-item--active {
  background: var(--background-action-low-blue-france);
  color: var(--text-active-blue-france);
  font-weight: 600;
}

.app-sidebar--collapsed .app-sidebar__nav-item {
  justify-content: center;
}

/* Espace flexible au milieu (sidebar réduite : pas de liste affichée) */
.app-sidebar__spacer {
  flex: 1;
}

/* Conversations (une par dossier ouvert), façon ChatGPT */
.app-sidebar__conversations {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding-top: 0.75rem;
  overflow: hidden;
}

.app-sidebar__section-title {
  margin: 0 0 0.375rem;
  padding: 0 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: var(--text-mention-grey);
  flex-shrink: 0;
}

.app-sidebar__empty {
  margin: 0;
  padding: 0 0.75rem;
  font-size: 0.8125rem;
  color: var(--text-mention-grey);
}

.app-sidebar__conversations .app-sidebar__nav {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  border-bottom: none;
  padding-bottom: 0;
}

.app-sidebar__conversation-item {
  align-items: flex-start;
  gap: 0.5rem;
}

.app-sidebar__conversation-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.app-sidebar__conversation-title {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-sidebar__conversation-preview {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.75rem;
  color: var(--text-mention-grey);
}

.app-sidebar__conversation-time {
  flex-shrink: 0;
  font-size: 0.6875rem;
  color: var(--text-mention-grey);
  white-space: nowrap;
}

.app-sidebar__conversation-delete {
  flex-shrink: 0;
  display: none;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  padding: 0;
  border: none;
  border-radius: 0.375rem;
  background: transparent;
  color: var(--text-mention-grey);
  cursor: pointer;
}

.app-sidebar__conversation-item:hover .app-sidebar__conversation-delete {
  display: flex;
}

.app-sidebar__conversation-delete:hover {
  background: var(--background-alt-grey-hover);
  color: var(--text-default-grey);
}

/* Contenu principal */
.app-shell__content {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
}

/* Bouton flottant d'accès aux tâches (issue #62) */
.app-shell__task-button {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border: none;
  border-radius: 50%;
  background: var(--background-action-high-blue-france);
  color: var(--text-inverted-blue-france);
  font-size: 1.25rem;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  z-index: 900;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.app-shell__task-button:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.25);
}

.app-shell__task-button--active {
  animation: task-button-pulse 2s ease-in-out infinite;
}

@keyframes task-button-pulse {
  0%, 100% { box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2); }
  50% { box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2), 0 0 0 6px rgba(0, 0, 145, 0.15); }
}

.app-shell__task-badge {
  position: absolute;
  top: -0.25rem;
  right: -0.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 1.25rem;
  height: 1.25rem;
  padding: 0 0.375rem;
  border-radius: 0.625rem;
  background: var(--background-action-high-red-marianne);
  color: var(--text-inverted-red-marianne);
  font-size: 0.75rem;
  font-weight: 700;
  border: 2px solid var(--background-default-grey);
}
</style>
