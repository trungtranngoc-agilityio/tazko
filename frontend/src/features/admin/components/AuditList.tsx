import { t, type MessageKey } from "@/shared/i18n";
import { when } from "@/shared/lib/when";
import type { AuditEntry } from "../api";
import { box } from "./parts";

// How each audit action reads in a sentence; an action without one shows its
// name, so a new action is never hidden.
const ACTIONS: Record<string, MessageKey> = {
  "signin.refused": "audit.signin.refused",
  "company.created": "audit.company.created",
  "member.added": "audit.member.added",
  "member.removed": "audit.member.removed",
  "member.role_changed": "audit.member.role_changed",
  "invite.created": "audit.invite.created",
  "invite.revoked": "audit.invite.revoked",
  "invite.accepted": "audit.invite.accepted",
  "person.enabled": "audit.person.enabled",
  "person.disabled": "audit.person.disabled",
  "super_admin.granted": "audit.super_admin.granted",
  "super_admin.revoked": "audit.super_admin.revoked",
  "account.created": "audit.account.created",
  "account.linked": "audit.account.linked",
  "workspace_domain.removed": "audit.workspace_domain.removed",
};

function verb(action: string): string {
  const key = ACTIONS[action];
  return key ? t(key) : action;
}

/** Audit log (prototype admin-audit): "<who> <did what> <target>", newest first.
 * Actor names and targets come from Google profiles and requests: text only. */
export function AuditList({ entries }: { entries: AuditEntry[] }) {
  return (
    <div className={box}>
      <ul aria-label={t("admin.audit")} className="text-sm">
        {entries.map((entry) => {
          const refused = entry.action === "signin.refused";
          const who = entry.actor
            ? entry.actor.name || entry.actor.email
            : refused
              ? t("admin.someone")
              : t("admin.commandLine");
          const showCompany = entry.company && !entry.action.startsWith("company.");
          return (
            <li
              key={entry.id}
              className="flex gap-4 border-t border-line px-5 py-3 first:border-t-0"
            >
              <time dateTime={entry.at} className="w-28 shrink-0 text-muted">
                {when(entry.at)}
              </time>
              <span className="min-w-0 break-words">
                <b>{who}</b> {verb(entry.action)}
                {entry.target && (
                  <>
                    {" "}
                    <b>{entry.target}</b>
                  </>
                )}
                {showCompany && entry.company && (
                  <span className="text-muted">
                    {" "}
                    {t("admin.in", { company: entry.company.name })}
                  </span>
                )}
                {refused && (
                  <>
                    {" "}
                    <span className="rounded-full bg-danger/15 px-2 py-0.5 text-xs font-semibold text-danger">
                      {t("admin.refused")}
                    </span>
                  </>
                )}
              </span>
            </li>
          );
        })}
        {entries.length === 0 && <li className="px-5 py-4 text-muted">{t("admin.noEntries")}</li>}
      </ul>
    </div>
  );
}
