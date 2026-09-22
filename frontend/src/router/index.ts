import { createRouter, createWebHistory } from "vue-router";

import AnalyseDetailPage from "@/pages/AnalyseDetailPage.vue";
import AnalysesPage from "@/pages/AnalysesPage.vue";
import DossierDetailPage from "@/pages/DossierDetailPage.vue";
import DossiersPage from "@/pages/DossiersPage.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "analyses", component: AnalysesPage },
    { path: "/analyses/:id", name: "analyse-detail", component: AnalyseDetailPage },
    { path: "/dossiers", name: "dossiers", component: DossiersPage },
    { path: "/dossiers/:id", name: "dossier-detail", component: DossierDetailPage },
  ],
});
