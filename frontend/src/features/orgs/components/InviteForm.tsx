import { useState, type SubmitEvent } from "react";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { Icon } from "@/shared/ui/Icon";
import { invite, type Invite, type Role } from "../api";

/** "Invite someone": email and role. Email delivery comes with M6, so the
 * owner is told to share the site address themselves. */
export function InviteForm({
  base,
  onInvited,
}: {
  base: string;
  onInvited: (invite: Invite) => void;
}) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("member");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setProblem(null);
    setDone(null);
    try {
      const made = await invite(base, email.trim(), role);
      setDone(t("invite.done", { email: made.email, url: window.location.origin }));
      setEmail("");
      onInvited(made);
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-xl border border-line bg-surface p-5">
      <h2 className="text-lg font-semibold">{t("invite.title")}</h2>
      <form onSubmit={submit} className="mt-3 flex flex-wrap items-center gap-3">
        <label className="min-w-64 flex-1">
          <span className="sr-only">{t("invite.email")}</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={t("invite.placeholder")}
            className="h-10 w-full rounded-md border border-line bg-surface px-3"
          />
        </label>
        <label>
          <span className="sr-only">{t("invite.role")}</span>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as Role)}
            className="h-10 rounded-md border border-line bg-surface px-3"
          >
            <option value="member">{t("role.member")}</option>
            <option value="owner">{t("role.owner")}</option>
          </select>
        </label>
        <button
          type="submit"
          disabled={busy}
          className="flex h-10 items-center gap-2 rounded-md bg-accent px-4 font-semibold text-white disabled:opacity-60"
        >
          <Icon name="plus" />
          {t("invite.submit")}
        </button>
      </form>
      <p className="mt-3 max-w-xl text-sm text-muted">{t("invite.help")}</p>
      {problem && (
        <p role="alert" className="mt-3 text-sm text-danger">
          {problem}
        </p>
      )}
      {done && (
        <p role="status" className="mt-3 text-sm text-success">
          {done}
        </p>
      )}
    </section>
  );
}
