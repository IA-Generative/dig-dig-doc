import { formatDueDate } from "@/utils/due";
import { EVENT_CATEGORIES, type DossierEvent } from "@/types/dossierEvent";

export interface EventDescription {
  icon: string;
  title: string;
  /** Détail en une ligne (ancien → nouveau statut, nom du document…). */
  detail?: string;
}

interface Lookups {
  /** Nom d'un document déposé, à partir de son identifiant (le journal ne contient pas les noms de fichiers). */
  documentName: (documentId: string) => string | undefined;
}

const formatSize = (bytes: number) => (bytes < 1_000_000 ? `${Math.max(1, Math.round(bytes / 1000))} Ko` : `${(bytes / 1_000_000).toFixed(1)} Mo`);

const REASONS: Record<string, string> = {
  status_removed: "statut supprimé et remplacé",
  default_duration: "durée par défaut de l'analyse",
  status_flag_changed: "le statut est devenu final ou ne l'est plus",
};

/** Catégorie d'un type d'événement (« Statuts », « Documents »…), ou undefined pour un type inconnu. */
export function categoryOf(type: string) {
  return EVENT_CATEGORIES.find((c) => c.types.includes(type));
}

/** Titre, icône et détail d'un événement du journal, en français. */
export function describeEvent(event: DossierEvent, lookups: Lookups): EventDescription {
  const p = event.payload;
  const reason = p.reason ? REASONS[p.reason as string] : undefined;

  switch (event.type) {
    case "created":
      return {
        icon: "ri-add-circle-line",
        title: "Dossier créé",
        detail: p.imported ? "Créé avant la mise en place de l'historique" : undefined,
      };
    case "consulted":
      return { icon: "ri-eye-line", title: "Dossier consulté" };
    case "status_changed":
      return {
        icon: "ri-flag-line",
        title: "Statut modifié",
        detail: [p.from?.name ? `${p.from.name} → ${p.to?.name}` : `Statut initial : ${p.to?.name}`, reason].filter(Boolean).join(" · "),
      };
    case "due_date_changed": {
      const from = p.from ? formatDueDate(p.from) : null;
      const to = p.to ? formatDueDate(p.to) : null;
      return {
        icon: "ri-calendar-event-line",
        title: !to ? "Échéance supprimée" : !from ? "Échéance fixée" : "Échéance modifiée",
        detail: [from && to ? `${from} → ${to}` : to ?? from, reason].filter(Boolean).join(" · "),
      };
    }
    case "closed":
      return { icon: "ri-check-double-line", title: "Dossier clôturé", detail: [p.status?.name, reason].filter(Boolean).join(" · ") };
    case "reopened":
      return { icon: "ri-restart-line", title: "Dossier rouvert", detail: [p.status?.name, reason].filter(Boolean).join(" · ") };
    case "analyse_assigned":
      return {
        icon: "ri-link",
        title: p.analyse_name ? `Rattaché à l'analyse « ${p.analyse_name} »` : "Rattaché à une analyse",
      };
    case "document_added": {
      const name = lookups.documentName(p.document_id);
      return {
        icon: "ri-file-add-line",
        title: name ? `Document ajouté : ${name}` : "Document ajouté",
        detail: [p.mimetype, typeof p.size === "number" ? formatSize(p.size) : undefined].filter(Boolean).join(" · "),
      };
    }
    case "analysis_started":
      return { icon: "ri-play-circle-line", title: "Analyse lancée", detail: p.analyse_version ? `Version ${p.analyse_version} de l'analyse` : undefined };
    case "analysis_stopped":
      return { icon: "ri-stop-circle-line", title: "Analyse arrêtée" };
    case "analysis_finished":
      return { icon: "ri-checkbox-circle-line", title: "Analyse terminée" };
    case "analysis_failed":
      return { icon: "ri-error-warning-line", title: "Analyse en échec" };
    case "document_generated":
      return {
        icon: "ri-file-word-2-line",
        title: p.template_name ? `Document généré : ${p.template_name}` : "Document généré",
        detail: [p.version_number ? `Version ${p.version_number}` : undefined, p.incomplete ? "incomplet" : undefined].filter(Boolean).join(" · "),
      };
    case "document_downloaded":
      return { icon: "ri-download-2-line", title: "Document téléchargé", detail: p.format ? String(p.format).toUpperCase() : undefined };
    default:
      // Type ajouté après cette version de l'interface : on l'affiche tel quel plutôt que de le masquer.
      return { icon: "ri-history-line", title: event.type.replace(/_/g, " ") };
  }
}

/** « Aujourd'hui », « Hier » ou la date longue : titre d'un groupe de jour. */
export function dayTitle(iso: string): string {
  const day = new Date(iso);
  const startOf = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const diff = Math.round((startOf(new Date()) - startOf(day)) / 86_400_000);
  if (diff === 0) return "Aujourd'hui";
  if (diff === 1) return "Hier";
  return day.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
}
