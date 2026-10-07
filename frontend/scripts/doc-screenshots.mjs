// Prend les captures d'écran de la documentation du tableau de bord (#174),
// du tableau de suivi (#173, #186) et de l'accès par groupe (#177), sous
// docs/frontend/<fonctionnalité>/.
//
// Les écrans s'appuient sur des données simulées côté interface ; l'API est
// simulée ici (interception des appels /api/**) pour ne dépendre ni du
// backend ni de Keycloak. Le serveur de dev doit tourner (pnpm dev).
//
// Usage : node scripts/doc-screenshots.mjs [url]   (défaut : http://localhost:5173)
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const baseUrl = process.argv[2] ?? "http://localhost:5173";
const docsRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../../docs/frontend");

const ANALYSE_ID = "an-subv";
const iso = (days) => new Date(Date.now() + days * 86_400_000).toISOString();

const profiles = {
  admin: { user_id: "u1", email: "alex.martin@example.org", first_name: "Alex", last_name: "Martin", roles: ["admin"], is_admin: true, groups: ["/service-culture", "/service-sport"] },
  user: { user_id: "u1", email: "alex.martin@example.org", first_name: "Alex", last_name: "Martin", roles: [], is_admin: false, groups: ["/service-culture", "/service-sport"] },
};

const dossier = (n, name, extra = {}) => ({
  id: `dos-${n}`,
  name,
  analyse_id: ANALYSE_ID,
  analyse_version: "v1",
  created_at: iso(-n),
  status: "terminé",
  started_at: iso(-n),
  ended_at: iso(-n),
  execution_steps: [],
  documents: [],
  summary_status: "terminé",
  summary_error: null,
  summary: null,
  suggestion_status: "terminé",
  suggested_analyses: [],
  ...extra,
});

const dossiers = [
  dossier(3, "Subvention association Les Mouettes n°102"),
  dossier(1, "Convention de partenariat culturelle n°100"),
  dossier(9, "Aide au projet sportif jeunesse n°108"),
];

const page_of = (items) => ({ items, total: items.length, page: 1, page_size: 20, pages: 1 });

function api(role) {
  return (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const method = route.request().method();
    const json = (body, status = 200) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

    if (path === "/api/auth/me") return json(profiles[role]);
    if (path === "/api/cgu/acceptance") return json({ accepted: true, cgu: null });
    if (path === "/api/cgu") return json({}, 404);
    if (path === "/api/analyses") {
      return json(page_of([{ id: ANALYSE_ID, name: "Instruction subventions", description: "Instruction des demandes de subvention des associations.", created_at: iso(-90), agent_count: 2 }]));
    }
    if (path === `/api/analyses/${ANALYSE_ID}`) {
      return json({
        id: ANALYSE_ID,
        name: "Instruction subventions",
        description: "Instruction des demandes de subvention des associations.",
        created_at: iso(-90),
        classification: { prompt: "", prompt_versions: [], labels: [], labels_versions: [] },
        extraction: { prompt: "", prompt_versions: [], entities: [], entities_versions: [] },
        agents: [],
      });
    }
    if (path === "/api/dossiers" && method === "GET") return json(page_of(dossiers));
    const match = path.match(/^\/api\/dossiers\/(dos-\d+)$/);
    if (match) return json(dossiers.find((d) => `dos-${match[1].slice(4)}` === d.id) ?? dossiers[0]);
    if (path === "/api/conversations") return json(page_of([]));
    if (path.startsWith("/api/reports") || path.startsWith("/api/me/tasks")) return json([]);
    if (path === "/api/me/stats") return json({});
    return json(page_of([]));
  };
}

async function newPage(browser, role, viewport = { width: 1280, height: 800 }) {
  const context = await browser.newContext({ viewport, locale: "fr-FR", timezoneId: "Europe/Paris" });
  await context.grantPermissions(["notifications"], { origin: baseUrl });
  const page = await context.newPage();
  await page.route("**/api/**", api(role));
  return page;
}

const out = (dir, file) => {
  const path = resolve(docsRoot, dir, file);
  mkdirSync(dirname(path), { recursive: true });
  return path;
};

const settle = (page, ms = 500) => page.waitForTimeout(ms);

/** Capture de la page entière. */
async function shot(page, dir, file) {
  await settle(page);
  await page.screenshot({ path: out(dir, file), fullPage: true });
  console.log(`✓ ${dir}/${file}`);
}

/** Capture d'une fenêtre (modale) ouverte. */
async function shotModal(page, dir, file) {
  await settle(page, 600);
  await page.locator(".fr-modal--opened .fr-modal__body").first().screenshot({ path: out(dir, file) });
  console.log(`✓ ${dir}/${file}`);
}

async function closeModal(page) {
  await page.keyboard.press("Escape");
  await settle(page, 300);
}

/** Ouvre le menu « Options » du tableau de suivi s'il est fermé. */
async function openOptions(page) {
  const open = await page.locator("details.track__more").evaluate((el) => el.open);
  if (!open) await page.getByText("Options").click();
}

async function waitDashboard(page) {
  await page.goto(`${baseUrl}/dashboard`, { waitUntil: "networkidle" });
  await page.getByText("Mon agenda").waitFor();
  await settle(page, 600);
}

// ---------------------------------------------------------------------------
// Tableau de bord
// ---------------------------------------------------------------------------
async function dashboard(browser) {
  const dir = "tableau-de-bord";
  const page = await newPage(browser, "admin", { width: 1280, height: 2000 });
  await waitDashboard(page);

  await shot(page, dir, "01-tableau-de-bord.png");

  await page.getByRole("button", { name: "Mois", exact: true }).click();
  await shot(page, dir, "02-calendrier-du-mois.png");

  await page.getByRole("button", { name: "Liste", exact: true }).click();
  await shot(page, dir, "03-liste-des-urgences.png");

  await page.getByRole("button", { name: /Rechercher/ }).click();
  await shot(page, dir, "04-recherche-et-filtres.png");
  await page.getByRole("button", { name: /Rechercher/ }).click();

  // Planification d'un créneau
  await page.getByRole("button", { name: "Jour", exact: true }).click();
  await settle(page);
  await page.locator(".cal__block").first().click();
  await shotModal(page, dir, "05-planifier-un-creneau.png");

  await page.locator("#slot-repeat-select").selectOption("custom");
  await page.getByRole("button", { name: "Ajouter un rappel" }).click();
  await page.locator("select[id^='slot-rem-']").last().selectOption("custom");
  await shotModal(page, dir, "06-repetition-et-rappels-personnalises.png");
  await closeModal(page);

  // Indicateurs
  await page.getByRole("button", { name: /Dossiers/ }).first().click();
  await shotModal(page, dir, "07-indicateurs.png");
  await closeModal(page);

  // Notifications
  await page.getByRole("button", { name: /^Notifications/ }).click();
  await shotModal(page, dir, "08-notifications.png");
  await closeModal(page);

  // Non affectés et activité
  await page.getByRole("button", { name: /Dossiers à prendre en charge/ }).click();
  await shotModal(page, dir, "09-dossiers-a-prendre-en-charge.png");
  await closeModal(page);

  await page.getByRole("button", { name: "Activité récente" }).click();
  await shotModal(page, dir, "10-activite-recente.png");

  await page.context().close();
}

// ---------------------------------------------------------------------------
// Tableau de suivi
// ---------------------------------------------------------------------------
async function tracking(browser) {
  const dir = "tableau-de-suivi";
  const page = await newPage(browser, "admin", { width: 1800, height: 1900 });
  await page.goto(`${baseUrl}/analyses/${ANALYSE_ID}/suivi`, { waitUntil: "networkidle" });
  await page.getByText(/\d+ dossiers?/).first().waitFor();
  await settle(page, 700);
  await shot(page, dir, "01-onglet-suivi.png");

  await page.getByRole("button", { name: /Filtres/ }).click();
  await shot(page, dir, "02-filtres.png");
  await page.getByRole("button", { name: /Filtres/ }).click();

  // Sélection et affectation en lot
  const boxes = page.locator("tbody input[type=checkbox]");
  await boxes.nth(0).check();
  await boxes.nth(1).check();
  await shot(page, dir, "03-affectation-en-lot.png");
  await page.getByRole("button", { name: "Tout désélectionner" }).click();

  // Aide d'une colonne
  await page.getByRole("button", { name: "Aide sur la colonne Échéance" }).click();
  await shot(page, dir, "04-definition-d-une-colonne.png");
  await page.keyboard.press("Escape");

  // Menu Options + Colonnes
  await openOptions(page);
  await shot(page, dir, "05-menu-options.png");
  await page.getByRole("button", { name: /Colonnes/ }).first().click();
  await shotModal(page, dir, "06-choix-des-colonnes.png");
  await closeModal(page);

  // Champs personnalisés, puis historique après une modification
  await openOptions(page);
  await page.getByRole("button", { name: /Champs personnalisés/ }).click();
  await page.locator(".cf__head").first().click();
  await shotModal(page, dir, "07-champs-personnalises.png");
  await page.locator("input[id^='cf-name-']").first().fill("Montant sollicité");
  await page.getByRole("button", { name: "Enregistrer", exact: true }).click();
  await settle(page, 400);
  await openOptions(page);
  await page.getByRole("button", { name: /Champs personnalisés/ }).click();
  await page.getByText(/Historique des versions/).click();
  await shotModal(page, dir, "08-historique-des-champs.png");
  await closeModal(page);

  // Édition en cellule avec erreur de validation (montant négatif)
  if (await page.locator("details.track__more").evaluate((el) => el.open)) await page.getByText("Options").click();
  await page.getByRole("button", { name: /^Modifier Montant sollicité/ }).first().click();
  await page.locator("tbody input.cell__input").first().fill("-5");
  await page.keyboard.press("Enter");
  await shot(page, dir, "09-edition-en-cellule.png");

  // Vue transversale
  await page.goto(`${baseUrl}/suivi`, { waitUntil: "networkidle" });
  await page.getByText(/\d+ dossiers?/).first().waitFor();
  await settle(page, 700);
  await shot(page, dir, "10-vue-transversale.png");

  await page.getByRole("button", { name: /Filtres/ }).click();
  await page.getByLabel("Instruction subventions").check();
  await shot(page, dir, "11-vue-transversale-une-analyse.png");

  await page.context().close();
}

// ---------------------------------------------------------------------------
// Accès aux dossiers par groupe
// ---------------------------------------------------------------------------
async function access(browser) {
  const dir = "acces-aux-dossiers";
  let page = await newPage(browser, "admin", { width: 1280, height: 1700 });

  await page.goto(`${baseUrl}/dossiers`, { waitUntil: "networkidle" });
  await page.getByText("Subvention association Les Mouettes").first().waitFor();
  await shot(page, dir, "01-pastille-restreint.png");

  await page.getByRole("button", { name: "Créer un dossier" }).click();
  await shotModal(page, dir, "02-creation-d-un-dossier-restreint.png");
  await closeModal(page);

  await page.goto(`${baseUrl}/dossiers/dos-3`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Accès au dossier" }).click();
  await shotModal(page, dir, "03-acces-au-dossier.png");

  // Retrait d'un groupe : confirmation des pertes d'accès
  await page.getByLabel("Service culture").uncheck();
  await page.getByLabel("Service sport").check();
  await shotModal(page, dir, "04-confirmation-des-pertes-d-acces.png");
  await closeModal(page);

  // Suivi : filtre Accès et définition en lot
  await page.goto(`${baseUrl}/suivi`, { waitUntil: "networkidle" });
  await page.getByText(/\d+ dossiers?/).first().waitFor();
  await page.getByRole("button", { name: "Tous", exact: true }).click();
  await settle(page);
  await page.getByRole("button", { name: /Filtres/ }).click();
  await page.locator("#tf-access").selectOption("restricted");
  await shot(page, dir, "05-suivi-dossiers-restreints.png");
  await page.locator("#tf-access").selectOption("");
  await page.locator("tbody input[type=checkbox]").nth(0).check();
  await page.locator("tbody input[type=checkbox]").nth(1).check();
  await page.getByRole("button", { name: "Définir l'accès" }).click();
  await shotModal(page, dir, "06-definir-l-acces-en-lot.png");
  await page.context().close();

  // Notification d'un dossier dont l'accès a été retiré
  page = await newPage(browser, "admin", { width: 1280, height: 1000 });
  await waitDashboard(page);
  await page.getByRole("button", { name: /^Notifications/ }).click();
  await shotModal(page, dir, "07-notification-d-un-dossier-non-accessible.png");
  await page.context().close();

  // Lecture seule pour un non-administrateur
  page = await newPage(browser, "user", { width: 1280, height: 1000 });
  await page.goto(`${baseUrl}/dossiers/dos-3`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Accès au dossier" }).click();
  await shotModal(page, dir, "08-lecture-seule-pour-un-non-administrateur.png");
  await page.context().close();
}

const browser = await chromium.launch();
try {
  await dashboard(browser);
  await tracking(browser);
  await access(browser);
} finally {
  await browser.close();
}
