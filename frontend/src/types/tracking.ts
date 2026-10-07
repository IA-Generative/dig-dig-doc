// Tableau de suivi des dossiers d'une analyse (issue #173, partie UI).
// Les données viennent pour l'instant de mocks (useTracking), en attendant
// les statuts (#168), la péremption (#172) et l'API d'affectation.

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
}

export interface Assignee {
  id: string;
  name: string;
}

export interface TrackingRow {
  id: string;
  reference: string;
  statusId: string;
  assigneeId: string | null;
  expiresAt: string | null;
  createdAt: string;
  lastActivityAt: string;
  values: Record<string, CustomValue>;
}

/** Colonne affichable : une colonne native, ou `field:<id>` pour un champ personnalisé. */
export type ColumnId = "reference" | "status" | "assignee" | "expiry" | "createdAt" | "lastActivityAt" | `field:${string}`;

export interface ColumnDef {
  id: ColumnId;
  label: string;
  /** Aide de la colonne, affichée dans l'en-tête. */
  definition: string;
  sortable: boolean;
}

export const NATIVE_COLUMNS: ColumnDef[] = [
  { id: "reference", label: "Référence", definition: "Référence unique du dossier. Cliquez pour l'ouvrir.", sortable: true },
  { id: "status", label: "Statut", definition: "Étape du dossier dans le traitement, selon les statuts définis par l'analyse.", sortable: true },
  { id: "assignee", label: "Affecté à", definition: "Instructeur responsable du dossier. Modifiable directement dans la ligne.", sortable: true },
  { id: "expiry", label: "Péremption", definition: "Date limite de traitement. La couleur indique le temps restant, selon les seuils de l'analyse.", sortable: true },
  { id: "createdAt", label: "Créé le", definition: "Date d'arrivée du dossier dans l'application.", sortable: true },
  { id: "lastActivityAt", label: "Dernière activité", definition: "Dernière action enregistrée sur le dossier (consultation exclue).", sortable: true },
];

/** Filtre d'un champ personnalisé : texte/choix/booléen en chaîne, plage pour nombre, montant et date. */
export type FieldFilter = string | { min: string; max: string };

export interface TrackingFilters {
  search: string;
  statusId: string;
  /** « me » = moi, « none » = non affecté, sinon identifiant d'utilisateur. */
  assignee: string;
  /** « expired », « 7 », « 30 » (jours restants au plus), « none » (sans date). */
  due: string;
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
  assignee: "",
  due: "",
  fieldFilters: {},
});
