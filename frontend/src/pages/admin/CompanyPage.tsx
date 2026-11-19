import { useEffect, useState } from "react";
import { Link, Navigate, useLocation, useNavigate, useParams } from "react-router";
import { LoadFailed, Loading, StatusPill, company, consoleCompanyBase } from "@/features/admin";
import { useMe } from "@/features/auth";
import {
  Initials,
  InviteForm,
  InvitesTable,
  MembersTable,
  invites,
  members,
} from "@/features/orgs";
import { t } from "@/shared/i18n";
import { useAsync } from "@/shared/lib/useAsync";

// Console: Company detail (prototype admin-company), Members and invites.
// Suspend, Resume and the Settings tab come with M1-07; Projects with M2 (D31).
export function CompanyPage() {
  const { slug = "" } = useParams();
  const me = useMe();
  const location = useLocation();
  const navigate = useNavigate();
  // A problem from New company, shown once: taken out of history so a reload
  // or Back does not show it again.
  const [notice] = useState(
    () => (location.state as { problem?: string | null } | null)?.problem ?? null,
  );
  useEffect(() => {
    if (location.state) navigate(location.pathname, { replace: true, state: null });
  }, [location.state, location.pathname, navigate]);
  const base = consoleCompanyBase(slug);
  const [found, reloadCompany] = useAsync(() => company(slug), `admin:company:${slug}`);
  const [people, reloadPeople] = useAsync(() => members(base), `admin:members:${slug}`);
  const [pending, reloadPending] = useAsync(() => invites(base), `admin:invites:${slug}`);

  if (found.kind === "loading") return <Loading />;
  if (found.kind === "failed") {
    if (found.status === 401) return <Navigate to="/signin" replace />;
    return <LoadFailed code={found.code} onRetry={reloadCompany} />;
  }
  const org = found.value;
  const readOnly = org.status !== "active";
  const failed = people.kind === "failed" ? people : pending.kind === "failed" ? pending : null;
  return (
    <>
      <p className="mb-3 text-sm text-muted">
        <Link to="/admin" className="underline hover:text-accent">
          {t("admin.companies")}
        </Link>{" "}
        / {org.name}
      </p>
      <div className="mb-5 flex flex-wrap items-center gap-4">
        <Initials name={org.name} size="xl" />
        <div>
          <h1 className="text-[1.75rem] font-bold">{org.name}</h1>
          <small className="font-mono text-muted">{org.slug}</small>
        </div>
        <StatusPill status={org.status} />
      </div>
      {notice && (
        <p role="alert" className="mb-4 text-danger">
          {notice}
        </p>
      )}
      <p className="mb-4 rounded-lg bg-sunken px-4 py-3 text-sm">
        {readOnly ? t("error.COMPANY_NOT_ACTIVE") : t("admin.companyNote")}
      </p>
      {failed ? (
        <LoadFailed
          code={failed.code}
          onRetry={() => {
            reloadPeople();
            reloadPending();
          }}
        />
      ) : (
        <div className="flex flex-col gap-5">
          {!readOnly && <InviteForm base={base} onInvited={reloadPending} />}
          {people.kind === "ready" ? (
            <MembersTable
              base={base}
              company={org.name}
              members={people.value}
              meId={me.id}
              onChanged={reloadPeople}
              onLeft={reloadPeople}
              onSelfDemoted={reloadPeople}
              readOnly={readOnly}
            />
          ) : (
            <Loading />
          )}
          {pending.kind === "ready" ? (
            <InvitesTable
              base={base}
              invites={pending.value}
              onChanged={reloadPending}
              readOnly={readOnly}
            />
          ) : (
            <Loading />
          )}
        </div>
      )}
    </>
  );
}
