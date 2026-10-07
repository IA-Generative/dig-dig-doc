// Le navigateur parle directement au backend via l'ingress (même host) :
// le cookie de session du BFF est scopé à cette origine, et le CORS du
// backend autorise explicitement le frontend (voir KeycloakSettings.FRONTEND_URL).
// En dev local, VITE_API_BASE_URL peut pointer vers http://localhost:8000.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    /** Détail brut renvoyé par le serveur (texte, liste d'erreurs ou objet structuré, ex. rapport de validation). */
    public detail?: unknown,
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
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    // Un détail structuré (`{code, message}`) donne son message ; sinon le libellé HTTP.
    const message =
      typeof detail === "string"
        ? detail
        : typeof detail?.message === "string"
          ? detail.message
          : // Erreur de validation FastAPI : le premier message, sans le préfixe technique de Pydantic.
            typeof detail?.[0]?.msg === "string"
            ? detail[0].msg.replace(/^Value error, /, "")
            : response.statusText;
    throw new ApiError(response.status, message, detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
