export interface AdminStats {
  analyses_count: number;
  dossiers_count: number;
  conversations_count: number;
  messages_count: number;
  agent_conversations_count: number;
  agent_messages_count: number;
  reports_count: number;
  users_count: number;
  dossiers_by_status: Record<string, number>;
  daily_creations: { date: string; count: number }[];
  top_models: { model: string; count: number }[];
}

export interface AdminTask {
  worker: string;
  name: string;
  id?: string;
  args?: unknown;
  kwargs?: unknown;
  time_start?: number | null;
  acknowledged?: boolean | null;
}

export interface AdminTasks {
  workers: string[];
  registered: AdminTask[];
  active: AdminTask[];
  reserved: AdminTask[];
  scheduled: AdminTask[];
}
