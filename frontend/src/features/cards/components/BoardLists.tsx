import { useState } from "react";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { Icon } from "@/shared/ui/Icon";
import { createCard, createList, renameList, type BoardRef, type List } from "../api";
import { Composer } from "./Composer";
import { ListColumn } from "./ListColumn";

// One box open at a time, as in the prototype: a list's card box or the new list box.
type Open = { kind: "card"; listId: number } | { kind: "list" } | null;

/** The lists of a board side by side (prototype .lists), with Add another
 * list at the end. New lists and cards go last, where the server puts them. */
export function BoardLists({
  slug,
  board,
  lists: loaded,
  editable,
}: {
  slug: string;
  board: BoardRef;
  lists: List[];
  editable: boolean;
}) {
  const [lists, setLists] = useState(loaded);
  const [open, setOpen] = useState<Open>(null);
  const [problem, setProblem] = useState<string | null>(null);

  async function attempt(action: () => Promise<void>): Promise<boolean> {
    setProblem(null);
    try {
      await action();
      return true;
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
      return false;
    }
  }
  const change = (listId: number, edit: (list: List) => List) =>
    setLists((all) => all.map((l) => (l.id === listId ? edit(l) : l)));

  const addList = (name: string) =>
    attempt(async () => {
      const made = await createList(slug, board, name);
      setLists((all) => [...all, made]);
    });
  const addCard = (listId: number, title: string) =>
    attempt(async () => {
      const made = await createCard(slug, board, listId, title);
      change(listId, (l) => ({ ...l, cards: [...l.cards, made] }));
    });
  const rename = (listId: number, name: string) =>
    void attempt(async () => {
      const renamed = await renameList(slug, board, listId, name);
      change(listId, (l) => ({ ...l, name: renamed.name }));
    });

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {problem && (
        <p role="alert" className="mx-4 mt-3 rounded-md bg-surface px-3 py-2 text-sm text-danger">
          {problem}
        </p>
      )}
      <div className="flex min-h-0 flex-1 items-start gap-3 overflow-x-auto overflow-y-hidden px-4 pt-3 pb-[18px]">
        {lists.map((list) => (
          <ListColumn
            key={list.id}
            list={list}
            editable={editable}
            composing={open?.kind === "card" && open.listId === list.id}
            onCompose={(on) => setOpen(on ? { kind: "card", listId: list.id } : null)}
            onRename={(name) => rename(list.id, name)}
            onAddCard={(title) => addCard(list.id, title)}
          />
        ))}
        {editable &&
          (open?.kind === "list" ? (
            <div className="w-[288px] shrink-0 rounded-xl bg-[var(--tz-list-bg)] p-3">
              <Composer
                label={t("lists.listTitle")}
                placeholder={t("lists.listPlaceholder")}
                submit={t("lists.addListSubmit")}
                multiline={false}
                maxLength={100}
                onAdd={addList}
                onClose={() => setOpen(null)}
              />
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setOpen({ kind: "list" })}
              className="flex w-[288px] shrink-0 items-center gap-2 rounded-xl bg-white/30 p-3 text-left font-semibold text-white hover:bg-white/40"
            >
              <Icon name="plus" />
              {t("lists.addList")}
            </button>
          ))}
      </div>
    </div>
  );
}
