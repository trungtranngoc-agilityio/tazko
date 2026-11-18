import { useNavigate } from "react-router";
import { useMe } from "@/features/auth";
import {
  InviteForm,
  InvitesTable,
  MembersTable,
  invites,
  members,
  useCompany,
} from "@/features/orgs";
import { errorText, t } from "@/shared/i18n";
import { useAsync } from "@/shared/lib/useAsync";

// Company settings (prototype 04): invite someone, members, pending invites.
// The API answers 403 to anyone who is not an owner; the page says so.
export function CompanySettingsPage() {
  const { company } = useCompany();
  const me = useMe();
  const navigate = useNavigate();
  const slug = company.slug;
  const [people, reloadPeople] = useAsync(() => members(slug), `members:${slug}`);
  const [pending, reloadPending] = useAsync(() => invites(slug), `invites:${slug}`);

  const failed = people.kind === "failed" ? people : pending.kind === "failed" ? pending : null;
  if (failed) {
    return (
      <p role="alert" className="text-ink">
        {errorText(failed.code)}
      </p>
    );
  }

  return (
    <>
      <h1 className="text-[1.75rem] font-bold">{t("settings.title")}</h1>
      <p className="mt-1 text-muted">{t("settings.lead", { company: company.name })}</p>
      <div className="mt-6 flex flex-col gap-5">
        <InviteForm slug={slug} onInvited={reloadPending} />
        {people.kind === "ready" ? (
          <MembersTable
            slug={slug}
            company={company.name}
            members={people.value}
            meId={me.id}
            onChanged={reloadPeople}
            onLeft={() => navigate("/", { replace: true })}
          />
        ) : (
          <p role="status" className="text-muted">
            {t("session.loading")}
          </p>
        )}
        {pending.kind === "ready" && (
          <InvitesTable slug={slug} invites={pending.value} onChanged={reloadPending} />
        )}
      </div>
    </>
  );
}
