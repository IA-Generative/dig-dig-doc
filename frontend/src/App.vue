<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from "vue-router";

const route = useRoute();

const navItems = [
  { to: "/", label: "Tableau de bord" },
  { to: "/dossiers", label: "Dossiers" },
];
</script>

<template>
  <div class="app-shell">
    <aside class="app-shell__sidebar" aria-label="Navigation principale">
      <div class="app-shell__brand">
        <p class="fr-logo">
          République
          <br />Française
        </p>
        <p class="app-shell__title">dig-dig-doc</p>
      </div>
      <nav class="app-shell__nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="app-shell__nav-link"
          :class="{ 'app-shell__nav-link--active': route.path === item.to }"
        >
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>
    <main class="app-shell__content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
}

.app-shell__sidebar {
  display: flex;
  flex-direction: column;
  width: 16rem;
  flex-shrink: 0;
  background-color: var(--background-alt-blue-france);
  border-right: 1px solid var(--border-default-grey);
  padding: 1.5rem 1rem;
}

.app-shell__brand {
  margin-bottom: 2rem;
}

.app-shell__title {
  margin-top: 0.75rem;
  font-weight: bold;
  font-size: 1.125rem;
}

.app-shell__nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.app-shell__nav-link {
  padding: 0.75rem 1rem;
  border-radius: 0.25rem;
  color: var(--text-action-high-blue-france);
  text-decoration: none;
}

.app-shell__nav-link:hover {
  background-color: var(--background-alt-blue-france-hover);
}

.app-shell__nav-link--active {
  background-color: var(--background-action-selected-blue-france);
  font-weight: bold;
}

.app-shell__content {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
}
</style>
