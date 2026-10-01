// Analyse de dossier (backend issues #112 et #114) : une analyse par
// exécution, faite d'éléments qui ont chacun plusieurs versions, et des
// propositions de modification que l'utilisateur accepte, modifie ou rejette.

export type AnalysisElementKind = "classification" | "entity" | "relation" | "synthesis" | "field";

export const ELEMENT_KIND_LABELS: Record<AnalysisElementKind, string> = {
  classification: "Classifications",
  entity: "Entités",
  relation: "Relations",
  synthesis: "Synthèses",
  field: "Champs",
};

export type VersionOrigin = "model" | "instructor" | "carried_over";

export const VERSION_ORIGIN_LABELS: Record<VersionOrigin, string> = {
  model: "Modèle",
  instructor: "Instructeur",
  carried_over: "Reprise",
};

export type DossierAnalysisStatus = "brouillon" | "validée" | "figée";

export type VersionSourceType = "chat_message" | "note" | "proposal";

export const VERSION_SOURCE_LABELS: Record<string, string> = {
  chat_message: "message du chat",
  note: "note",
  proposal: "proposition",
};

/** Valeur d'une version : sa forme dépend du type de l'élément. */
export type ElementValue = Record<string, unknown>;

export interface ElementVersion {
  id: string;
  elementId: string;
  versionNumber: number;
  value: ElementValue;
  confidence: number | null;
  origin: VersionOrigin;
  predictionId: string | null;
  authorId: string | null;
  reason: string | null;
  sourceType: string | null;
  sourceId: string | null;
  restoredFromVersionId: string | null;
  createdAt: string;
}

export interface AnalysisElement {
  id: string;
  analysisId: string;
  unitId: string | null;
  kind: AnalysisElementKind;
  definitionName: string | null;
  documentId: string | null;
  firstPageNumber: number | null;
  needsReview: boolean;
  reviewReason: string | null;
  /** Version retenue : celle qui fait foi. */
  retainedVersion: ElementVersion | null;
  /** Dernière version produite par le modèle (peut différer de la retenue). */
  latestModelVersion: ElementVersion | null;
  createdAt: string;
}

export interface DossierAnalysisSummary {
  id: string;
  dossierId: string;
  sequence: number;
  status: DossierAnalysisStatus;
  analyseVersion: string | null;
  model: string | null;
  startedAt: string | null;
  endedAt: string | null;
  createdAt: string;
}

export interface DossierAnalysis extends DossierAnalysisSummary {
  elements: AnalysisElement[];
}

export type ProposalStatus = "pending" | "accepted" | "modified" | "rejected";

export const PROPOSAL_STATUS_LABELS: Record<ProposalStatus, string> = {
  pending: "En attente",
  accepted: "Acceptée",
  modified: "Acceptée avec modification",
  rejected: "Rejetée",
};

export interface Proposal {
  id: string;
  analysisId: string;
  /** Vide quand la proposition ajoute un nouvel élément. */
  elementId: string | null;
  kind: AnalysisElementKind;
  definitionName: string | null;
  proposedValue: ElementValue;
  reason: string;
  sourceType: string | null;
  proposedBy: string;
  status: ProposalStatus;
  decidedBy: string | null;
  decidedAt: string | null;
  createdAt: string;
}

/** Texte lisible d'une valeur d'élément. `resolveElement` retrouve le nom d'un élément relié. */
export function valueToText(
  kind: AnalysisElementKind,
  value: ElementValue,
  resolveElement?: (id: string) => string | undefined,
): string {
  switch (kind) {
    case "classification":
      return String(value.label ?? "");
    case "entity":
    case "field":
      return String(value.value ?? "");
    case "synthesis":
      return String(value.text ?? "");
    case "relation": {
      const source = String(value.source_element_id ?? "");
      const target = String(value.target_element_id ?? "");
      const from = resolveElement?.(source) ?? "…";
      const to = resolveElement?.(target) ?? "…";
      return `${from} — ${String(value.type ?? "")} → ${to}`;
    }
  }
}

/** Valeur d'élément à envoyer au backend à partir du texte saisi (null si le type n'est pas éditable en texte). */
export function textToValue(kind: AnalysisElementKind, text: string): ElementValue | null {
  switch (kind) {
    case "classification":
      return { label: text };
    case "entity":
    case "field":
      return { value: text };
    case "synthesis":
      return { text };
    case "relation":
      return null;
  }
}
