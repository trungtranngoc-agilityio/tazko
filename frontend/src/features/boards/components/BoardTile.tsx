import { t } from "@/shared/i18n";
import { Icon } from "@/shared/ui/Icon";
import type { Board } from "../api";

/** One board (prototype .btile): its background, name, a restricted mark,
 * the open lists and cards, and a personal star. */
export function BoardTile({ board, onStar }: { board: Board; onStar: (on: boolean) => void }) {
  const lists = t(board.lists === 1 ? "boards.list" : "boards.lists", { count: board.lists });
  const cards = t(board.cards === 1 ? "boards.card" : "boards.cards", { count: board.cards });
  const counts = t("boards.counts", { lists, cards });
  return (
    <article
      aria-label={board.name}
      className={`board-bg-${board.background ?? "dusk"} group relative flex h-[104px] min-w-0 flex-col justify-between overflow-hidden rounded-xl p-3 text-white`}
    >
      <span
        aria-hidden="true"
        className="absolute inset-0 bg-gradient-to-b from-black/10 to-black/35"
      />
      <b className="relative pr-8 break-words [text-shadow:0_1px_2px_rgb(0_0_0/0.3)]">
        {board.name}
      </b>
      <small className="relative flex items-center gap-1 opacity-90">
        {board.restricted && <Icon name="lock" className="size-3.5" />}
        {board.restricted ? t("boards.restrictedCounts", { counts }) : counts}
      </small>
      <button
        type="button"
        aria-label={t("boards.star")}
        aria-pressed={board.starred}
        onClick={() => onStar(!board.starred)}
        className={`absolute top-2 right-2 grid size-7 place-items-center rounded-md bg-black/25 group-hover:opacity-100 focus-visible:opacity-100 ${board.starred ? "opacity-100 [&_svg]:fill-amber-400 [&_svg]:stroke-amber-400" : "opacity-0"}`}
      >
        <Icon name="star" className="size-4" />
      </button>
    </article>
  );
}
