import type { StreamEvent } from "@/composables/useChatStream";

export interface ToolStep {
  name: string;
  args: Record<string, unknown>;
  /** Aperçu du résultat (200 caractères max, tronqué par le worker). */
  result: string | null;
  status: "running" | "done" | "error";
}

// Regroupe les événements tool_call / tool_result en étapes : un tool_call
// ouvre une étape, le tool_result suivant la ferme. Le worker appelle les
// outils un par un, donc l'association par ordre est fiable.
export function groupToolEvents(events: StreamEvent[]): ToolStep[] {
  const steps: ToolStep[] = [];

  for (const event of events) {
    if (event.kind === "tool_call") {
      steps.push({
        name: String(event.data.tool_name ?? "outil"),
        args: (event.data.arguments as Record<string, unknown>) ?? {},
        result: null,
        status: "running",
      });
    } else if (event.kind === "tool_result") {
      const step = findRunning(steps);
      if (step) {
        step.result = String(event.data.preview ?? "");
        step.status = "done";
      }
    } else if (event.kind === "error") {
      const step = findRunning(steps);
      if (step) step.status = "error";
    }
  }

  return steps;
}

function findRunning(steps: ToolStep[]): ToolStep | undefined {
  for (let i = steps.length - 1; i >= 0; i--) {
    if (steps[i].status === "running") return steps[i];
  }
  return undefined;
}
