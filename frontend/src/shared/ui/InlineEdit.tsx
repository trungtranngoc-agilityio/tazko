import { useRef, useState, type ElementType } from "react";

/**
 * A heading that turns into a text box when clicked (prototype inl(): board
 * and list names). Enter or leaving the box saves, Escape cancels; a blank
 * or unchanged name saves nothing. Not editable, it is the plain heading.
 */
export function InlineEdit({
  as: Tag,
  value,
  label,
  title,
  editable,
  maxLength,
  className = "",
  inputClassName = "",
  onSave,
}: {
  as: ElementType;
  value: string;
  label: string;
  title: string;
  editable: boolean;
  maxLength: number;
  className?: string;
  inputClassName?: string;
  onSave: (value: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  // Enter saves and unmounts the box, which blurs it: save only once.
  const finished = useRef(false);

  function start() {
    finished.current = false;
    setDraft(value);
    setEditing(true);
  }
  function finish(save: boolean) {
    if (finished.current) return;
    finished.current = true;
    setEditing(false);
    const next = draft.trim();
    if (save && next && next !== value) onSave(next);
  }

  if (editing) {
    return (
      <input
        // The box replaces what was just clicked, so focus moves into it.
        autoFocus
        aria-label={label}
        value={draft}
        maxLength={maxLength}
        onChange={(e) => setDraft(e.target.value)}
        onFocus={(e) => e.target.select()}
        onKeyDown={(e) => {
          // Enter while an input method is composing finishes the word, not the name.
          if (e.nativeEvent.isComposing) return;
          if (e.key === "Enter") {
            e.preventDefault();
            finish(true);
          }
          if (e.key === "Escape") finish(false);
        }}
        onBlur={() => finish(true)}
        className={`min-w-0 rounded-md border border-accent bg-surface px-2 text-ink ${inputClassName}`}
      />
    );
  }
  return (
    <Tag className={className}>
      {editable ? (
        <button
          type="button"
          title={title}
          onClick={start}
          className="max-w-full rounded-md px-1 text-left [overflow-wrap:anywhere] hover:bg-black/10"
        >
          {value}
        </button>
      ) : (
        <span className="px-1 [overflow-wrap:anywhere]">{value}</span>
      )}
    </Tag>
  );
}
