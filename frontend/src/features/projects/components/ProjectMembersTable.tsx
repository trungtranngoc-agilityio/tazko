import { useState } from "react";
import { AccountBadge, Initials } from "@/features/orgs";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { when } from "@/shared/lib/when";
import { Icon } from "@/shared/ui/Icon";
import { removeProjectMember, setProjectRole, type ProjectMember, type ProjectRole } from "../api";

const ROLES: ProjectRole[] = ["owner", "member", "observer"];

interface Props {
  slug: string;
  projectId: number;
  project: string;
  members: ProjectMember[];
  meId: number;
  /** Project owners change roles and remove people. */
  manages: boolean;
  /** Account and last sign-in: project and company owners only (the API sends none to others). */
  details: boolean;
  onChanged: () => void;
  onLeft: () => void;
}

/** The project's people (prototype Project members). Owners change roles and
 * remove people; everyone sees the roles and may leave. Removing, leaving and
 * giving up your own ownership ask first; the server keeps the last owner and
 * the reason is shown. */
export function ProjectMembersTable(props: Props) {
  const { slug, projectId, project, members, meId, onChanged, onLeft } = props;
  const [problem, setProblem] = useState<string | null>(null);

  async function act(run: () => Promise<unknown>, after: () => void) {
    setProblem(null);
    try {
      await run();
      after();
    } catch (error) {
      const code = error instanceof ApiError ? error.code : "UNKNOWN";
      // The code is shared with companies; say it about the project here.
      setProblem(code === "LAST_OWNER" ? t("pmembers.lastOwner") : errorText(code));
      onChanged(); // show the role the server kept
    }
  }

  function remove(member: ProjectMember) {
    const me = member.user_id === meId;
    const question = me
      ? t("pmembers.confirmLeave", { project })
      : t("pmembers.confirmRemove", { name: member.name || member.email, project });
    if (!window.confirm(question)) return;
    void act(() => removeProjectMember(slug, projectId, member.user_id), me ? onLeft : onChanged);
  }

  function setRole(member: ProjectMember, role: ProjectRole) {
    const givingUp = member.user_id === meId && member.role === "owner" && role !== "owner";
    if (givingUp && !window.confirm(t("pmembers.confirmDemote", { project }))) return;
    void act(() => setProjectRole(slug, projectId, member.user_id, role), onChanged);
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
            {props.details && <th className="px-3 py-2 font-semibold">{t("members.account")}</th>}
            <th className="px-3 py-2 font-semibold">{t("members.role")}</th>
            {props.details && (
              <th className="px-3 py-2 font-semibold">{t("pmembers.lastActive")}</th>
            )}
            <th className="px-3 py-2">
              <span className="sr-only">{t("members.remove")}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {members.map((member) => (
            <MemberRow
              key={member.user_id}
              member={member}
              me={member.user_id === meId}
              manages={props.manages}
              details={props.details}
              onRole={(role) => setRole(member, role)}
              onRemove={() => remove(member)}
            />
          ))}
        </tbody>
      </table>
    </section>
  );
}

function MemberRow({
  member,
  me,
  manages,
  details,
  onRole,
  onRemove,
}: {
  member: ProjectMember;
  me: boolean;
  manages: boolean;
  details: boolean;
  onRole: (role: ProjectRole) => void;
  onRemove: () => void;
}) {
  const label = member.name || member.email;
  return (
    <tr className="border-t border-line">
      <td className="px-5 py-2.5">
        <span className="flex items-center gap-3">
          <Initials name={label} />
          <span className="min-w-0">
            <span className="block truncate font-semibold">
              {me ? t("pmembers.you", { name: label }) : member.name}
            </span>
            <span className="block truncate text-xs text-muted">{member.email}</span>
          </span>
        </span>
      </td>
      {details && (
        <td className="px-3">
          <AccountBadge account={member.account} />
        </td>
      )}
      <td className="px-3">
        {manages ? (
          <select
            aria-label={t("members.roleOf", { name: label })}
            value={member.role}
            onChange={(e) => onRole(e.target.value as ProjectRole)}
            className="h-9 rounded-md border border-line bg-surface px-2"
          >
            {ROLES.map((role) => (
              <option key={role} value={role}>
                {t(`projectRole.${role}`)}
              </option>
            ))}
          </select>
        ) : (
          <span className="rounded-full bg-sunken px-2 py-0.5 text-xs">
            {t(`rolePill.${member.role}`)}
          </span>
        )}
      </td>
      {details && (
        <td className="px-3 text-muted">
          {member.last_seen_at ? when(member.last_seen_at, { dateOnly: true }) : t("members.never")}
        </td>
      )}
      <td className="px-3">
        {(manages || me) && (
          <button
            type="button"
            aria-label={
              me && !manages ? t("pmembers.leave") : t("members.removeOf", { name: label })
            }
            onClick={onRemove}
            className="flex items-center gap-1.5 text-muted hover:text-danger"
          >
            <Icon name="x" className="size-4" />
            {me && !manages ? t("pmembers.leave") : t("members.remove")}
          </button>
        )}
      </td>
    </tr>
  );
}
