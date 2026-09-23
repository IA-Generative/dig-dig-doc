import { computed, reactive } from "vue";

import { apiFetch } from "@/utils/api";
import type { Report, ReportType } from "@/types/report";

function mapReport(api: any): Report {
  return {
    id: api.id,
    type: api.type,
    title: api.title,
    description: api.description,
    status: api.status,
    hasScreenshot: api.has_screenshot,
    adminResponse: api.admin_response,
    createdAt: api.created_at,
  };
}

// "Mes signalements" : partagé par toute l'application (menu utilisateur),
// comme useMyConversations.
const reports = reactive<Report[]>([]);

async function fetchMyReports() {
  const data = await apiFetch<any[]>("/api/reports");
  reports.splice(0, reports.length, ...data.map(mapReport));
}

async function createReport(
  type: ReportType,
  title: string,
  description: string,
  screenshot: File | Blob | null,
): Promise<Report> {
  const formData = new FormData();
  formData.append("type", type);
  formData.append("title", title);
  formData.append("description", description);
  if (screenshot) formData.append("screenshot", screenshot, "screenshot.png");
  const data = await apiFetch<any>("/api/reports", { method: "POST", body: formData });
  const report = mapReport(data);
  reports.unshift(report);
  return report;
}

export function useReports() {
  return { reports: computed(() => reports), fetchMyReports, createReport };
}
