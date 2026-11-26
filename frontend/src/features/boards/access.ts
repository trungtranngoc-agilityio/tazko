import type { Project } from "@/features/projects";

// What the board screens offer, from the same rules the server enforces
// (backend modules/projects/access.py). Hiding a control is not the check.

/** Create boards: project owners, and members while the project lets them. */
export function createsBoards(project: Project): boolean {
  if (project.archived_at) return false;
  return (
    project.role === "owner" || (project.role === "member" && project.members_can_create_boards)
  );
}

/** Rename, close and reopen boards: project owners and members. */
export function editsBoards(project: Project): boolean {
  return !project.archived_at && (project.role === "owner" || project.role === "member");
}
