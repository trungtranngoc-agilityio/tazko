import { useEffect, useRef } from "react";

/**
 * A short note at the bottom of the window (prototype .toast2), with Undo
 * when the change can be taken back. It leaves by itself, later when it
 * offers Undo so there is time to press it. Give each note its own `key`.
 */
export function Toast({
  message,
  undoLabel,
  onUndo,
  onDone,
}: {
  message: string;
  undoLabel?: string;
  onUndo?: () => void;
  onDone: () => void;
}) {
  const done = useRef(onDone);
  done.current = onDone;
  const undoable = onUndo !== undefined;

  useEffect(() => {
    const timer = setTimeout(() => done.current(), undoable ? 6000 : 2800);
    return () => clearTimeout(timer);
  }, [undoable]);

  return (
    <div
      role="status"
      className="fixed bottom-5 left-1/2 z-[90] flex max-w-[calc(100%-24px)] -translate-x-1/2 items-center gap-3.5 rounded-[10px] bg-ink px-3.5 py-2.5 font-medium text-bg shadow-lg"
    >
      <span>{message}</span>
      {onUndo && (
        <button
          type="button"
          onClick={onUndo}
          className="font-bold text-accent brightness-[1.4] hover:underline"
        >
          {undoLabel}
        </button>
      )}
    </div>
  );
}
