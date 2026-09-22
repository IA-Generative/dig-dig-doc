import { createRouter, createWebHistory } from "vue-router";

import AnalysesPage from "@/pages/AnalysesPage.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: "/", name: "analyses", component: AnalysesPage }],
});
