import { createRouter, createWebHistory } from "vue-router";

import DashboardPage from "@/pages/DashboardPage.vue";
import DossiersPage from "@/pages/DossiersPage.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "dashboard", component: DashboardPage },
    { path: "/dossiers", name: "dossiers", component: DossiersPage },
  ],
});
