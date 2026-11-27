import { api } from "@/shared/api";

/** What a card tile shows. `rank` sorts the cards of a list as plain text. */
export interface Card {
  id: number;
  list_id: number;
  title: string;
  rank: string;
  due_at: string | null;
  done_at: string | null;
  cover_color: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

/** A list with its open cards in order. */
export interface List {
  id: number;
  board_id: number;
  name: string;
  rank: string;
  created_at: string;
  archived_at: string | null;
  cards: Card[];
}

/** The board the lists belong to. */
export interface BoardRef {
  id: number;
  project_id: number;
}

const at = (slug: string, board: BoardRef) =>
  `/api/orgs/${encodeURIComponent(slug)}/projects/${board.project_id}/boards/${board.id}`;

/** The whole open board: lists in order, each with its open cards. */
export function boardLists(slug: string, board: BoardRef): Promise<List[]> {
  return api<List[]>(`${at(slug, board)}/lists`);
}
