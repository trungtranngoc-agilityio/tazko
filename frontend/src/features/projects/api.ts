import { api } from "@/shared/api";
import type { Account } from "@/features/orgs";

export type ProjectRole = "owner" | "member" | "observer";
export type AgingDays = 3 | 7 | 14 | 30;

/** A project as the signed-in person sees it; `role` is null for a company
 * owner who is not in it. */
export interface Project {
  id: number;
  name: string;
  description: string;
  color: string | null;
  default_background: string | null;
  members_can_create_boards: boolean;
  members_can_invite: boolean;
  aging_enabled: boolean;
  aging_days: number;
  created_at: string;
  archived_at: string | null;
  role: ProjectRole | null;
}

export interface Person {
  user_id: number;
  name: string;
}

/** A project on Your projects. */
export interface ProjectCard extends Project {
  members: number;
  people: Person[];
  boards: number;
}

/** A row of Manage projects (company owners). */
export interface ProjectSummary {
  id: number;
  name: string;
  color: string | null;
  archived_at: string | null;
  owners: Person[];
  members: number;
  boards: number;
}

export interface ProjectMember {
  user_id: number;
  name: string;
  email: string;
  avatar_url: string | null;
  role: ProjectRole;
  account: Account;
  last_seen_at: string | null;
}

export interface ProjectInvite {
  id: number;
  email: string;
  role: ProjectRole;
  account: Account;
  invited_by: string | null;
  created_at: string;
  expires_at: string;
}

export type ProjectChanges = Partial<
  Pick<
    Project,
    | "name"
    | "description"
    | "color"
    | "default_background"
    | "members_can_create_boards"
    | "members_can_invite"
    | "aging_enabled"
  >
> & { aging_days?: AgingDays; archived?: boolean };

const base = (slug: string) => `/api/orgs/${encodeURIComponent(slug)}/projects`;
const one = (slug: string, id: number) => `${base(slug)}/${id}`;
const json = (method: string, body: unknown): RequestInit => ({
  method,
  body: JSON.stringify(body),
});

export function myProjects(slug: string): Promise<ProjectCard[]> {
  return api<ProjectCard[]>(base(slug));
}

export function manageProjects(slug: string): Promise<ProjectSummary[]> {
  return api<ProjectSummary[]>(`${base(slug)}?view=manage`);
}

export function project(slug: string, id: number): Promise<Project> {
  return api<Project>(one(slug, id));
}

export function createProject(slug: string, name: string, ownerId: number): Promise<Project> {
  return api<Project>(base(slug), json("POST", { name, owner_id: ownerId }));
}

export function updateProject(slug: string, id: number, changes: ProjectChanges): Promise<Project> {
  return api<Project>(one(slug, id), json("PATCH", changes));
}

export function deleteProject(slug: string, id: number): Promise<void> {
  return api<void>(one(slug, id), { method: "DELETE" });
}

export function projectMembers(slug: string, id: number): Promise<ProjectMember[]> {
  return api<ProjectMember[]>(`${one(slug, id)}/members`);
}

export function addProjectMember(
  slug: string,
  id: number,
  userId: number,
  role: ProjectRole,
): Promise<ProjectMember> {
  return api<ProjectMember>(`${one(slug, id)}/members`, json("POST", { user_id: userId, role }));
}

export function setProjectRole(
  slug: string,
  id: number,
  userId: number,
  role: ProjectRole,
): Promise<ProjectMember> {
  return api<ProjectMember>(`${one(slug, id)}/members/${userId}`, json("PATCH", { role }));
}

export function removeProjectMember(slug: string, id: number, userId: number): Promise<void> {
  return api<void>(`${one(slug, id)}/members/${userId}`, { method: "DELETE" });
}

export function projectInvites(slug: string, id: number): Promise<ProjectInvite[]> {
  return api<ProjectInvite[]>(`${one(slug, id)}/invites`);
}

export function inviteToProject(
  slug: string,
  id: number,
  email: string,
  role: ProjectRole,
): Promise<ProjectInvite> {
  return api<ProjectInvite>(`${one(slug, id)}/invites`, json("POST", { email, role }));
}

export function revokeProjectInvite(slug: string, id: number, inviteId: number): Promise<void> {
  return api<void>(`${one(slug, id)}/invites/${inviteId}`, { method: "DELETE" });
}
