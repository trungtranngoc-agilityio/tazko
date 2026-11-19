import { Navigate, useNavigate } from "react-router";
import { useMe } from "@/features/auth";
import {
  InviteForm,
  InvitesTable,
  MembersTable,
  companyBase,
  invites,
  members,
  useCompany,
} from "@/features/orgs";
import { errorText, t } from "@/shared/i18n";
import { useAsync } from "@/shared/lib/useAsync";

// Company settings (prototype 04): invite someone, members, pending invites.
// The API answers 403 to anyone who is not an owner; the page says so under
// its heading, with Try again.
export function CompanySettingsPage() {
  const { company, reloadCompanies } = useCompany();
  const me = useMe();
  const navigate = useNavigate();
  const slug = company.slug;
  const base = companyBase(slug);
  const [people, reloadPeople] = useAsync(() => members(base), `members:${slug}`);
  const [pending, reloadPending] = useAsync(() => invites(base), `invites:${slug}`);
  const failed = people.kind === "failed" ? people : pending.kind === "failed" ? pending : null;

  if (failed?.status === 401) return <Navigate to="/signin" replace />;
  return (
    <>
      <h1 className="text-[1.75rem] font-bold">{t("settings.title")}</h1>
      <p className="mt-1 text-muted">{t("settings.lead", { company: company.name })}</p>
      {failed ? (
        <div className="mt-6">
          <p role="alert" className="text-ink">
            {errorText(failed.code)}
          </p>
          <button
            type="button"
            onClick={() => {
              reloadPeople();
              reloadPending();
            }}
            className="mt-3 h-9 rounded-md border border-line bg-surface px-4 font-semibold hover:bg-sunken"
          >
            {t("session.retry")}
          </button>
        </div>
      ) : (
        <div className="mt-6 flex flex-col gap-5">
          <InviteForm base={base} onInvited={reloadPending} />
          {people.kind === "ready" ? (
            <MembersTable
              base={base}
              company={company.name}
              members={people.value}
              meId={me.id}
              onChanged={reloadPeople}
              onLeft={() => navigate("/", { replace: true })}
              onSelfDemoted={() => {
                reloadCompanies();
                navigate(`/c/${slug}`, { replace: true });
              }}
            />
          ) : (
            <p role="status" className="text-muted">
              {t("session.loading")}
            </p>
          )}
          {pending.kind === "ready" ? (
            <InvitesTable base={base} invites={pending.value} onChanged={reloadPending} />
          ) : (
            <p className="text-muted">{t("session.loading")}</p>
          )}
        </div>
      )}
    </>
  );
}
