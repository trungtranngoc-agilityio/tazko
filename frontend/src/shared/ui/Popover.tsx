import { useEffect, useRef, type ReactNode } from "react";
import { Icon } from "./Icon";

/**
 * A small panel under the button that opened it (prototype .pop): a title,
 * a close button and its body. Escape, the close button or a press outside
 * the panel and its button closes it. The parent element holds both the
 * button and the panel, so pressing the button again toggles it closed.
 */
export function Popover({
  title,
  closeLabel,
  onClose,
  className = "",
  children,
}: {
  title: string;
  closeLabel: string;
  onClose: () => void;
  className?: string;
  children: ReactNode;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  close.current = onClose;

  useEffect(() => {
    const anchor = panel.current?.parentElement;
    const away = (event: PointerEvent) => {
      if (anchor && !anchor.contains(event.target as Node)) close.current();
    };
    // On the document: a control disabled while it saves drops the focus to
    // the page, and Escape must still close the panel then. Escape in a field
    // outside the panel belongs to that field.
    const escape = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      const field = target.isContentEditable || ["INPUT", "TEXTAREA"].includes(target.tagName);
      if (event.key !== "Escape" || event.defaultPrevented) return;
      if (field && !panel.current?.contains(target)) return;
      close.current();
    };
    document.addEventListener("pointerdown", away);
    document.addEventListener("keydown", escape);
    const first = (selector: string) => panel.current?.querySelector<HTMLElement>(selector);
    (first("[data-first]") ?? first("button"))?.focus();
    return () => {
      document.removeEventListener("pointerdown", away);
      document.removeEventListener("keydown", escape);
    };
  }, []);

  return (
    <div
      ref={panel}
      role="dialog"
      aria-label={title}
      className={`absolute top-full z-40 mt-1.5 flex max-h-[calc(100vh-120px)] w-80 max-w-[calc(100vw-16px)] flex-col rounded-xl border border-line bg-surface text-ink shadow-lg ${className}`}
    >
      <header className="flex items-center border-b border-line py-1.5 pr-1.5 pl-3.5">
        <b className="flex-1 text-[0.9rem]">{title}</b>
        <button
          type="button"
          aria-label={closeLabel}
          onClick={onClose}
          className="grid size-7 place-items-center rounded-md text-muted hover:bg-sunken"
        >
          <Icon name="x" className="size-4" />
        </button>
      </header>
      <div className="overflow-y-auto p-2.5 text-sm">{children}</div>
    </div>
  );
}
