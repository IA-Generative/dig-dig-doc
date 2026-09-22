<script setup lang="ts">
import { computed, ref } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

import { useAuth } from "@/composables/useAuth";

const route = useRoute();
const { isAuthenticated, userName, login, logout } = useAuth();

const isSidebarCollapsed = ref(false);
const toggleSidebar = () => {
  isSidebarCollapsed.value = !isSidebarCollapsed.value;
};

const navItems = [
  { to: "/", label: "Tableau de bord", icon: "ri-dashboard-line" },
  { to: "/dossiers", label: "Dossiers", icon: "ri-folder-line" },
];

const quickLinks = computed(() =>
  isAuthenticated.value
    ? [
        { label: userName.value, icon: "ri-account-circle-line" },
        { label: "Se déconnecter", icon: "ri-logout-box-r-line", button: true, onClick: logout },
      ]
    : [{ label: "Se connecter", icon: "ri-login-box-line", button: true, onClick: login }],
);
</script>

<template>
  <div class="app-shell">
    <DsfrHeader
      service-title="dig-dig-doc"
      service-description="Instruction assistée des dossiers usagers"
      :quick-links="quickLinks"
      :show-search="false"
    />
    <div class="app-shell__body">
      <aside
        class="app-shell__sidebar"
        :class="{ 'app-shell__sidebar--collapsed': isSidebarCollapsed }"
        aria-label="Navigation principale"
      >
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

        <RouterLink to="/analyses" class="app-shell__new-analysis" :title="isSidebarCollapsed ? 'Analyses' : undefined">
          <VIcon name="ri-add-line" />
          <span class="app-shell__label">Analyses</span>
        </RouterLink>

        <nav class="app-shell__nav">
          <RouterLink
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            class="app-shell__nav-link"
            :class="{ 'app-shell__nav-link--active': route.path === item.to }"
            :title="isSidebarCollapsed ? item.label : undefined"
          >
            <VIcon :name="item.icon" />
            <span class="app-shell__label">{{ item.label }}</span>
          </RouterLink>
        </nav>
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
  gap: 1.5rem;
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

/* ChatGPT-style pill button: full width, rounded, sits above the nav list. */
.app-shell__new-analysis {
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

.app-shell__sidebar--collapsed .app-shell__new-analysis {
  justify-content: center;
  padding: 0.75rem;
}

.app-shell__new-analysis:hover {
  background-color: var(--background-action-low-blue-france-hover);
}

.app-shell__nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.app-shell__nav-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 0.25rem;
  color: var(--text-action-high-blue-france);
  text-decoration: none;
  white-space: nowrap;
}

.app-shell__sidebar--collapsed .app-shell__nav-link {
  justify-content: center;
  padding: 0.75rem;
}

.app-shell__nav-link:hover {
  background-color: var(--background-alt-blue-france-hover);
}

.app-shell__nav-link--active {
  background-color: var(--background-action-selected-blue-france);
  font-weight: bold;
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
