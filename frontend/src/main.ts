import "@gouvfr/dsfr/dist/dsfr.min.css";
// Comportements interactifs du DSFR (onglets, accordéons, modales...), pas
// seulement le CSS - sans lui, les panneaux d'onglets inactifs restent visibles.
import "@gouvfr/dsfr/dist/dsfr.module.min.js";
import VueDsfr from "@gouvminint/vue-dsfr";
import { createApp } from "vue";

import App from "./App.vue";
import { router } from "./router";

const app = createApp(App);
app.use(router);
app.use(VueDsfr);
app.mount("#app");
