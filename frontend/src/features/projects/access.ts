import type { Project, ProjectRole } from "./api";

// What a screen offers, from the same rules the server enforces
// (backend modules/projects/access.py). Hiding a control is not the check.

/** Roles the person may invite someone as, in the order of the prototype's menu. */
export function inviteRoles(project: Project, companyOwner: boolean): ProjectRole[] {
  if (project.archived_at) return [];
  if (project.role === "owner") return ["member", "observer", "owner"];
  const roles: ProjectRole[] =
    project.role === "member" && project.members_can_invite ? ["member", "observer"] : [];
  // Company owners manage every project's owners, in it or not.
  return companyOwner ? [...roles, "owner"] : roles;
}

/** Change roles and remove people: project owners, while the project is open. */
export function managesMembers(project: Project): boolean {
  return project.role === "owner" && !project.archived_at;
}

/** The Settings tab: project owners. */
export function editsSettings(project: Project): boolean {
  return project.role === "owner";
}
