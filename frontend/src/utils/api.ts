// Le navigateur parle directement au backend (pas via l'origine Vite/nginx) :
// le cookie de session du BFF est scopé à cette origine, et le CORS du
// backend autorise explicitement le frontend (voir KeycloakSettings.FRONTEND_URL).
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const isFormData = init.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    ...init,
    headers: isFormData ? init.headers : { "Content-Type": "application/json", ...init.headers },
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new ApiError(response.status, detail?.detail ?? response.statusText);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
