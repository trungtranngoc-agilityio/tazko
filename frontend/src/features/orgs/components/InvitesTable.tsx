import { useState } from "react";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { when } from "@/shared/lib/when";
import { revokeInvite, type Invite } from "../api";
import { AccountBadge } from "./AccountBadge";

/** Invites nobody has used yet, newest first, with Revoke. */
export function InvitesTable({
  slug,
  invites,
  onChanged,
}: {
  slug: string;
  invites: Invite[];
  onChanged: () => void;
}) {
  const [problem, setProblem] = useState<string | null>(null);

  async function revoke(invite: Invite) {
    setProblem(null);
    try {
      await revokeInvite(slug, invite.id);
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
    }
    onChanged();
  }

  return (
    <section className="rounded-xl border border-line bg-surface">
      <h2 className="px-5 pt-5 text-lg font-semibold">
        {t("invites.title")} <span className="font-normal text-muted">({invites.length})</span>
      </h2>
      {problem && (
        <p role="alert" className="px-5 pt-2 text-sm text-danger">
          {problem}
        </p>
      )}
      {invites.length === 0 ? (
        <p className="px-5 py-4 text-sm text-muted">{t("invites.none")}</p>
      ) : (
        <table aria-label={t("invites.title")} className="mt-3 w-full text-sm">
          <thead className="bg-sunken text-left text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-5 py-2 font-semibold">{t("invites.email")}</th>
              <th className="px-3 py-2 font-semibold">{t("members.account")}</th>
              <th className="px-3 py-2 font-semibold">{t("members.role")}</th>
              <th className="px-3 py-2 font-semibold">{t("invites.invitedBy")}</th>
              <th className="px-3 py-2 font-semibold">{t("invites.date")}</th>
              <th className="px-3 py-2">
                <span className="sr-only">{t("invites.revoke")}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {invites.map((invite) => (
              <tr key={invite.id} className="border-t border-line">
                <td className="px-5 py-3">{invite.email}</td>
                <td className="px-3">
                  <AccountBadge account={invite.account} />
                </td>
                <td className="px-3">
                  <span className="rounded-full bg-sunken px-2 py-0.5 text-xs">
                    {t(`role.${invite.role}`)}
                  </span>
                </td>
                <td className="px-3 text-muted">{invite.invited_by ?? ""}</td>
                <td className="px-3 text-muted">{when(invite.created_at)}</td>
                <td className="px-3">
                  <button
                    type="button"
                    aria-label={t("invites.revokeOf", { email: invite.email })}
                    onClick={() => void revoke(invite)}
                    className="h-8 rounded-md border border-line px-3 hover:bg-sunken"
                  >
                    {t("invites.revoke")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
