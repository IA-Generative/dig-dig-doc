/**
 * Composable pour la gestion des tutoriels (V1 statique).
 *
 * Les tutoriels sont des fichiers Markdown servis statiquement depuis
 * /tutorials/*.md. La progression (tutoriels vus) est persistée en
 * localStorage.
 */
import { computed, ref } from "vue";

import { renderMarkdown } from "@/utils/markdown";

export interface Tutorial {
  slug: string;
  title: string;
  icon: string;
  category: string;
  url: string;
}

/** Catalogue statique des tutoriels disponibles. */
const TUTORIALS: Tutorial[] = [
  {
    slug: "01-demarrage",
    title: "Démarrage : créer une analyse et un dossier",
    icon: "ri-rocket-line",
    category: "Premiers pas",
    url: "/tutorials/01-demarrage.md",
  },
  {
    slug: "02-documents",
    title: "Ajouter des documents à un dossier",
    icon: "ri-file-upload-line",
    category: "Premiers pas",
    url: "/tutorials/02-documents.md",
  },
  {
    slug: "03-pipeline",
    title: "Lancer le pipeline d'instruction",
    icon: "ri-flow-chart",
    category: "Analyse",
    url: "/tutorials/03-pipeline.md",
  },
  {
    slug: "04-assistant",
    title: "Utiliser l'assistant conversationnel",
    icon: "ri-chat-3-line",
    category: "Analyse",
    url: "/tutorials/04-assistant.md",
  },
  {
    slug: "05-partage",
    title: "Consulter et partager les résultats",
    icon: "ri-share-line",
    category: "Collaboration",
    url: "/tutorials/05-partage.md",
  },
];

const STORAGE_KEY = "digdigdoc-tutorials-seen";

// État partagé entre toutes les instances du composable.
const tutorials = ref<Tutorial[]>(TUTORIALS);
const seenSlugs = ref<Set<string>>(loadSeen());
const currentSlug = ref<string | null>(null);
const currentHtml = ref("");
const loading = ref(false);
const error = ref("");

function loadSeen(): Set<string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return new Set(JSON.parse(raw) as string[]);
  } catch {
    // localStorage indisponible ou corrompu.
  }
  return new Set();
}

function persistSeen() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...seenSlugs.value]));
  } catch {
    // Ignoré.
  }
}

export function useTutorials() {
  const progress = computed(() => ({
    seen: seenSlugs.value.size,
    total: tutorials.value.length,
  }));

  const progressPercent = computed(() =>
    tutorials.value.length === 0
      ? 0
      : Math.round((seenSlugs.value.size / tutorials.value.length) * 100),
  );

  function isSeen(slug: string): boolean {
    return seenSlugs.value.has(slug);
  }

  function markSeen(slug: string) {
    if (!seenSlugs.value.has(slug)) {
      seenSlugs.value = new Set([...seenSlugs.value, slug]);
      persistSeen();
    }
  }

  function resetProgress() {
    seenSlugs.value = new Set();
    persistSeen();
  }

  async function open(slug: string) {
    const tutorial = tutorials.value.find((t) => t.slug === slug);
    if (!tutorial) return;

    currentSlug.value = slug;
    loading.value = true;
    error.value = "";
    currentHtml.value = "";

    try {
      const res = await fetch(tutorial.url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      currentHtml.value = renderMarkdown(await res.text());
      markSeen(slug);
    } catch {
      error.value =
        "Impossible de charger ce tutoriel. Réessayez plus tard.";
    } finally {
      loading.value = false;
    }
  }

  function close() {
    currentSlug.value = null;
    currentHtml.value = "";
    error.value = "";
  }

  return {
    tutorials,
    currentSlug,
    currentHtml,
    loading,
    error,
    progress,
    progressPercent,
    isSeen,
    markSeen,
    resetProgress,
    open,
    close,
  };
}
