import { computed, ref } from "vue";

import { mockDossierName } from "@/mocks/dossiers";
import type { AppNotification } from "@/types/dashboard";
import type { SlotDraft } from "@/types/schedule";
import { occurrenceStarts } from "@/utils/recurrence";

// MOCK (issue #174, partie UI) : état partagé au niveau du module pour que
// la pastille de la sidebar et le tableau de bord restent synchronisés.
// À remplacer par l'API de notifications (table `notification`, `read_at`).

const hoursAgo = (h: number) => new Date(Date.now() - h * 3_600_000).toISOString();

const notifications = ref<AppNotification[]>([
  {
    id: "n-1",
    kind: "overdue",
    dossierId: "dos-5",
    dossierName: mockDossierName("dos-5"),
    message: "L'échéance du dossier est dépassée.",
    createdAt: hoursAgo(2),
  },
  {
    id: "n-2",
    kind: "assigned",
    dossierId: "dos-9",
    dossierName: mockDossierName("dos-9"),
    message: "Ce dossier vous a été affecté par Camille D.",
    createdAt: hoursAgo(5),
  },
  {
    id: "n-3",
    kind: "analysis_done",
    dossierId: "dos-13",
    dossierName: mockDossierName("dos-13"),
    message: "L'analyse que vous avez lancée est terminée.",
    createdAt: hoursAgo(26),
  },
  {
    id: "n-5",
    kind: "reminder",
    dossierId: "dos-17",
    dossierName: mockDossierName("dos-17"),
    message: "Rappel : créneau de traitement à 09:00.",
    createdAt: hoursAgo(1),
  },
  {
    id: "n-4",
    kind: "status_changed",
    dossierId: "dos-21",
    dossierName: mockDossierName("dos-21"),
    message: "Statut passé à « À valider » par Samir B.",
    createdAt: hoursAgo(50),
    readAt: hoursAgo(40),
  },
]);

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
        notifications.value.unshift(reminder);
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

  function markRead(id: string) {
    const target = notifications.value.find((n) => n.id === id);
    if (target && !target.readAt) target.readAt = new Date().toISOString();
  }

  function markAllRead() {
    const now = new Date().toISOString();
    for (const n of notifications.value) if (!n.readAt) n.readAt = now;
  }

  return { notifications, unreadCount, badgeLabel, markRead, markAllRead,
    setReminders,
    browserPermission,
    browserEnabled,
    enableBrowserNotifications,
    disableBrowserNotifications,
  };
}
