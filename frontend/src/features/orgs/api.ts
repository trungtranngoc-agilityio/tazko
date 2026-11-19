import { api } from "@/shared/api";

export type Role = "owner" | "member";
export type Account = "workspace" | "personal" | null;

/** A company in the switcher (GET /api/orgs). */
export interface Company {
  slug: string;
  name: string;
  role: Role;
  status: "active" | "suspended";
}

export interface Member {
  user_id: number;
  name: string;
  email: string;
  avatar_url: string | null;
  account: Account;
  role: Role;
  last_seen_at: string | null;
}

export interface Invite {
  id: number;
  email: string;
  role: Role;
  account: Account;
  invited_by: string | null;
  created_at: string;
  expires_at: string;
}

export function myCompanies(): Promise<Company[]> {
  return api<Company[]>("/api/orgs");
}

/** Where one company's members and invites live: `/api/orgs/<slug>` for its
 * owners, `/admin/api/companies/<slug>` for super admins (same contract). */
export const companyBase = (slug: string) => `/api/orgs/${encodeURIComponent(slug)}`;

export function members(base: string): Promise<Member[]> {
  return api<Member[]>(`${base}/members`);
}

export function changeRole(base: string, userId: number, role: Role): Promise<Member> {
  return api<Member>(`${base}/members/${userId}`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
}

export function removeMember(base: string, userId: number): Promise<void> {
  return api<void>(`${base}/members/${userId}`, { method: "DELETE" });
}

export function invites(base: string): Promise<Invite[]> {
  return api<Invite[]>(`${base}/invites`);
}

export function invite(base: string, email: string, role: Role): Promise<Invite> {
  return api<Invite>(`${base}/invites`, {
    method: "POST",
    body: JSON.stringify({ email, role }),
  });
}

export function revokeInvite(base: string, id: number): Promise<void> {
  return api<void>(`${base}/invites/${id}`, { method: "DELETE" });
}
