import { ref } from "vue";

import { API_BASE_URL } from "@/utils/api";

/**
 * Événement de streaming générique : un payload JSON libre + un type
 * d'événement (par défaut "chat-event"). Permet de réutiliser le même
 * composable pour les conversations de dossier (ChatEvent) et les
 * conversations de l'agent helper (AgentChatEvent).
 */
export interface StreamEvent {
  kind: string;
  data: Record<string, unknown>;
}

export interface UseChatStreamOptions {
  /** Nom de l'événement SSE à écouter (défaut : "chat-event"). */
  eventName?: string;
  /** Appelé à chaque événement reçu. */
  onEvent: (event: StreamEvent) => void;
  /** Appelé quand le serveur émet "done" (exécution terminée). */
  onDone: () => void;
  /** Appelé en cas d'erreur SSE (connexion perdue, etc.). */
  onError?: () => void;
}

/**
 * Composable SSE générique pour le streaming de chat.
 *
 * Factorise la logique d'abonnement EventSource qui était inline dans
 * `useConversations.streamConversation` et `DossierDetailPage.submit`.
 * Le frontend ouvre un flux, reçoit les événements d'exécution (tool_call,
 * tool_result, thinking, done, error) en temps réel, puis le serveur
 * ferme la connexion avec un événement "done".
 *
 * Retourne :
 * - `isRunning` : ref booléen, vrai pendant que le flux est ouvert.
 * - `start(url)` : ouvre l'EventSource, retourne une fonction `close()`.
 * - `stop()` : ferme le flux manuellement (ex: onUnmounted).
 */
export function useChatStream(options: UseChatStreamOptions) {
  const { eventName = "chat-event", onEvent, onDone, onError } = options;
  const isRunning = ref(false);
  let eventSource: EventSource | undefined;

  function start(url: string): () => void {
    stop();
    const fullUrl = url.startsWith("http") ? url : `${API_BASE_URL}${url}`;
    eventSource = new EventSource(fullUrl, { withCredentials: true });
    isRunning.value = true;

    eventSource.addEventListener(eventName, (event) => {
      try {
        const data = JSON.parse(event.data);
        onEvent(data);
      } catch {
        // Payload malformé : on ignore l'événement plutôt que de planter le flux.
      }
    });
    eventSource.addEventListener("done", () => {
      eventSource?.close();
      eventSource = undefined;
      isRunning.value = false;
      onDone();
    });
    eventSource.addEventListener("error", () => {
      eventSource?.close();
      eventSource = undefined;
      isRunning.value = false;
      onError?.();
    });

    return stop;
  }

  function stop() {
    if (eventSource) {
      eventSource.close();
      eventSource = undefined;
      isRunning.value = false;
    }
  }

  return { isRunning, start, stop };
}
