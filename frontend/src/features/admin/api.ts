import type { Account, Invite, Role } from "@/features/orgs";
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

export interface AnyInvite extends Invite {
  company: CompanyRef;
}

export interface Person {
  id: number;
  name: string;
  email: string;
  avatar_url: string | null;
  account: Account;
  companies: (CompanyRef & { role: Role })[];
  last_seen_at: string | null;
  is_super_admin: boolean;
  active: boolean;
}

export interface Page<T> {
  items: T[];
  next: number | null;
}

/** The audit log filter, as the API names the kinds (the part of `action`
 * before the dot). */
export const AUDIT_KINDS = [
  "signin",
  "company",
  "member",
  "invite",
  "person",
  "super_admin",
  "account",
  "workspace_domain",
] as const;
export type AuditKind = (typeof AUDIT_KINDS)[number];

export interface AuditEntry {
  id: number;
  at: string;
  action: string;
  actor: { id: number; name: string; email: string } | null;
  company: CompanyRef | null;
  target: string | null;
  detail: Record<string, unknown> | null;
  ip: string | null;
}

export interface ServerInfo {
  version: string;
  public_url: string;
  uptime_seconds: number;
  data_bytes: number;
  last_backup: null;
  email: { enabled: boolean; host: string | null; port: number | null; sender: string | null };
}

export interface WorkspaceDomain {
  domain: string;
  first_seen_at: string;
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

export function suspendCompany(slug: string): Promise<CompanySummary> {
  return api<CompanySummary>(`${consoleCompanyBase(slug)}/suspend`, { method: "POST" });
}

export function resumeCompany(slug: string): Promise<CompanySummary> {
  return api<CompanySummary>(`${consoleCompanyBase(slug)}/resume`, { method: "POST" });
}

/** Moves the company to trash for 30 days; `confirm` is the short name typed again. */
export function deleteCompany(slug: string, confirm: string): Promise<void> {
  return api<void>(consoleCompanyBase(slug), {
    method: "DELETE",
    body: JSON.stringify({ confirm }),
  });
}

export function allInvites(): Promise<AnyInvite[]> {
  return api<AnyInvite[]>(`${ROOT}/invites`);
}

export function revokeAnyInvite(id: number): Promise<void> {
  return api<void>(`${ROOT}/invites/${id}`, { method: "DELETE" });
}

function query(params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export function people(q: string, after: number | null): Promise<Page<Person>> {
  return api<Page<Person>>(`${ROOT}/people${query({ q: q.trim(), after })}`);
}

export function setPersonFlags(
  id: number,
  flags: { is_super_admin?: boolean; active?: boolean },
): Promise<Person> {
  return api<Person>(`${ROOT}/people/${id}`, { method: "PATCH", body: JSON.stringify(flags) });
}

export function auditLog(kind: AuditKind | null, before: number | null): Promise<Page<AuditEntry>> {
  return api<Page<AuditEntry>>(`${ROOT}/audit${query({ kind, before })}`);
}

export function server(): Promise<ServerInfo> {
  return api<ServerInfo>(`${ROOT}/server`);
}

export function workspaceDomains(): Promise<WorkspaceDomain[]> {
  return api<WorkspaceDomain[]>(`${ROOT}/workspace-domains`);
}

export function forgetWorkspaceDomain(domain: string): Promise<void> {
  return api<void>(`${ROOT}/workspace-domains/${encodeURIComponent(domain)}`, {
    method: "DELETE",
  });
}
