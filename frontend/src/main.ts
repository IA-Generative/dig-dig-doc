import "@gouvfr/dsfr/dist/dsfr.min.css";
import VueDsfr from "@gouvminint/vue-dsfr";
import { createApp } from "vue";

import App from "./App.vue";
import { router } from "./router";

const app = createApp(App);
app.use(router);
app.use(VueDsfr);
app.mount("#app");
