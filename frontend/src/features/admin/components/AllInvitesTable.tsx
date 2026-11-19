import { useState } from "react";
import { AccountBadge } from "@/features/orgs";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { when } from "@/shared/lib/when";
import { revokeAnyInvite, type AnyInvite } from "../api";
import { box, tableHead } from "./parts";

/** Invites page (prototype admin-invites): every pending invite, with its company. */
export function AllInvitesTable({
  invites,
  onChanged,
}: {
  invites: AnyInvite[];
  onChanged: () => void;
}) {
  const [problem, setProblem] = useState<string | null>(null);

  async function revoke(invite: AnyInvite) {
    setProblem(null);
    try {
      await revokeAnyInvite(invite.id);
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
    }
    onChanged(); // show the list as it is now, also when someone used it meanwhile
  }

  if (invites.length === 0) {
    return (
      <div className="py-12 text-center">
        <h2 className="text-lg font-semibold">{t("admin.noInvites")}</h2>
        {problem && (
          <p role="alert" className="mt-2 text-sm text-danger">
            {problem}
          </p>
        )}
      </div>
    );
  }
  return (
    <>
      {problem && (
        <p role="alert" className="mb-3 text-sm text-danger">
          {problem}
        </p>
      )}
      <div className={box}>
        <table aria-label={t("admin.invites")} className="w-full text-sm">
          <thead className={tableHead}>
            <tr>
              <th className="px-5 py-2 font-semibold">{t("invites.email")}</th>
              <th className="px-3 py-2 font-semibold">{t("members.account")}</th>
              <th className="px-3 py-2 font-semibold">{t("admin.company")}</th>
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
                <td className="px-3">{invite.company.name}</td>
                <td className="px-3">
                  <span className="rounded-full bg-sunken px-2 py-0.5 text-xs">
                    {t(`role.${invite.role}`)}
                  </span>
                </td>
                <td className="px-3 text-muted">{invite.invited_by ?? ""}</td>
                <td className="px-3 text-muted">{when(invite.created_at, { dateOnly: true })}</td>
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
      </div>
    </>
  );
}
