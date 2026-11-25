import { useEffect, useRef, useState, type SubmitEvent } from "react";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { deleteCompany, type CompanySummary } from "../api";

/**
 * Delete company (prototype dDelete): the short name must be typed before the
 * button works, and the server checks it again. The folder moves to trash for
 * 30 days (D35). Escape or Cancel closes it.
 */
export function DeleteCompanyDialog({
  company,
  onClose,
  onDeleted,
}: {
  company: CompanySummary;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => input.current?.focus(), []);

  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (typed !== company.slug) return;
    setBusy(true);
    setProblem(null);
    try {
      await deleteCompany(company.slug, typed);
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
      setBusy(false);
      return;
    }
    onDeleted();
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-company-title"
        onKeyDown={(e) => {
          if (e.key === "Escape") onClose();
        }}
        className="w-full max-w-md rounded-xl border border-line bg-surface p-6 shadow-lg"
      >
        <h2 id="delete-company-title" className="text-lg font-semibold">
          {t("admin.deleteAsk", { name: company.name })}
        </h2>
        <p className="mt-1 text-sm text-muted">{t("admin.deleteDialogLead")}</p>
        <form onSubmit={submit} className="mt-4 flex flex-col gap-4 text-sm">
          <label>
            <span>
              {t("admin.deleteConfirmBefore")} <b className="font-mono">{company.slug}</b>{" "}
              {t("admin.deleteConfirmAfter")}
            </span>
            <input
              ref={input}
              autoComplete="off"
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              className="mt-1 h-10 w-full rounded-md border border-line bg-surface px-3 font-mono"
            />
          </label>
          {problem && (
            <p role="alert" className="text-danger">
              {problem}
            </p>
          )}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="h-10 rounded-md border border-line px-4 font-semibold hover:bg-sunken"
            >
              {t("admin.cancel")}
            </button>
            <button
              type="submit"
              disabled={busy || typed !== company.slug}
              className="h-10 rounded-md bg-danger px-4 font-semibold text-white disabled:opacity-50"
            >
              {t("admin.deleteGo")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
