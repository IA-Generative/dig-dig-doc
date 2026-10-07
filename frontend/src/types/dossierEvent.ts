// Journal d'événements du dossier (issues #169, #171) : qui a fait quoi, et quand.

export interface DossierEvent {
  id: string;
  /** Type d'événement : voir EVENT_CATEGORIES ; un type inconnu (ajouté plus tard) reste affichable. */
  type: string;
  /** `null` : action du système (fin d'analyse par un worker, historique antérieur au journal). */
  actorId: string | null;
  actorName: string | null;
  createdAt: string;
  /** Valeurs nécessaires à l'affichage ; jamais le contenu du dossier. */
  payload: Record<string, any>;
}

export interface DossierEventActor {
  actorId: string;
  actorName: string | null;
}

export type EventCategory = "creation" | "status" | "analyse" | "documents" | "due" | "consultation";

export const EVENT_CATEGORIES: { value: EventCategory; label: string; icon: string; types: string[] }[] = [
  { value: "creation", label: "Création", icon: "ri-add-circle-line", types: ["created"] },
  { value: "status", label: "Statuts", icon: "ri-flag-line", types: ["status_changed", "closed", "reopened"] },
  {
    value: "analyse",
    label: "Analyse",
    icon: "ri-search-eye-line",
    types: ["analyse_assigned", "analysis_started", "analysis_stopped", "analysis_finished", "analysis_failed"],
  },
  {
    value: "documents",
    label: "Documents",
    icon: "ri-file-text-line",
    types: ["document_added", "document_generated", "document_downloaded"],
  },
  { value: "due", label: "Échéance", icon: "ri-calendar-event-line", types: ["due_date_changed"] },
  { value: "consultation", label: "Consultations", icon: "ri-eye-line", types: ["consulted"] },
];
