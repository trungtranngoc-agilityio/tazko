/** An on/off switch (prototype People page and project settings). */
export function Switch({
  on,
  label,
  onToggle,
  disabled = false,
}: {
  on: boolean;
  label: string;
  onToggle: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      disabled={disabled}
      onClick={onToggle}
      className={`relative h-5 w-9 shrink-0 rounded-full transition-colors disabled:opacity-50 ${on ? "bg-accent" : "bg-line"}`}
    >
      <span
        aria-hidden="true"
        className={`absolute top-0.5 size-4 rounded-full bg-white shadow transition-[left] ${on ? "left-[1.125rem]" : "left-0.5"}`}
      />
    </button>
  );
}
