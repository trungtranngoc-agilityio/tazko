import { useState } from "react";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { when } from "@/shared/lib/when";
import { changeRole, removeMember, type Member, type Role } from "../api";
import { AccountBadge } from "./AccountBadge";
import { Initials } from "./Initials";

interface Props {
  slug: string;
  company: string;
  members: Member[];
  meId: number;
  onChanged: () => void;
  onLeft: () => void;
  onSelfDemoted: () => void;
}

/** Members with role and Remove. Every removal is confirmed (KNOWN-DEVIATIONS #5),
 * and so is making yourself a member; the server refuses to drop the last owner
 * and the reason is shown. */
export function MembersTable(props: Props) {
  const { slug, company, members, meId, onChanged, onLeft, onSelfDemoted } = props;
  const [problem, setProblem] = useState<string | null>(null);

  async function act(run: () => Promise<unknown>, after: () => void) {
    setProblem(null);
    try {
      await run();
      after();
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
      onChanged(); // show the role the server kept
    }
  }

  function remove(member: Member) {
    const me = member.user_id === meId;
    const question = me
      ? t("members.confirmLeave", { company })
      : t("members.confirmRemove", { name: member.name || member.email, company });
    if (!window.confirm(question)) return;
    void act(() => removeMember(slug, member.user_id), me ? onLeft : onChanged);
  }

  function setRole(member: Member, role: Role) {
    const demotingMe = member.user_id === meId && role === "member";
    if (demotingMe && !window.confirm(t("members.confirmDemote", { company }))) return;
    void act(() => changeRole(slug, member.user_id, role), demotingMe ? onSelfDemoted : onChanged);
  }

  return (
    <section className="rounded-xl border border-line bg-surface">
      <h2 className="px-5 pt-5 text-lg font-semibold">
        {t("members.title")} <span className="font-normal text-muted">({members.length})</span>
      </h2>
      {problem && (
        <p role="alert" className="px-5 pt-2 text-sm text-danger">
          {problem}
        </p>
      )}
      <table aria-label={t("members.title")} className="mt-3 w-full text-sm">
        <thead className="bg-sunken text-left text-xs uppercase tracking-wide text-muted">
          <tr>
            <th className="px-5 py-2 font-semibold">{t("members.person")}</th>
            <th className="px-3 py-2 font-semibold">{t("members.account")}</th>
            <th className="px-3 py-2 font-semibold">{t("members.role")}</th>
            <th className="px-3 py-2 font-semibold">{t("members.lastSeen")}</th>
            <th className="px-3 py-2">
              <span className="sr-only">{t("members.remove")}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {members.map((member) => {
            const label = member.name || member.email;
            return (
              <tr key={member.user_id} className="border-t border-line">
                <td className="px-5 py-2.5">
                  <span className="flex items-center gap-3">
                    <Initials name={label} />
                    <span>
                      <span className="block font-semibold">{member.name}</span>
                      <span className="block text-xs text-muted">{member.email}</span>
                    </span>
                  </span>
                </td>
                <td className="px-3">
                  <AccountBadge account={member.account} />
                </td>
                <td className="px-3">
                  <select
                    aria-label={t("members.roleOf", { name: label })}
                    value={member.role}
                    onChange={(e) => setRole(member, e.target.value as Role)}
                    className="h-9 rounded-md border border-line bg-surface px-2"
                  >
                    <option value="owner">{t("role.owner")}</option>
                    <option value="member">{t("role.member")}</option>
                  </select>
                </td>
                <td className="px-3 text-muted">
                  {member.last_seen_at ? when(member.last_seen_at) : t("members.never")}
                </td>
                <td className="px-3">
                  <button
                    type="button"
                    aria-label={t("members.removeOf", { name: label })}
                    onClick={() => remove(member)}
                    className="text-muted hover:text-danger"
                  >
                    × {t("members.remove")}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
