export interface CguVersion {
  id: string;
  content: string;
  version: number;
  publishedAt: string | null;
}

export interface CguAdminVersion {
  id: string;
  content: string;
  version: number;
  isActive: boolean;
  publishedAt: string | null;
  createdBy: string | null;
  createdAt: string;
}

export interface CguAcceptanceStatus {
  accepted: boolean;
  cgu: CguVersion | null;
}
