import type { DueInfo } from "@/types/dossier";

// Tableau de suivi des dossiers d'une analyse (issue #173).
// La liste vient de l'API (useTrackingApi). Les colonnes personnalisées, les vues et l'accès par groupe
// restent simulés (useTracking) tant que leur backend n'existe pas.

export type FieldType = "text" | "number" | "amount" | "date" | "boolean" | "choice";

export const FIELD_TYPE_LABELS: Record<FieldType, string> = {
  text: "Texte",
  number: "Nombre",
  amount: "Montant",
  date: "Date",
  boolean: "Oui / Non",
  choice: "Liste de choix",
};

export type CustomValue = string | number | boolean | null;

/** Colonne personnalisée définie par l'administrateur de l'analyse. */
export interface CustomField {
  id: string;
  name: string;
  /** Définition du champ (comme celle d'un label ou d'une entité) : affichée en aide dans l'en-tête, réutilisable pour guider l'IA. */
  definition: string;
  type: FieldType;
  required: boolean;
  defaultValue: CustomValue;
  /** Valeurs possibles (type `choice`). */
  choices: string[];
  /** Code devise ISO (type `amount`). */
  currency: string;
}

export interface TrackingStatus {
  id: string;
  label: string;
  /** Variante du badge DSFR. */
  tone: "new" | "info" | "success" | "warning" | "error";
  final: boolean;
  /** Catégorie commune à toutes les analyses : sert au filtre de la vue transversale (statuts propres à chaque analyse). */
  category: StatusCategory;
}

export type StatusCategory = "initial" | "progress" | "final";

export const STATUS_CATEGORY_LABELS: Record<StatusCategory, string> = {
  initial: "À démarrer",
  progress: "En cours",
  final: "Clos",
};

export interface Assignee {
  id: string;
  name: string;
}

export interface MockAnalyse {
  id: string;
  name: string;
}

/** Une ligne du tableau de suivi telle que la renvoie l'API (`GET /api/tracking`, #173). */
export interface TrackingListRow {
  id: string;
  /** Référence lisible (« DOS-2026-0042 »). */
  reference: string;
  name: string;
  analyse: { id: string; name: string };
  status: { id: string; name: string; color: string; isFinal: boolean } | null;
  assignee: Assignee | null;
  dueAt: string | null;
  /** Niveau d'échéance calculé par le serveur selon les seuils de l'analyse (#172). */
  due: DueInfo | null;
  createdAt: string;
  lastActivityAt: string;
  /** Valeurs des colonnes personnalisées : pas encore portées par l'API, toujours vide. */
  values: Record<string, CustomValue>;
}

export interface TrackingRow {
  id: string;
  reference: string;
  /** Nom du dossier (le tableau de bord l'affiche aussi). */
  name: string;
  analyseId: string;
  statusId: string;
  assigneeId: string | null;
  dueAt: string | null;
  createdAt: string;
  lastActivityAt: string;
  values: Record<string, CustomValue>;
}

/** Colonne affichable : une colonne native, ou `field:<id>` pour un champ personnalisé. */
export type ColumnId = "reference" | "name" | "analyse" | "status" | "assignee" | "due" | "createdAt" | "lastActivityAt" | `field:${string}`;

export interface ColumnDef {
  id: ColumnId;
  label: string;
  /** Aide de la colonne, affichée dans l'en-tête. */
  definition: string;
  sortable: boolean;
}

export const NATIVE_COLUMNS: ColumnDef[] = [
  { id: "reference", label: "Référence", definition: "Référence unique du dossier. Cliquez pour l'ouvrir.", sortable: true },
  { id: "name", label: "Dossier", definition: "Nom du dossier.", sortable: true },
  { id: "analyse", label: "Analyse", definition: "Analyse à laquelle le dossier est rattaché. Les colonnes personnalisées dépendent de l'analyse.", sortable: true },
  { id: "status", label: "Statut", definition: "Étape du dossier dans le traitement, selon les statuts définis par l'analyse.", sortable: true },
  { id: "assignee", label: "Affecté à", definition: "Instructeur responsable du dossier. Modifiable directement dans la ligne.", sortable: true },
  { id: "due", label: "Échéance", definition: "Date limite de traitement. La couleur indique le temps restant, selon les seuils de l'analyse.", sortable: true },
  { id: "createdAt", label: "Créé le", definition: "Date d'arrivée du dossier dans l'application.", sortable: true },
  { id: "lastActivityAt", label: "Dernière activité", definition: "Dernière action enregistrée sur le dossier (consultation exclue).", sortable: true },
];

/** Filtre d'un champ personnalisé : texte/choix/booléen en chaîne, plage pour nombre, montant et date. */
export type FieldFilter = string | { min: string; max: string };

export interface TrackingFilters {
  search: string;
  /** Identifiant de statut, ou « cat:<catégorie> » (initial, progress, final) dans la vue transversale. */
  statusId: string;
  /** Analyses retenues (vide = toutes celles auxquelles l'utilisateur a accès). */
  analyseIds: string[];
  /** « me » = moi, « none » = non affecté, sinon identifiant d'utilisateur. */
  assignee: string;
  /** « overdue », « 7 », « 30 » (jours restants au plus), « none » (sans date). */
  due: string;
  /** « restricted » ou « analyse » (visibilité du dossier, #177) ; vide = tous. */
  access: string;
  fieldFilters: Record<string, FieldFilter>;
}

export interface TrackingSort {
  key: ColumnId;
  dir: "asc" | "desc";
}

export interface TrackingView {
  id: string;
  name: string;
  builtIn: boolean;
  filters: TrackingFilters;
  sort: TrackingSort;
}

export interface ColumnPrefs {
  order: ColumnId[];
  hidden: ColumnId[];
}

export const emptyFilters = (): TrackingFilters => ({
  search: "",
  statusId: "",
  analyseIds: [],
  assignee: "",
  due: "",
  access: "",
  fieldFilters: {},
});
