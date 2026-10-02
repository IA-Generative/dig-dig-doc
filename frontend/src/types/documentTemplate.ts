// Modèles de document (backend issue #138) : un fichier ODT à placeholders {{ nom }} et la définition de ses
// champs, versionnés. Réservés aux administrateurs.

export type FieldType = "text" | "date" | "number" | "list" | "boolean";
export type ElementKind = "classification" | "entity" | "relation" | "synthesis" | "field";

export const FIELD_TYPE_LABELS: Record<FieldType, string> = {
  text: "Texte",
  date: "Date",
  number: "Nombre",
  list: "Liste de textes",
  boolean: "Oui / non",
};

export const ELEMENT_KIND_LABELS: Record<ElementKind, string> = {
  entity: "Entité",
  classification: "Classification",
  relation: "Relation",
  synthesis: "Synthèse",
  field: "Champ renseigné",
};

/** Métadonnées du dossier ou du contexte de génération utilisables comme source d'un champ. */
export const METADATA_KEY_LABELS = {
  dossier_name: "Nom du dossier",
  dossier_id: "Identifiant du dossier",
  dossier_created_at: "Date de création du dossier",
  dossier_started_at: "Date de début d'instruction",
  dossier_ended_at: "Date de fin d'instruction",
  instructor_name: "Nom de l'instructeur",
  instructor_email: "Courriel de l'instructeur",
  generated_at: "Date de génération du document",
  analysis_revision: "Version de l'analyse",
  document_version: "Version du document",
} as const;
export type MetadataKey = keyof typeof METADATA_KEY_LABELS;

export type FieldSource =
  | { kind: "analysis"; elementKind: ElementKind; definitionName: string }
  | { kind: "instruction" }
  | { kind: "dossier_metadata"; key: MetadataKey };

export type SourceKind = FieldSource["kind"];

export const SOURCE_KIND_LABELS: Record<SourceKind, string> = {
  analysis: "Donnée de l'analyse",
  instruction: "Renseigné au fil de l'instruction",
  dossier_metadata: "Métadonnée du dossier",
};

export interface FieldDefinition {
  /** Nom stable : celui du placeholder dans le fichier. */
  name: string;
  label: string;
  type: FieldType;
  required: boolean;
  /** Consigne de génération propre au champ (format de date, longueur, ton). */
  instruction: string;
  source: FieldSource;
}

/** Ce que l'analyse d'un modèle définit : les éléments que la source d'un champ peut désigner. */
export interface AnalyseDefinitions {
  entity: string[];
  classification: string[];
  synthesis: string[];
}

/** Un champ dont la source désigne un élément que l'analyse ne définit pas (rapport du serveur, 422). */
export interface UnknownSource {
  field: string;
  elementKind: ElementKind;
  definitionName: string;
}

export interface SourcesReport {
  message: string;
  unknownSources: UnknownSource[];
}

/** Avertissement du contrôle d'un modèle à l'import (backend issue #148) : à lire, jamais bloquant. */
export interface ImportWarning {
  /** font_substituted, native_field, images, fonts_unchecked. */
  code: string;
  level: "warning" | "info";
  message: string;
}

export interface FontReport {
  name: string;
  /** installed, compatible (mêmes métriques), substituted (la mise en page change) ou unknown. */
  status: "installed" | "compatible" | "substituted" | "unknown";
  replacedBy: string | null;
}

export interface DocumentTemplate {
  id: string;
  /** Analyse à laquelle appartient le modèle : il ne sert qu'aux dossiers de cette analyse. */
  analyseId: string | null;
  archived: boolean;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  versionNumber: number;
  name: string;
  description: string;
  generationInstructions: string;
  fields: FieldDefinition[];
  /** Placeholders trouvés dans le fichier par le worker, à l'import. */
  placeholders: string[];
  /** Avertissements du contrôle à l'import (polices absentes de l'image, champs natifs, images). */
  warnings: ImportWarning[];
  fileName: string;
  fileSize: number;
  lastAuthorId: string;
}

export interface DocumentTemplateVersion {
  id: string;
  versionNumber: number;
  name: string;
  description: string;
  generationInstructions: string;
  fields: FieldDefinition[];
  placeholders: string[];
  fileName: string;
  fileSize: number;
  authorId: string;
  restoredFromVersionId: string | null;
  createdAt: string;
}

export interface TemplateInspection {
  placeholders: string[];
  fileName: string;
  fileSize: number;
  fonts: FontReport[];
  warnings: ImportWarning[];
}

/** Rapport renvoyé par le serveur quand les champs ne correspondent pas au fichier (422). */
export interface PlaceholderReport {
  message: string;
  unknownPlaceholders: string[];
  unusedFields: string[];
}

export interface GenerationPrompt {
  versionNumber: number | null;
  label: string;
  content: string;
  isDefault: boolean;
}
