import { useEffect, useState } from "react";
import { Link, Navigate, useLocation, useNavigate, useParams } from "react-router";
import {
  DeleteCompanyDialog,
  LoadFailed,
  Loading,
  StatusPill,
  company,
  consoleCompanyBase,
  resumeCompany,
  suspendCompany,
  type CompanySummary,
} from "@/features/admin";
import { useMe } from "@/features/auth";
import {
  Initials,
  InviteForm,
  InvitesTable,
  MembersTable,
  invites,
  members,
} from "@/features/orgs";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { useAsync } from "@/shared/lib/useAsync";

type Tab = "members" | "settings";

// Console: Company detail (prototype admin-company). Suspend or Resume in the
// header; tabs Members and invites, and Settings with Delete company (M1-07).
// The Projects tab comes with M2; name and storage limit editing wait (D35).
export function CompanyPage() {
  const { slug = "" } = useParams();
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
  const [found, reloadCompany] = useAsync(() => company(slug), `admin:company:${slug}`);
  const [tab, setTab] = useState<Tab>("members");
  const [done, setDone] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [deleting, setDeleting] = useState(false);

  if (found.kind === "loading") return <Loading />;
  if (found.kind === "failed") {
    if (found.status === 401) return <Navigate to="/signin" replace />;
    return <LoadFailed code={found.code} onRetry={reloadCompany} />;
  }
  const org = found.value;
  const active = org.status === "active";

  async function toggle() {
    setBusy(true);
    setProblem(null);
    setDone(null);
    try {
      await (active ? suspendCompany(slug) : resumeCompany(slug));
      setDone(t(active ? "admin.suspendedNotice" : "admin.resumedNotice", { name: org.name }));
      reloadCompany();
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
    } finally {
      setBusy(false);
    }
  }

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
        <button
          type="button"
          disabled={busy}
          onClick={toggle}
          className="ml-auto h-10 rounded-md border border-line bg-surface px-4 font-semibold hover:bg-sunken disabled:opacity-60"
        >
          {active ? t("admin.suspend") : t("admin.resume")}
        </button>
      </div>
      {(notice || problem) && (
        <p role="alert" className="mb-4 text-danger">
          {problem ?? notice}
        </p>
      )}
      {done && (
        <p role="status" className="mb-4 text-success">
          {done}
        </p>
      )}
      <div
        role="tablist"
        aria-label={t("admin.sections")}
        className="mb-5 flex gap-1 border-b border-line"
      >
        {(["members", "settings"] as const).map((name) => (
          <button
            key={name}
            type="button"
            role="tab"
            aria-selected={tab === name}
            onClick={() => setTab(name)}
            className={`-mb-px border-b-2 px-3 py-2 font-semibold ${
              tab === name
                ? "border-accent text-accent"
                : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {name === "members" ? t("admin.tabMembers") : t("admin.tabSettings")}
          </button>
        ))}
      </div>
      {tab === "members" ? (
        <MembersTab org={org} />
      ) : (
        <section className="rounded-xl border border-danger bg-surface p-5">
          <h2 className="text-lg font-semibold">{t("admin.deleteTitle")}</h2>
          <p className="mt-1 mb-4 text-sm text-muted">{t("admin.deleteLead")}</p>
          <button
            type="button"
            onClick={() => setDeleting(true)}
            className="h-10 rounded-md border border-danger px-4 font-semibold text-danger hover:bg-danger/10"
          >
            {t("admin.deleteButton")}
          </button>
        </section>
      )}
      {deleting && (
        <DeleteCompanyDialog
          company={org}
          onClose={() => setDeleting(false)}
          onDeleted={() =>
            navigate("/admin", {
              state: { done: t("admin.trashedNotice", { name: org.name }) },
            })
          }
        />
      )}
    </>
  );
}

/** Members and invites, read-only while the company is suspended. */
function MembersTab({ org }: { org: CompanySummary }) {
  const me = useMe();
  const base = consoleCompanyBase(org.slug);
  const [people, reloadPeople] = useAsync(() => members(base), `admin:members:${org.slug}`);
  const [pending, reloadPending] = useAsync(() => invites(base), `admin:invites:${org.slug}`);
  const readOnly = org.status !== "active";
  const failed = people.kind === "failed" ? people : pending.kind === "failed" ? pending : null;
  return (
    <>
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
