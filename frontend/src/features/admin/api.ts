import { api } from "@/shared/api";

// The super admin console API (/admin/api, M1-06). Members and invites of one
// company use the orgs feature's calls with consoleCompanyBase(slug).

export interface CompanySummary {
  slug: string;
  name: string;
  status: "active" | "suspended";
  members: number;
  storage_bytes: number;
  storage_limit_bytes: number | null;
  last_activity_at: string | null;
}

export interface CompanyRef {
  slug: string;
  name: string;
}

const ROOT = "/admin/api";

/** The console's path for one company; pass it to the orgs members and invites calls. */
export const consoleCompanyBase = (slug: string) => `${ROOT}/companies/${encodeURIComponent(slug)}`;

export function companies(): Promise<CompanySummary[]> {
  return api<CompanySummary[]>(`${ROOT}/companies`);
}

export function company(slug: string): Promise<CompanySummary> {
  return api<CompanySummary>(consoleCompanyBase(slug));
}

export function createCompany(slug: string, name: string): Promise<CompanySummary> {
  return api<CompanySummary>(`${ROOT}/companies`, {
    method: "POST",
    body: JSON.stringify({ slug, name }),
  });
}
