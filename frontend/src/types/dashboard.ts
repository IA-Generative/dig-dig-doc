import type { Recurrence } from "@/types/schedule";

// Tableau de bord utilisateur (issue #174). Partie UI : les données
// proviennent pour l'instant de mocks (voir useDashboard), en attendant
// les statuts (#168), l'échéance (#172) et les affectations (#173).

export type DueLevel = "overdue" | "soon";

export const DUE_LEVEL_LABELS: Record<DueLevel, string> = {
  overdue: "Échéance dépassée",
  soon: "Échéance proche",
};

export interface DashboardUrgency {
  dossierId: string;
  dossierName: string;
  analyseName: string;
  statusLabel: string;
  dueAt: string;
  level: DueLevel;
  /** Créneau de traitement planifié par l'utilisateur (ISO). Les deux ensemble, ou aucun. */
  plannedStart?: string;
  plannedEnd?: string;
  /** Répétition du créneau (absent = une seule fois). */
  recurrence?: Recurrence;
  /** Rappels, en minutes avant chaque occurrence (0 = à l'heure). */
  reminders?: number[];
}

export interface DashboardStatusCount {
  /** Identifiant du statut (configurable par analyse, #168). */
  statusId: string;
  label: string;
  count: number;
}

export interface DashboardUnassigned {
  dossierId: string;
  dossierName: string;
  analyseName: string;
  createdAt: string;
}

export type ActivityKind = "status_changed" | "document_added" | "analysis_done" | "analysis_failed";

export interface DashboardActivity {
  id: string;
  kind: ActivityKind;
  dossierId: string;
  dossierName: string;
  message: string;
  at: string;
}

/** Indicateurs de suivi personnels (calculés côté serveur à terme). */
export interface DashboardStats {
  /** Tous mes dossiers, clos compris. */
  totalDossiers: number;
  /** Mes dossiers clôturés. */
  closedDossiers: number;
  /** Dossiers clôturés cette semaine / la semaine précédente. */
  completedThisWeek: number;
  completedPrevWeek: number;
  /** Dossiers clôturés par semaine, des 4 dernières semaines (la plus ancienne d'abord). */
  weeklyClosed: number[];
  /** Délai moyen, en jours, entre l'arrivée d'un dossier et sa clôture. */
  avgProcessingDays: number;
  /** Part des dossiers clos avant leur échéance, entre 0 et 1. */
  onTimeRate: number;
}

export interface DashboardData {
  stats: DashboardStats;
  urgencies: DashboardUrgency[];
  statusCounts: DashboardStatusCount[];
  /** `null` : l'utilisateur n'a pas le droit de voir les dossiers non affectés. */
  unassigned: DashboardUnassigned[] | null;
  activity: DashboardActivity[];
}

export type NotificationKind =
  | "assigned"
  | "due_soon"
  | "overdue"
  | "status_changed"
  | "analysis_done"
  | "analysis_failed"
  | "reminder";

export type NotificationCategory = "assignment" | "deadline" | "status" | "analysis" | "reminder";

export const NOTIFICATION_CATEGORIES: { value: NotificationCategory; label: string; icon: string }[] = [
  { value: "assignment", label: "Affectations", icon: "ri-user-received-line" },
  { value: "deadline", label: "Échéances", icon: "ri-alarm-warning-line" },
  { value: "status", label: "Statuts", icon: "ri-flag-line" },
  { value: "analysis", label: "Analyses", icon: "ri-checkbox-circle-line" },
  { value: "reminder", label: "Rappels", icon: "ri-notification-badge-line" },
];

const CATEGORY_BY_KIND: Record<NotificationKind, NotificationCategory> = {
  assigned: "assignment",
  due_soon: "deadline",
  overdue: "deadline",
  status_changed: "status",
  analysis_done: "analysis",
  analysis_failed: "analysis",
  reminder: "reminder",
};

export const categoryOf = (kind: NotificationKind): NotificationCategory => CATEGORY_BY_KIND[kind];

export interface AppNotification {
  id: string;
  kind: NotificationKind;
  dossierId: string;
  dossierName: string;
  message: string;
  createdAt: string;
  readAt?: string;
}
