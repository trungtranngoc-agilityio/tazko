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

const base = (slug: string) => `/api/orgs/${encodeURIComponent(slug)}`;

export function members(slug: string): Promise<Member[]> {
  return api<Member[]>(`${base(slug)}/members`);
}

export function changeRole(slug: string, userId: number, role: Role): Promise<Member> {
  return api<Member>(`${base(slug)}/members/${userId}`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
}

export function removeMember(slug: string, userId: number): Promise<void> {
  return api<void>(`${base(slug)}/members/${userId}`, { method: "DELETE" });
}

export function invites(slug: string): Promise<Invite[]> {
  return api<Invite[]>(`${base(slug)}/invites`);
}

export function invite(slug: string, email: string, role: Role): Promise<Invite> {
  return api<Invite>(`${base(slug)}/invites`, {
    method: "POST",
    body: JSON.stringify({ email, role }),
  });
}

export function revokeInvite(slug: string, id: number): Promise<void> {
  return api<void>(`${base(slug)}/invites/${id}`, { method: "DELETE" });
}
