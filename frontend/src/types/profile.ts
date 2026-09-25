export type Theme = "light" | "dark" | "system";

export interface UserPreferences {
  theme: Theme;
}

export interface UserStats {
  conversations_count: number;
  messages_sent_count: number;
  agent_conversations_count: number;
  agent_messages_sent_count: number;
  dossiers_count: number;
  analyses_shared_count: number;
  last_activity_at: string | null;
}
