/** The round initials badge the prototype uses for people and companies. */
export function Initials({ name, size = "md" }: { name: string; size?: "md" | "lg" }) {
  const letters =
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((word) => word[0]?.toUpperCase())
      .join("") || "?";
  const box = size === "lg" ? "size-8 rounded-md text-xs" : "size-7 rounded-full text-[0.7rem]";
  return (
    <span
      aria-hidden="true"
      className={`grid shrink-0 place-items-center bg-warning/20 font-semibold text-ink ${box}`}
    >
      {letters}
    </span>
  );
}
