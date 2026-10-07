import { computed, ref } from "vue";

import type { AppNotification } from "@/types/dashboard";
import { apiFetch } from "@/utils/api";

// Notifications (issue #174) : les notifications d'affectation, d'échéance, de statut et d'analyse viennent de
// l'API (`GET /api/notifications`, interrogée toutes les 60 s tant que la page est visible : chaque lecture met
// à jour les notifications côté serveur, rappels de créneau compris, #219).
// État partagé au niveau du module pour que la pastille de la barre latérale et le tableau de bord restent
// synchronisés.

const POLL_MS = 60_000;

/** Notifications du serveur, de la plus récente à la plus ancienne. */
const serverNotifications = ref<AppNotification[]>([]);
const notifications = computed(() => serverNotifications.value);

/** Identifiants déjà vus : seules les nouvelles notifications déclenchent une alerte du navigateur. */
const knownIds = new Set<string>();
let firstLoad = true;
let pollTimer: ReturnType<typeof setInterval> | undefined;

function mapNotification(api: any): AppNotification {
  return {
    id: api.id,
    kind: api.kind,
    dossierId: api.dossier_id ?? null,
    dossierName: api.dossier_name ?? null,
    accessible: api.accessible !== false,
    message: api.message,
    createdAt: api.created_at,
    readAt: api.read_at ?? undefined,
  };
}

async function fetchNotifications() {
  try {
    const items = (await apiFetch<any[]>("/api/notifications?limit=100")).map(mapNotification);
    for (const n of items) {
      if (!knownIds.has(n.id) && !firstLoad && !n.readAt) showBrowserNotification(n);
      knownIds.add(n.id);
    }
    firstLoad = false;
    serverNotifications.value = items;
  } catch {
    // Hors ligne ou session expirée : on garde l'état précédent et on réessaiera au prochain passage.
  }
}

/** Démarre l'interrogation périodique (idempotent) : à appeler quand la personne est connectée. */
function startPolling() {
  if (pollTimer) return;
  fetchNotifications();
  pollTimer = setInterval(() => {
    if (document.visibilityState === "visible") fetchNotifications();
  }, POLL_MS);
}

function stopPolling() {
  clearInterval(pollTimer);
  pollTimer = undefined;
  serverNotifications.value = [];
  knownIds.clear();
  firstLoad = true;
}

// --- Notifications du navigateur --------------------------------------------
// API Notification : l'alerte système s'affiche tant que l'application est
// ouverte dans un onglet (même en arrière-plan). Pour être notifié application
// fermée, il faudra Web Push (service worker + clés VAPID côté serveur).
const BROWSER_KEY = "digdigdoc-browser-notifications";
const supported = typeof window !== "undefined" && "Notification" in window;

const browserPermission = ref<NotificationPermission | "unsupported">(supported ? Notification.permission : "unsupported");
const browserEnabled = ref(false);
try {
  browserEnabled.value = supported && Notification.permission === "granted" && localStorage.getItem(BROWSER_KEY) === "true";
} catch {
  // Stockage bloqué : l'option reste désactivée au rechargement.
}

function persistBrowserEnabled(value: boolean) {
  browserEnabled.value = value;
  try {
    localStorage.setItem(BROWSER_KEY, String(value));
  } catch {
    // Ignoré : la préférence ne survivra pas au rechargement.
  }
}

/** Active les alertes du navigateur (doit être appelé suite à un clic : le navigateur demande l'autorisation). */
async function enableBrowserNotifications() {
  if (!supported) return;
  if (Notification.permission === "default") browserPermission.value = await Notification.requestPermission();
  else browserPermission.value = Notification.permission;
  persistBrowserEnabled(browserPermission.value === "granted");
}

function disableBrowserNotifications() {
  persistBrowserEnabled(false);
}

function showBrowserNotification(n: AppNotification) {
  if (!supported || !browserEnabled.value || Notification.permission !== "granted") return;
  const alert = new Notification(n.dossierName ?? "Dossier non accessible", {
    body: n.message,
    tag: n.id,
    icon: "/marianne-icone.png",
  });
  alert.onclick = () => {
    window.focus();
    if (n.dossierId) window.location.assign(`/dossiers/${n.dossierId}`);
    alert.close();
  };
}

export function useNotifications() {
  const unreadCount = computed(() => notifications.value.filter((n) => !n.readAt).length);
  /** Libellé de la pastille, plafonné à « 99+ ». */
  const badgeLabel = computed(() => (unreadCount.value > 99 ? "99+" : String(unreadCount.value)));

  /** Marque une notification comme lue (tout de suite à l'écran, puis côté serveur). */
  function markRead(id: string) {
    const now = new Date().toISOString();
    const target = serverNotifications.value.find((n) => n.id === id);
    if (!target || target.readAt) return;
    target.readAt = now;
    apiFetch<void>(`/api/notifications/${id}/read`, { method: "POST" }).catch(() => {
      target.readAt = undefined; // l'enregistrement a échoué : elle redevient non lue
    });
  }

  function markAllRead() {
    const now = new Date().toISOString();
    const pending = serverNotifications.value.filter((n) => !n.readAt);
    for (const n of pending) n.readAt = now;
    if (pending.length) {
      apiFetch("/api/notifications/read-all", { method: "POST" }).catch(() => {
        for (const n of pending) n.readAt = undefined;
      });
    }
  }

  return {
    notifications,
    unreadCount,
    badgeLabel,
    markRead,
    markAllRead,
    startPolling,
    stopPolling,
    refresh: fetchNotifications,
    browserPermission,
    browserEnabled,
    enableBrowserNotifications,
    disableBrowserNotifications,
  };
}
