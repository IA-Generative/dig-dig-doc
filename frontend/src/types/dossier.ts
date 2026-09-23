export type DossierStatus = "en_attente" | "en_cours" | "terminé" | "arrêté" | "échec";

export const DOSSIER_STATUS_LABELS: Record<DossierStatus, string> = {
  en_attente: "En attente",
  en_cours: "En cours",
  terminé: "Terminé",
  arrêté: "Arrêté",
  échec: "Échec",
};

export type ExecutionStepStatus = "en_cours" | "terminé" | "échec";

export const EXECUTION_STEP_STATUS_LABELS: Record<ExecutionStepStatus, string> = {
  en_cours: "En cours",
  terminé: "Terminé",
  échec: "Échec",
};

export type ExecutionStepKind = "classification" | "extraction" | "agent";

export interface ExecutionStep {
  id: string;
  kind: ExecutionStepKind;
  label: string;
  status: ExecutionStepStatus;
  startedAt: string;
  endedAt?: string;
  /**
   * Résultat produit par l'étape, présenté dans la page de résultat.
   * Absent tant que l'étape n'est pas terminée, ou pour un agent dont la
   * sortie n'est pas activée (Agent.output === false).
   */
  output?: string;
}

export type TextExtractionStatus = "en_attente" | "en_cours" | "terminé" | "échec";

export const TEXT_EXTRACTION_STATUS_LABELS: Record<TextExtractionStatus, string> = {
  en_attente: "En attente",
  en_cours: "Extraction en cours",
  terminé: "Texte extrait",
  échec: "Échec de l'extraction",
};

export interface DossierDocument {
  id: string;
  name: string;
  size: number;
  s3Key: string;
  mimetype: string;
  /** Nature du document (ex: "CNI") : posée par la classification ou corrigée manuellement. */
  label?: string;
  /** Suivi du run du worker document_process (extract_document_text). */
  textExtractionStatus: TextExtractionStatus;
  textExtractionError?: string;
}

export interface Dossier {
  id: string;
  name: string;
  /** Une analyse est obligatoire : un dossier ne peut pas exister sans être lié à une analyse. */
  analyseId: string;
  /** Version de l'analyse utilisée pour l'exécution (snapshot au lancement). */
  analyseVersion: string;
  createdAt: string;
  status: DossierStatus;
  startedAt?: string;
  endedAt?: string;
  executionSteps: ExecutionStep[];
  documents: DossierDocument[];
}
