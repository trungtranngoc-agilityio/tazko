import { useEffect, useRef } from "react";
import { t } from "@/shared/i18n";
import { Icon } from "@/shared/ui/Icon";

/**
 * The board menu (prototype drawer), on the right under the top bar. For now
 * it holds Close board, for owners and members (the parent shows the menu only
 * to them). Escape closes it.
 */
export function BoardMenu({
  onCloseBoard,
  onClose,
}: {
  onCloseBoard: () => void;
  onClose: () => void;
}) {
  const first = useRef<HTMLButtonElement>(null);
  useEffect(() => first.current?.focus(), []);

  const item =
    "flex w-full items-center gap-2.5 rounded-lg px-2 py-[7px] text-left hover:bg-sunken";
  return (
    <aside
      aria-label={t("board.menu")}
      onKeyDown={(event) => {
        if (event.key === "Escape") onClose();
      }}
      className="fixed top-[46px] right-0 bottom-0 z-40 flex w-[min(360px,100%)] flex-col border-l border-line bg-surface text-ink shadow-lg"
    >
      <header className="flex items-center border-b border-line py-2 pr-2 pl-4">
        <h2 className="flex-1 font-bold">{t("board.menu")}</h2>
        <button
          ref={first}
          type="button"
          aria-label={t("board.closeMenu")}
          onClick={onClose}
          className="grid size-8 place-items-center rounded-md text-muted hover:bg-sunken"
        >
          <Icon name="x" />
        </button>
      </header>
      <div className="flex flex-col p-2.5 text-sm">
        <button type="button" onClick={onCloseBoard} className={`${item} text-danger`}>
          <Icon name="archive" />
          {t("board.close")}
        </button>
      </div>
    </aside>
  );
}
