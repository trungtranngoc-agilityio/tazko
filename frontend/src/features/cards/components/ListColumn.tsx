import { useState } from "react";
import { t } from "@/shared/i18n";
import { Icon } from "@/shared/ui/Icon";
import { InlineEdit } from "@/shared/ui/InlineEdit";
import { Popover } from "@/shared/ui/Popover";
import type { List } from "../api";
import { CardTile } from "./CardTile";
import { Composer } from "./Composer";

/** One list on the board (prototype .ls): its name, card count, collapse,
 * the list menu, the card tiles and Add a card. Collapsing stays on this
 * page only. */
export function ListColumn({
  list,
  editable,
  composing,
  onCompose,
  onRename,
  onAddCard,
  onArchive,
}: {
  list: List;
  editable: boolean;
  composing: boolean;
  onCompose: (open: boolean) => void;
  onRename: (name: string) => void;
  onAddCard: (title: string) => Promise<boolean>;
  onArchive: () => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [menu, setMenu] = useState(false);
  const count = list.cards.length;

  if (collapsed) {
    return (
      <section
        aria-label={list.name}
        className="flex w-[46px] shrink-0 flex-col items-center rounded-xl bg-[var(--tz-list-bg)] py-2 shadow-[var(--tz-list-shadow)]"
      >
        <button
          type="button"
          aria-label={t("lists.expand", { name: list.name })}
          onClick={() => setCollapsed(false)}
          className="p-1.5 font-bold text-ink [writing-mode:vertical-rl]"
        >
          {t("lists.collapsed", { name: list.name, count })}
        </button>
      </section>
    );
  }
  return (
    <section
      aria-label={list.name}
      className="flex max-h-full w-[288px] shrink-0 flex-col rounded-xl bg-[var(--tz-list-bg)] text-ink shadow-[var(--tz-list-shadow)]"
    >
      <header className="flex items-center gap-1 py-2 pr-1.5 pl-3">
        <InlineEdit
          as="h2"
          value={list.name}
          label={t("lists.renameLabel")}
          title={t("lists.rename")}
          editable={editable}
          maxLength={100}
          onSave={onRename}
          className="min-w-0 flex-1 text-[0.92rem] font-bold"
          inputClassName="h-8 flex-1 text-[0.92rem]"
        />
        <span className="text-xs font-semibold text-muted">{count}</span>
        <button
          type="button"
          aria-label={t("lists.collapse")}
          onClick={() => setCollapsed(true)}
          className="grid size-7 place-items-center rounded-md text-muted hover:bg-sunken"
        >
          <Icon name="chev" className="size-4" />
        </button>
        {editable && (
          <span className="relative">
            <button
              type="button"
              aria-label={t("lists.actions")}
              aria-expanded={menu}
              onClick={() => setMenu(!menu)}
              className="grid size-7 place-items-center rounded-md text-muted hover:bg-sunken"
            >
              <Icon name="more" className="size-4" />
            </button>
            {menu && (
              <Popover
                title={t("lists.actions")}
                closeLabel={t("lists.closeActions")}
                onClose={() => setMenu(false)}
                className="right-0 w-[290px]"
              >
                <button
                  type="button"
                  data-first
                  onClick={() => {
                    setMenu(false);
                    onArchive();
                  }}
                  className="flex w-full items-center gap-2.5 rounded-lg px-2 py-[7px] text-left text-danger hover:bg-sunken"
                >
                  <Icon name="archive" />
                  {t("lists.archive")}
                </button>
              </Popover>
            )}
          </span>
        )}
      </header>
      <div
        className={`flex min-h-2.5 flex-col gap-2 overflow-y-auto px-2 pt-0.5 ${editable ? "pb-1" : "pb-2"}`}
      >
        {list.cards.map((card) => (
          <CardTile key={card.id} card={card} />
        ))}
        {count === 0 && (
          <p className="px-2 py-3.5 text-center text-[0.82rem] text-muted">{t("lists.noCards")}</p>
        )}
      </div>
      {editable && (
        <div className="px-2 pt-1 pb-2">
          {composing ? (
            <Composer
              label={t("lists.cardTitle")}
              placeholder={t("lists.cardPlaceholder")}
              submit={t("lists.addCardSubmit")}
              multiline
              maxLength={512}
              onAdd={onAddCard}
              onClose={() => onCompose(false)}
            />
          ) : (
            <button
              type="button"
              onClick={() => onCompose(true)}
              className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left font-medium text-muted hover:bg-sunken hover:text-ink"
            >
              <Icon name="plus" />
              {t("lists.addCard")}
            </button>
          )}
        </div>
      )}
    </section>
  );
}
