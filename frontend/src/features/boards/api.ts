import { api } from "@/shared/api";

/** A board as the signed-in person sees it. `access` (the restricted list) is
 * shown to project owners only; `lists` and `cards` count the open ones. */
export interface Board {
  id: number;
  project_id: number;
  name: string;
  background: string | null;
  restricted: boolean;
  starred: boolean;
  access: number[] | null;
  lists: number;
  cards: number;
  created_at: string;
  archived_at: string | null;
}

export type BoardChanges = { name?: string; background?: string | null; archived?: boolean };

const org = (slug: string) => `/api/orgs/${encodeURIComponent(slug)}`;
const boards = (slug: string, projectId: number) => `${org(slug)}/projects/${projectId}/boards`;
const json = (method: string, body: unknown): RequestInit => ({
  method,
  body: JSON.stringify(body),
});

/** Where a board opens in the web app. */
export function boardPath(slug: string, board: Pick<Board, "id" | "project_id">): string {
  return `/c/${slug}/p/${board.project_id}/b/${board.id}`;
}

export function getBoard(slug: string, projectId: number, boardId: number): Promise<Board> {
  return api<Board>(`${boards(slug, projectId)}/${boardId}`);
}

export function projectBoards(slug: string, projectId: number): Promise<Board[]> {
  return api<Board[]>(boards(slug, projectId));
}

export function starredBoards(slug: string): Promise<Board[]> {
  return api<Board[]>(`${org(slug)}/starred-boards`);
}

export function createBoard(
  slug: string,
  projectId: number,
  name: string,
  background: string | null,
): Promise<Board> {
  return api<Board>(boards(slug, projectId), json("POST", { name, background }));
}

export function updateBoard(slug: string, board: Board, changes: BoardChanges): Promise<Board> {
  return api<Board>(`${boards(slug, board.project_id)}/${board.id}`, json("PATCH", changes));
}

export function setStar(slug: string, board: Board, on: boolean): Promise<void> {
  return api<void>(`${boards(slug, board.project_id)}/${board.id}/star`, {
    method: on ? "PUT" : "DELETE",
  });
}
