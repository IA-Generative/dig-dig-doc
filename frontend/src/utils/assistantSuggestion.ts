/**
 * Le worker ajoute en fin de réponse un commentaire HTML
 * `<!--assistant-suggestion:<question encodée>-->` quand le chat du dossier
 * propose d'ouvrir l'assistant de l'application (voir
 * worker/agent_execution/app/chat_graph.py).
 */
const MARKER = /\n*<!--assistant-suggestion:([^>]*?)-->\s*$/;

export interface AssistantSuggestion {
  /** Contenu du message sans le marqueur. */
  text: string;
  /** Question à pré-remplir dans l'assistant, null s'il n'y a pas de proposition. */
  question: string | null;
}

export function parseAssistantSuggestion(content: string): AssistantSuggestion {
  const match = MARKER.exec(content);
  if (!match) return { text: content, question: null };
  let question: string | null;
  try {
    question = decodeURIComponent(match[1]) || null;
  } catch {
    question = null;
  }
  return { text: content.slice(0, match.index), question };
}
