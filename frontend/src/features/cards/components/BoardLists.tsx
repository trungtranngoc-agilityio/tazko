import type { List } from "../api";
import { ListColumn } from "./ListColumn";

/** The lists of a board side by side (prototype .lists), in the server's order. */
export function BoardLists({ lists }: { lists: List[] }) {
  return (
    <div className="flex min-h-0 flex-1 items-start gap-3 overflow-x-auto overflow-y-hidden px-4 pt-3 pb-[18px]">
      {lists.map((list) => (
        <ListColumn key={list.id} list={list} />
      ))}
    </div>
  );
}
