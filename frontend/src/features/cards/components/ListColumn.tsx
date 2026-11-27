import { useState } from "react";
import { t } from "@/shared/i18n";
import { Icon } from "@/shared/ui/Icon";
import type { List } from "../api";
import { CardTile } from "./CardTile";

/** One list on the board (prototype .ls): its name, card count, collapse and
 * the card tiles. Collapsing stays on this page only. */
export function ListColumn({ list }: { list: List }) {
  const [collapsed, setCollapsed] = useState(false);
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
        <h2 className="min-w-0 flex-1 px-1 text-[0.92rem] font-bold [overflow-wrap:anywhere]">
          {list.name}
        </h2>
        <span className="text-xs font-semibold text-muted">{count}</span>
        <button
          type="button"
          aria-label={t("lists.collapse")}
          onClick={() => setCollapsed(true)}
          className="grid size-7 place-items-center rounded-md text-muted hover:bg-sunken"
        >
          <Icon name="chev" className="size-4" />
        </button>
      </header>
      <div className="flex min-h-2.5 flex-col gap-2 overflow-y-auto px-2 pt-0.5 pb-2">
        {list.cards.map((card) => (
          <CardTile key={card.id} card={card} />
        ))}
        {count === 0 && (
          <p className="px-2 py-3.5 text-center text-[0.82rem] text-muted">{t("lists.noCards")}</p>
        )}
      </div>
    </section>
  );
}
