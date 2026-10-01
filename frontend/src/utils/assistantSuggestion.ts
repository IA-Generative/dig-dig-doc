/**
 * Le worker ajoute en fin de réponse du chat des commentaires HTML invisibles
 * (voir worker/agent_execution/app/chat_graph.py) :
 *
 * - `<!--assistant-suggestion:<question encodée>-->` : le chat propose d'ouvrir
 *   l'assistant de l'application avec cette question pré-remplie (#104) ;
 * - `<!--analysis-proposals:<analyse>:<id>,<id>-->` : le chat a déposé des
 *   propositions de modification de l'analyse du dossier (#115).
 *
 * Ils peuvent être présents ensemble, dans n'importe quel ordre.
 */
const SUGGESTION = /\n*<!--assistant-suggestion:([^>]*?)-->\s*$/;
const PROPOSALS = /\n*<!--analysis-proposals:([^:>]*):([^>]*?)-->\s*$/;

export interface ProposalsRef {
  analysisId: string;
  proposalIds: string[];
}

export interface MessageMarkers {
  /** Contenu du message sans les marqueurs. */
  text: string;
  /** Question à pré-remplir dans l'assistant, null s'il n'y a pas de proposition d'ouvrir l'assistant. */
  question: string | null;
  /** Propositions de modification de l'analyse déposées par cette réponse. */
  proposals: ProposalsRef | null;
}

function decode(value: string): string | null {
  try {
    return decodeURIComponent(value) || null;
  } catch {
    return null;
  }
}

export function parseMessageMarkers(content: string): MessageMarkers {
  let text = content;
  let question: string | null = null;
  let proposals: ProposalsRef | null = null;

  // On retire les marqueurs de la fin vers le début, quel que soit leur ordre.
  for (;;) {
    const suggestion = SUGGESTION.exec(text);
    if (suggestion) {
      question = decode(suggestion[1]);
      text = text.slice(0, suggestion.index);
      continue;
    }
    const found = PROPOSALS.exec(text);
    if (found) {
      const analysisId = decode(found[1]);
      const proposalIds = found[2].split(",").filter(Boolean);
      if (analysisId && proposalIds.length > 0) proposals = { analysisId, proposalIds };
      text = text.slice(0, found.index);
      continue;
    }
    break;
  }
  return { text, question, proposals };
}

export interface AssistantSuggestion {
  /** Contenu du message sans les marqueurs. */
  text: string;
  /** Question à pré-remplir dans l'assistant, null s'il n'y a pas de proposition. */
  question: string | null;
}

export function parseAssistantSuggestion(content: string): AssistantSuggestion {
  const { text, question } = parseMessageMarkers(content);
  return { text, question };
}
