/** One of the prototype's five avatar tones, picked from the name the same way
 * (tone() in design/tazko-prototype.html), so a person keeps their colour. */
function tone(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  return `c${hash % 5}`;
}

/** First letters of the first and last words, as the prototype writes them. */
function letters(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  const first = words[0]?.[0] ?? "?";
  const last = words.length > 1 ? (words[words.length - 1]?.[0] ?? "") : "";
  return (first + last).toUpperCase();
}

const SIZES = {
  md: "size-7 rounded-full text-[0.7rem]",
  lg: "size-8 rounded-md text-xs",
  xl: "size-11 rounded-lg text-base",
} as const;

/** The initials badge the prototype uses for people (round) and companies
 * (square: lg and xl). Colours are --tz-c0..c4 in app/styles/index.css. */
export function Initials({ name, size = "md" }: { name: string; size?: keyof typeof SIZES }) {
  const t = tone(name);
  return (
    <span
      aria-hidden="true"
      data-tone={t}
      style={{ background: `var(--tz-${t}-bg)`, color: `var(--tz-${t}-fg)` }}
      className={`grid shrink-0 place-items-center font-bold ${SIZES[size]}`}
    >
      {letters(name)}
    </span>
  );
}
