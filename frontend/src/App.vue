<script setup lang="ts">
import { ref } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

import { useAuth } from "@/composables/useAuth";

const route = useRoute();
const { isAuthenticated, userName, login, logout } = useAuth();

const isSidebarCollapsed = ref(false);
const toggleSidebar = () => {
  isSidebarCollapsed.value = !isSidebarCollapsed.value;
};

const navItems = [
  { to: "/", label: "Analyses", icon: "ri-add-line" },
  { to: "/dossiers", label: "Dossiers", icon: "ri-folder-line" },
];
</script>

<template>
  <div class="app-shell">
    <DsfrHeader
      service-title="dig-dig-doc"
      service-description="Instruction assistée des dossiers usagers"
      :show-search="false"
    />
    <div class="app-shell__body">
      <aside
        class="app-shell__sidebar"
        :class="{ 'app-shell__sidebar--collapsed': isSidebarCollapsed }"
        aria-label="Navigation principale"
      >
        <div class="app-shell__sidebar-top">
          <button
            type="button"
            class="app-shell__collapse-toggle"
            :aria-expanded="!isSidebarCollapsed"
            :title="isSidebarCollapsed ? 'Déployer la navigation' : 'Réduire la navigation'"
            @click="toggleSidebar"
          >
            <VIcon :name="isSidebarCollapsed ? 'ri-menu-unfold-line' : 'ri-menu-fold-line'" />
            <span class="app-shell__collapse-toggle-label">Réduire</span>
          </button>

          <RouterLink
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            class="app-shell__nav-pill"
            :class="{ 'app-shell__nav-pill--active': route.path === item.to }"
            :title="isSidebarCollapsed ? item.label : undefined"
          >
            <VIcon :name="item.icon" />
            <span class="app-shell__label">{{ item.label }}</span>
          </RouterLink>
        </div>

        <!-- Profile / login pinned to the bottom-left, ChatGPT-style. -->
        <button
          type="button"
          class="app-shell__profile"
          :title="isSidebarCollapsed ? (isAuthenticated ? userName : 'Se connecter') : undefined"
          @click="isAuthenticated ? logout() : login()"
        >
          <VIcon :name="isAuthenticated ? 'ri-account-circle-line' : 'ri-login-box-line'" />
          <span class="app-shell__label">{{ isAuthenticated ? userName : "Se connecter" }}</span>
        </button>
      </aside>
      <main class="app-shell__content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-shell__body {
  display: flex;
  flex: 1;
}

.app-shell__sidebar {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  width: 16rem;
  flex-shrink: 0;
  background-color: var(--background-alt-blue-france);
  border-right: 1px solid var(--border-default-grey);
  padding: 1.5rem 1rem;
  transition: width 0.15s ease;
  overflow: hidden;
}

.app-shell__sidebar--collapsed {
  width: 4.5rem;
  padding-left: 0.75rem;
  padding-right: 0.75rem;
}

.app-shell__sidebar-top {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.app-shell__collapse-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: none;
  border: none;
  color: var(--text-action-high-blue-france);
  cursor: pointer;
  padding: 0.5rem;
  align-self: flex-start;
}

.app-shell__sidebar--collapsed .app-shell__collapse-toggle {
  align-self: center;
}

/* ChatGPT-style pill buttons: full width, rounded, stacked at the top. */
.app-shell__nav-pill {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: 1.5rem;
  border: 1px solid var(--border-action-high-blue-france);
  color: var(--text-action-high-blue-france);
  font-weight: bold;
  text-decoration: none;
  transition: background-color 0.15s ease;
  white-space: nowrap;
}

.app-shell__sidebar--collapsed .app-shell__nav-pill {
  justify-content: center;
  padding: 0.75rem;
}

.app-shell__nav-pill:hover {
  background-color: var(--background-action-low-blue-france-hover);
}

.app-shell__nav-pill--active {
  background-color: var(--background-action-selected-blue-france);
}

/* Profile / connexion, pinned bottom-left like ChatGPT's account menu. */
.app-shell__profile {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 0.25rem;
  border: none;
  background: none;
  color: var(--text-action-high-blue-france);
  cursor: pointer;
  text-align: left;
  white-space: nowrap;
}

.app-shell__sidebar--collapsed .app-shell__profile {
  justify-content: center;
}

.app-shell__profile:hover {
  background-color: var(--background-alt-blue-france-hover);
}

.app-shell__sidebar--collapsed .app-shell__label,
.app-shell__sidebar--collapsed .app-shell__collapse-toggle-label {
  display: none;
}

.app-shell__content {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
}
</style>
