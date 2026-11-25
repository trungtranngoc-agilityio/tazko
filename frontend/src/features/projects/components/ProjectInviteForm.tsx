import { useState, type SubmitEvent } from "react";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { Icon } from "@/shared/ui/Icon";
import { inviteToProject, type ProjectInvite, type ProjectRole } from "../api";

/** "Invite to this project" (prototype Project members): email and project
 * role. No email is sent yet, so the person inviting is told to share the
 * site address. Someone new joins the company as a plain member. */
export function ProjectInviteForm({
  slug,
  projectId,
  company,
  roles,
  onInvited,
}: {
  slug: string;
  projectId: number;
  company: string;
  roles: ProjectRole[];
  onInvited: (invite: ProjectInvite) => void;
}) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<ProjectRole>(roles[0] ?? "member");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  async function submit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setProblem(null);
    setDone(null);
    try {
      const made = await inviteToProject(slug, projectId, email.trim(), role);
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
      <h2 className="text-lg font-semibold">{t("pinvite.title")}</h2>
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
            onChange={(e) => setRole(e.target.value as ProjectRole)}
            className="h-10 rounded-md border border-line bg-surface px-3"
          >
            {roles.map((r) => (
              <option key={r} value={r}>
                {t(`projectRole.${r}`)}
              </option>
            ))}
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
      <p className="mt-3 max-w-xl text-sm text-muted">{t("pinvite.help", { company })}</p>
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
