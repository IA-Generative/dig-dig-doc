// Notes internes d'un dossier (backend issue #117) : versionnées, internes
// (jamais visibles de l'usager), pouvant servir de source à des propositions
// de mise à jour de l'analyse de dossier.

export type NoteAnalysisStatus = "en_cours" | "terminé" | "échec";

export interface DossierNote {
  id: string;
  dossierId: string;
  createdBy: string;
  archived: boolean;
  /** Contenu actuel (dernière version). */
  content: string;
  versionNumber: number;
  lastAuthorId: string;
  createdAt: string;
  updatedAt: string;
  /** Analyse de la note par le worker pour proposer des mises à jour (sur demande). */
  analysisStatus: NoteAnalysisStatus | null;
  /** Version de la note qui a été analysée. */
  analysisVersionNumber: number | null;
  analysisProposalCount: number | null;
  analysisError: string | null;
}

export interface NoteVersion {
  id: string;
  noteId: string;
  versionNumber: number;
  content: string;
  authorId: string;
  restoredFromVersionId: string | null;
  createdAt: string;
}
