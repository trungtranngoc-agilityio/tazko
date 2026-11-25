import { useEffect, useRef, useState, type SubmitEvent } from "react";
import type { Member } from "@/features/orgs";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { createProject, type Project } from "../api";

/** New project (prototype dialog on Manage projects): a name and its first
 * owner, chosen from the company's people. Escape or Cancel closes it. */
export function NewProjectDialog({
  slug,
  people,
  meId,
  onClose,
  onCreated,
}: {
  slug: string;
  people: Member[];
  meId: number;
  onClose: () => void;
  onCreated: (project: Project) => void;
}) {
  const [name, setName] = useState("");
  const [owner, setOwner] = useState<number>(meId);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const first = useRef<HTMLInputElement>(null);

  useEffect(() => first.current?.focus(), []);

  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setProblem(null);
    try {
      onCreated(await createProject(slug, name.trim(), owner));
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
        aria-labelledby="new-project-title"
        onKeyDown={(e) => {
          if (e.key === "Escape") onClose();
        }}
        className="w-full max-w-md rounded-xl border border-line bg-surface p-6 shadow-lg"
      >
        <h2 id="new-project-title" className="text-lg font-semibold">
          {t("manage.newTitle")}
        </h2>
        <p className="mt-1 text-sm text-muted">{t("manage.newLead")}</p>
        <form onSubmit={submit} className="mt-4 flex flex-col gap-4 text-sm">
          <label className="flex flex-col gap-1.5 font-semibold">
            {t("manage.name")}
            <input
              ref={first}
              required
              maxLength={100}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("manage.namePlaceholder")}
              className="h-10 rounded-md border border-line bg-surface px-3 font-normal"
            />
          </label>
          <label className="flex flex-col gap-1.5 font-semibold">
            {t("manage.firstOwner")}
            <select
              value={owner}
              onChange={(e) => setOwner(Number(e.target.value))}
              className="h-10 rounded-md border border-line bg-surface px-3 font-normal"
            >
              {people.map((p) => (
                <option key={p.user_id} value={p.user_id}>
                  {t("manage.personWithRole", {
                    name: p.name || p.email,
                    role: t(`role.${p.role}`).toLowerCase(),
                  })}
                </option>
              ))}
            </select>
          </label>
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
              {t("manage.cancel")}
            </button>
            <button
              type="submit"
              disabled={busy}
              className="h-10 rounded-md bg-accent px-4 font-semibold text-white disabled:opacity-60"
            >
              {t("manage.create")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
