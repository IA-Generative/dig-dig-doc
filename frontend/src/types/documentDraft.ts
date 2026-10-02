// Brouillons de document et documents générés (backend issues #140, #141, #142, #143). Internes : jamais montrés
// à l'usager. Un brouillon lie un modèle (version précise) à une révision précise de l'analyse du dossier.

import type { FieldSource, FieldType } from "@/types/documentTemplate";

export type FieldStatus = "non_renseigné" | "proposé" | "validé";
export type FieldOrigin = "analysis" | "agent" | "instructor";
export type GenerationStatus = "en_cours" | "terminé" | "échec";

export const FIELD_STATUS_LABELS: Record<FieldStatus, string> = {
  non_renseigné: "Non renseigné",
  proposé: "Proposé",
  validé: "Validé",
};

export const FIELD_ORIGIN_LABELS: Record<FieldOrigin, string> = {
  analysis: "Donnée de l'analyse",
  agent: "Proposé par l'agent",
  instructor: "Saisi par un instructeur",
};

/** Valeur d'un champ : texte, nombre, booléen ou liste de textes selon son type. */
export type FieldValue = string | number | boolean | string[] | null;

export interface SourceDetail {
  type: string;
  label: string;
  text: string;
  page: number | null;
}

export interface FieldVersion {
  id: string;
  fieldName: string;
  versionNumber: number;
  value: FieldValue;
  status: FieldStatus;
  origin: FieldOrigin;
  authorId: string | null;
  reason: string | null;
  restoredFromVersionId: string | null;
  promptVersion: string | null;
  model: string | null;
  createdAt: string;
}

export interface DraftField {
  name: string;
  label: string;
  type: FieldType;
  required: boolean;
  instruction: string;
  source: FieldSource | { kind: string };
  current: FieldVersion;
  sourceDetails: SourceDetail[];
  /** Un élément de l'analyse dont vient la valeur a été modifié depuis la révision du brouillon. */
  stale: boolean;
}

export interface Completeness {
  complete: boolean;
  /** Champs obligatoires non renseignés. */
  missing: string[];
  /** Champs obligatoires seulement proposés (à valider). */
  proposed: string[];
}

export interface DocumentDraft {
  id: string;
  dossierId: string;
  analysisId: string;
  revisionId: string;
  revisionNumber: number;
  templateId: string;
  templateName: string;
  templateVersionNumber: number;
  status: "brouillon" | "généré" | "archivé";
  createdBy: string;
  createdAt: string;
  fields: DraftField[];
  completeness: Completeness;
  generationStatus: GenerationStatus | null;
  generationError: string | null;
  generationProposalCount: number | null;
  generationMissing: string[] | null;
  generationTruncated: boolean;
  generationPromptVersion: string | null;
}

export interface DraftSummary {
  id: string;
  templateName: string;
  templateVersionNumber: number;
  status: string;
  createdBy: string;
  createdAt: string;
}

export interface DossierTemplate {
  id: string;
  name: string;
  description: string;
  versionNumber: number;
  fieldCount: number;
}

export interface GeneratedDocument {
  id: string;
  draftId: string;
  versionNumber: number;
  templateName: string;
  templateVersionNumber: number;
  revisionNumber: number;
  fileName: string;
  hasPdf: boolean;
  odtSize: number | null;
  pdfSize: number | null;
  incompleteFields: string[];
  visibility: string;
  authorId: string;
  createdAt: string;
}

/** Texte d'une valeur, pour l'afficher ou l'éditer (une liste : un élément par ligne). */
export function valueToText(value: FieldValue, type: FieldType): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.join("\n");
  if (type === "boolean" && typeof value === "boolean") return value ? "oui" : "non";
  return String(value);
}

/** Valeur à envoyer pour un texte saisi : liste (une par ligne) ou booléen selon le type du champ. */
export function textToValue(text: string, type: FieldType): FieldValue {
  if (type === "list") return text.split("\n").map((line) => line.trim()).filter(Boolean);
  if (type === "boolean") return text.trim().toLowerCase() === "oui";
  return text.trim();
}
