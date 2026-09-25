/**
 * Tâches utilisateur (issue #62) : suivi des tâches asynchrones (Celery)
 * lancées par l'utilisateur courant.
 *
 * Miroir de `backend/app/schemas/user_task.py` → UserTaskOut.
 */

export type UserTaskKind =
  | "text_extraction"
  | "classification"
  | "entity_extraction"
  | "agent_execution"
  | "chat_response"
  | "helper_chat"
  | "document_summary"
  | "dossier_summary"
  | "analyse_suggestion";

export type UserTaskStatus = "pending" | "running" | "success" | "failure";

export interface UserTask {
  id: string;
  kind: UserTaskKind;
  status: UserTaskStatus;
  label: string;
  celery_task_id: string | null;
  target_id: string | null;
  target_type: string | null;
  error: string | null;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
}
