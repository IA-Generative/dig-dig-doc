import { ref } from "vue";

import { apiFetch } from "@/utils/api";
import type { ReportAdmin, ReportStatus, ReportType } from "@/types/report";

function mapReportAdmin(api: any): ReportAdmin {
  return {
    id: api.id,
    type: api.type,
    title: api.title,
    description: api.description,
    status: api.status,
    hasScreenshot: api.has_screenshot,
    adminResponse: api.admin_response,
    createdAt: api.created_at,
    userDisplay: api.user_display,
    respondedBy: api.responded_by,
  };
}

/** Signalements de tous les utilisateurs, réservé aux admins (page Administration). */
export function useReportsAdmin() {
  const reports = ref<ReportAdmin[]>([]);
  const total = ref(0);
  const pageCount = ref(1);
  const currentPage = ref(1);
  const pageSize = ref(20);

  const fetchList = async (
    page = currentPage.value,
    size = pageSize.value,
    statusFilter?: ReportStatus,
    typeFilter?: ReportType,
  ) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(size) });
    if (statusFilter) params.set("status_filter", statusFilter);
    if (typeFilter) params.set("type_filter", typeFilter);
    const data = await apiFetch<{ items: any[]; total: number; page: number; page_size: number; pages: number }>(
      `/api/admin/reports?${params}`,
    );
    reports.value = data.items.map(mapReportAdmin);
    total.value = data.total;
    pageCount.value = data.pages;
    currentPage.value = data.page;
    pageSize.value = data.page_size;
  };

  const updateReport = async (reportId: string, status: ReportStatus, adminResponse: string | null) => {
    const data = await apiFetch<any>(`/api/admin/reports/${reportId}`, {
      method: "PATCH",
      body: JSON.stringify({ status, admin_response: adminResponse }),
    });
    const updated = mapReportAdmin(data);
    const index = reports.value.findIndex((r) => r.id === updated.id);
    if (index !== -1) reports.value[index] = updated;
    return updated;
  };

  return { reports, total, pageCount, currentPage, pageSize, fetchList, updateReport };
}
