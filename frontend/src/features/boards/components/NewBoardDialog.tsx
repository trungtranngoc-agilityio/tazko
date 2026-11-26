import { useEffect, useRef, useState, type SubmitEvent } from "react";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { BOARD_BACKGROUNDS } from "@/shared/lib/backgrounds";
import { createBoard, type Board } from "../api";

/** Create board (prototype dialog on a project's Boards): a title and a
 * background, the project's default picked first. Escape or Cancel closes it. */
export function NewBoardDialog({
  slug,
  projectId,
  background,
  onClose,
  onCreated,
}: {
  slug: string;
  projectId: number;
  background: string | null;
  onClose: () => void;
  onCreated: (board: Board) => void;
}) {
  const [name, setName] = useState("");
  const [picked, setPicked] = useState<string | null>(background);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const first = useRef<HTMLInputElement>(null);

  useEffect(() => first.current?.focus(), []);

  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setProblem(null);
    try {
      onCreated(await createBoard(slug, projectId, name.trim(), picked));
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="new-board-title"
        onKeyDown={(e) => {
          if (e.key === "Escape") onClose();
        }}
        className="w-full max-w-md rounded-xl border border-line bg-surface p-6 shadow-lg"
      >
        <h2 id="new-board-title" className="text-lg font-semibold">
          {t("boards.newTitle")}
        </h2>
        <form onSubmit={submit} className="mt-4 flex flex-col gap-4 text-sm">
          <label className="flex flex-col gap-1.5 font-semibold">
            {t("boards.name")}
            <input
              ref={first}
              required
              maxLength={100}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("boards.namePlaceholder")}
              className="h-10 rounded-md border border-line bg-surface px-3 font-normal"
            />
          </label>
          <fieldset className="flex flex-col gap-1.5">
            <legend className="mb-1.5 font-semibold">{t("boards.background")}</legend>
            <div className="flex flex-wrap gap-2">
              {BOARD_BACKGROUNDS.map((key) => (
                <button
                  key={key}
                  type="button"
                  aria-label={t("psettings.backgroundOption", { key })}
                  aria-pressed={picked === key}
                  onClick={() => setPicked(key)}
                  className={`board-bg-${key} h-9 w-11 rounded-md border-2 ${picked === key ? "border-accent" : "border-transparent"}`}
                />
              ))}
            </div>
          </fieldset>
          {problem && (
            <p role="alert" className="text-danger">
              {problem}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="h-10 rounded-md border border-line px-4 font-semibold hover:bg-sunken"
            >
              {t("boards.cancel")}
            </button>
            <button
              type="submit"
              disabled={busy}
              className="h-10 rounded-md bg-accent px-4 font-semibold text-white disabled:opacity-60"
            >
              {t("boards.create")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
