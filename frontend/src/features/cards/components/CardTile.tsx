import type { Card } from "../api";

/** A card on its list (prototype .cd): the title for now; cover, labels,
 * people and dates join it with the card dialog. */
export function CardTile({ card }: { card: Card }) {
  return (
    <article
      aria-label={card.title}
      className="shrink-0 rounded-[9px] border border-transparent bg-surface px-2.5 py-2 text-[0.9rem] leading-snug [overflow-wrap:anywhere] shadow-[var(--tz-list-shadow)]"
    >
      {card.title}
    </article>
  );
}
