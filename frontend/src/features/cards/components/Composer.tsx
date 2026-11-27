import { useRef, useState } from "react";
import { t } from "@/shared/i18n";
import { Icon } from "@/shared/ui/Icon";

/**
 * The box under a list for a new card, and at the end of the board for a new
 * list (prototype .cmp and .addl.open). Enter adds and keeps the box open for
 * the next one; Escape or Cancel closes it. A blank title adds nothing.
 */
export function Composer({
  label,
  placeholder,
  submit,
  multiline,
  maxLength,
  onAdd,
  onClose,
}: {
  label: string;
  placeholder: string;
  submit: string;
  multiline: boolean;
  maxLength: number;
  onAdd: (title: string) => Promise<boolean>;
  onClose: () => void;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const box = useRef<HTMLInputElement & HTMLTextAreaElement>(null);

  async function add() {
    const title = text.trim();
    if (!title || busy) {
      box.current?.focus();
      return;
    }
    setBusy(true);
    const added = await onAdd(title);
    setBusy(false);
    if (added) setText("");
    box.current?.focus();
  }

  const Field = multiline ? "textarea" : "input";
  return (
    <div className="flex flex-col gap-2">
      <Field
        ref={box}
        // The box opens because its button was just clicked.
        autoFocus
        aria-label={label}
        placeholder={placeholder}
        maxLength={maxLength}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          // Enter while an input method is composing finishes the word, not the card.
          if (e.nativeEvent.isComposing) return;
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            void add();
          }
          if (e.key === "Escape") onClose();
        }}
        className={`w-full resize-none rounded-lg border border-accent bg-surface px-2.5 text-sm text-ink ${multiline ? "min-h-[60px] py-2" : "h-[34px]"}`}
      />
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => void add()}
          className="h-8 rounded-md bg-accent px-3 text-sm font-semibold text-white disabled:opacity-60"
        >
          {submit}
        </button>
        <button
          type="button"
          aria-label={t("lists.cancel")}
          onClick={onClose}
          className="grid size-8 place-items-center rounded-md text-muted hover:bg-sunken"
        >
          <Icon name="x" />
        </button>
      </div>
    </div>
  );
}
