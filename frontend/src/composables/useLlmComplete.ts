import { apiFetch } from "@/utils/api";

// Appel générique de chat completion (POST /api/llm/complete), utilisé par
// toutes les aides LLM (useLlmAssist.ts) : elles construisent le prompt,
// cette fonction se contente de l'envoyer et de renvoyer le texte produit.
export async function completeChat(prompt: string, model: string | null): Promise<string> {
  const data = await apiFetch<{ content: string }>("/api/llm/complete", {
    method: "POST",
    body: JSON.stringify({ prompt, model }),
  });
  return data.content;
}

/** Extrait et parse le premier objet/tableau JSON trouvé dans une réponse LLM, qui peut être entouré de texte ou de balises ```. */
export function parseJsonFromCompletion<T>(content: string): T {
  for (const [open, close] of [
    ["[", "]"],
    ["{", "}"],
  ] as const) {
    const start = content.indexOf(open);
    const end = content.lastIndexOf(close);
    if (start !== -1 && end > start) return JSON.parse(content.slice(start, end + 1)) as T;
  }
  throw new Error("Réponse LLM invalide : JSON attendu.");
}
