import { useEffect, useRef, useState, type SubmitEvent } from "react";
import { invite } from "@/features/orgs";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { consoleCompanyBase, createCompany } from "../api";

/** The short name the prototype suggests from the company name. */
function suggest(name: string): string {
  return name
    .replace(/[đĐ]/g, "d") // no decomposition in Unicode, so NFKD keeps it
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40)
    .replace(/-+$/, "");
}

const field = "mt-1 h-10 w-full rounded-md border border-line bg-surface px-3";

/**
 * New company (prototype dNewCo): name, short name, first owner. Creates the
 * company, then invites the owner. The storage limit field waits for M1-07,
 * which brings company settings. Escape or Cancel closes it.
 */
export function NewCompanyDialog({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (slug: string, problem: string | null) => void;
}) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [owner, setOwner] = useState("");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const first = useRef<HTMLInputElement>(null);

  useEffect(() => first.current?.focus(), []);

  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) {
      setProblem(t("admin.nameNeeded"));
      return;
    }
    setBusy(true);
    setProblem(null);
    let made: string;
    try {
      made = (await createCompany(slug, name.trim())).slug;
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
      setBusy(false);
      return;
    }
    try {
      await invite(consoleCompanyBase(made), owner.trim(), "owner");
      onCreated(made, null);
    } catch (error) {
      const reason = errorText(error instanceof ApiError ? error.code : "UNKNOWN");
      onCreated(made, t("admin.inviteFailed", { reason }));
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="new-company-title"
        onKeyDown={(e) => {
          if (e.key === "Escape") onClose();
        }}
        className="w-full max-w-md rounded-xl border border-line bg-surface p-6 shadow-lg"
      >
        <h2 id="new-company-title" className="text-lg font-semibold">
          {t("admin.newCompany")}
        </h2>
        <p className="mt-1 text-sm text-muted">{t("admin.newCompanyLead")}</p>
        <form onSubmit={submit} className="mt-4 flex flex-col gap-4 text-sm">
          <label>
            <span className="font-semibold">{t("admin.companyName")}</span>
            <input
              ref={first}
              required
              maxLength={100}
              value={name}
              placeholder={t("admin.companyNamePlaceholder")}
              onChange={(e) => {
                setName(e.target.value);
                if (!slugTouched) setSlug(suggest(e.target.value));
              }}
              className={field}
            />
          </label>
          <label>
            <span className="font-semibold">{t("admin.slug")}</span>
            <input
              required
              pattern="[a-z0-9](?:[a-z0-9\-]{0,38}[a-z0-9])?"
              maxLength={40}
              value={slug}
              onChange={(e) => {
                setSlugTouched(true);
                setSlug(e.target.value);
              }}
              className={`${field} font-mono`}
            />
            <span className="mt-1 block text-xs text-muted">{t("admin.slugHelp")}</span>
          </label>
          <label>
            <span className="font-semibold">{t("admin.ownerEmail")}</span>
            <input
              type="email"
              required
              value={owner}
              placeholder={t("invite.placeholder")}
              onChange={(e) => setOwner(e.target.value)}
              className={field}
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
              disabled={busy}
              className="h-10 rounded-md bg-accent px-4 font-semibold text-white disabled:opacity-60"
            >
              {t("admin.create")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
