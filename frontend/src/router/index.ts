import { createRouter, createWebHistory } from "vue-router";

import AnalysesPage from "@/pages/AnalysesPage.vue";
import DossiersPage from "@/pages/DossiersPage.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "analyses", component: AnalysesPage },
    { path: "/dossiers", name: "dossiers", component: DossiersPage },
  ],
});
