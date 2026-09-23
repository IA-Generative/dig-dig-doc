export type ReportType = "bug" | "idea" | "question";

export type ReportStatus = "new" | "in_progress" | "resolved" | "wont_fix";

export const REPORT_TYPE_LABELS: Record<ReportType, string> = {
  bug: "Bug",
  idea: "Idée",
  question: "Question",
};

export const REPORT_STATUS_LABELS: Record<ReportStatus, string> = {
  new: "Nouveau",
  in_progress: "En cours",
  resolved: "Résolu",
  wont_fix: "Refusé",
};

export interface Report {
  id: string;
  type: ReportType;
  title: string;
  description: string;
  status: ReportStatus;
  hasScreenshot: boolean;
  adminResponse: string | null;
  createdAt: string;
}

/** Vue admin : mêmes champs qu'un Report, plus l'identité de l'auteur et du répondant. */
export interface ReportAdmin extends Report {
  userDisplay: string;
  respondedBy: string | null;
}
