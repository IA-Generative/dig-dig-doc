import { computed, ref } from "vue";

import type { AppNotification } from "@/types/dashboard";
import type { SlotDraft } from "@/types/schedule";
import { apiFetch } from "@/utils/api";
import { occurrenceStarts } from "@/utils/recurrence";

// Notifications (issue #174) : les notifications d'affectation, d'échéance, de statut et d'analyse viennent de
// l'API (`GET /api/notifications`, interrogée toutes les 60 s tant que la page est visible : chaque lecture met
// à jour les notifications côté serveur). Les rappels de créneau restent déclenchés localement par le navigateur.
// État partagé au niveau du module pour que la pastille de la barre latérale et le tableau de bord restent
// synchronisés.

const POLL_MS = 60_000;

/** Notifications du serveur, de la plus récente à la plus ancienne. */
const serverNotifications = ref<AppNotification[]>([]);
/** Rappels de créneau déclenchés dans ce navigateur (pas encore côté serveur). */
const localReminders = ref<AppNotification[]>([]);
const notifications = computed(() =>
  [...localReminders.value, ...serverNotifications.value].sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt)),
);

/** Identifiants déjà vus : seules les nouvelles notifications déclenchent une alerte du navigateur. */
const knownIds = new Set<string>();
let firstLoad = true;
let pollTimer: ReturnType<typeof setInterval> | undefined;

function mapNotification(api: any): AppNotification {
  return {
    id: api.id,
    kind: api.kind,
    dossierId: api.dossier_id,
    dossierName: api.dossier_name,
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
  const alert = new Notification(n.dossierName, { body: n.message, tag: n.id, icon: "/marianne-icone.png" });
  alert.onclick = () => {
    window.focus();
    window.location.assign(`/dossiers/${n.dossierId}`);
    alert.close();
  };
}

// --- Rappels (MOCK) -------------------------------------------------------
// Chaque rappel d'un créneau (y compris récurrent) génère une notification
// « reminder » à l'heure voulue. Ici le déclenchement est local (minuteur
// dans le navigateur) ; côté serveur ce sera une tâche planifiée du worker,
// comme les seuils d'échéance.
interface RegisteredSlot {
  dossierId: string;
  dossierName: string;
  slot: SlotDraft;
  registeredAt: number;
}
const registered = new Map<string, RegisteredSlot>();
/** Rappels déjà émis (dossier|début d'occurrence|décalage) : un rappel ne part qu'une fois. */
const fired = new Set<string>();
let timer: ReturnType<typeof setInterval> | undefined;

const DAY_MS = 86_400_000;

function fireDueReminders() {
  const now = Date.now();
  for (const { dossierId, dossierName, slot, registeredAt } of registered.values()) {
    const maxOffset = Math.max(0, ...slot.reminders);
    // Occurrences dont au moins un rappel peut tomber maintenant.
    const occurrences = occurrenceStarts(
      new Date(slot.start),
      slot.recurrence,
      new Date(now - DAY_MS),
      new Date(now + maxOffset * 60_000 + DAY_MS),
    );
    for (const occ of occurrences) {
      for (const minutes of slot.reminders) {
        const fireAt = occ.getTime() - minutes * 60_000;
        const key = `${dossierId}|${occ.toISOString()}|${minutes}`;
        // Pas de rappel pour un instant antérieur à l'enregistrement du créneau.
        if (fireAt > now || fireAt <= registeredAt || fired.has(key)) continue;
        fired.add(key);
        const time = occ.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
        const reminder: AppNotification = {
          id: `rem-${key}`,
          kind: "reminder",
          dossierId,
          dossierName,
          message: `Rappel : créneau de traitement à ${time}.`,
          createdAt: new Date().toISOString(),
        };
        localReminders.value.unshift(reminder);
        showBrowserNotification(reminder);
      }
    }
  }
}

/** Enregistre (ou retire, avec `null`) les rappels du créneau d'un dossier. */
function setReminders(dossierId: string, dossierName: string, slot: SlotDraft | null) {
  if (!slot || slot.reminders.length === 0) {
    registered.delete(dossierId);
  } else {
    registered.set(dossierId, { dossierId, dossierName, slot, registeredAt: Date.now() });
    timer ??= setInterval(fireDueReminders, 10_000);
  }
}

export function useNotifications() {
  const unreadCount = computed(() => notifications.value.filter((n) => !n.readAt).length);
  /** Libellé de la pastille, plafonné à « 99+ ». */
  const badgeLabel = computed(() => (unreadCount.value > 99 ? "99+" : String(unreadCount.value)));

  /** Marque une notification comme lue (tout de suite à l'écran, puis côté serveur). */
  function markRead(id: string) {
    const now = new Date().toISOString();
    const local = localReminders.value.find((n) => n.id === id);
    if (local) {
      if (!local.readAt) local.readAt = now;
      return;
    }
    const target = serverNotifications.value.find((n) => n.id === id);
    if (!target || target.readAt) return;
    target.readAt = now;
    apiFetch<void>(`/api/notifications/${id}/read`, { method: "POST" }).catch(() => {
      target.readAt = undefined; // l'enregistrement a échoué : elle redevient non lue
    });
  }

  function markAllRead() {
    const now = new Date().toISOString();
    for (const n of localReminders.value) if (!n.readAt) n.readAt = now;
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
    setReminders,
    browserPermission,
    browserEnabled,
    enableBrowserNotifications,
    disableBrowserNotifications,
  };
}
