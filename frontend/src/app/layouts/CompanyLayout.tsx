import { Navigate, NavLink, Outlet, useLocation, useMatch, useParams } from "react-router";
import { RequireSession, SignOutButton, useMe } from "@/features/auth";
import { CompanySwitcher, Initials, myCompanies, type CompanyContext } from "@/features/orgs";
import { errorText, t } from "@/shared/i18n";
import { useAsync } from "@/shared/lib/useAsync";
import { Icon } from "@/shared/ui/Icon";

// The app shell inside one company (prototype: sidebar with the company card,
// navigation, and the signed-in person at the bottom). Pages get the current
// company through useCompany().
export function CompanyLayout() {
  return (
    <RequireSession>
      <CompanyShell />
    </RequireSession>
  );
}

function CompanyShell() {
  const { slug = "" } = useParams();
  const me = useMe();
  const { pathname } = useLocation();
  // A board fills the window without the sidebar, as in the prototype.
  const onBoard = useMatch("/c/:slug/p/:projectId/b/:boardId") !== null;
  const [companies, reloadCompanies] = useAsync(myCompanies, "companies");

  if (companies.kind === "loading") {
    return (
      <p role="status" className="p-6 text-muted">
        {t("session.loading")}
      </p>
    );
  }
  if (companies.kind === "failed") {
    if (companies.status === 401) return <Navigate to="/signin" replace />;
    return (
      <p role="alert" className="p-6">
        {errorText(companies.code)}
      </p>
    );
  }
  const found = companies.value.find((c) => c.slug === slug);
  if (!found || found.status !== "active") {
    return (
      <p role="alert" className="p-6">
        {found ? t("company.isSuspended") : errorText("NOT_FOUND")}
      </p>
    );
  }
  const company = found;
  const context: CompanyContext = { company, companies: companies.value, reloadCompanies };
  const link = ({ isActive }: { isActive: boolean }) =>
    `flex h-9 items-center gap-3 rounded-md px-3 ${isActive ? "bg-accent-soft font-semibold text-accent" : "hover:bg-sunken"}`;

  if (onBoard) {
    return (
      <main className="min-h-screen bg-bg text-ink">
        <Outlet context={context} />
      </main>
    );
  }
  return (
    <div className="flex min-h-screen bg-bg text-ink">
      <aside className="flex w-64 shrink-0 flex-col gap-4 border-r border-line bg-surface p-4">
        <CompanySwitcher
          companies={companies.value}
          current={company}
          superAdmin={me.is_super_admin}
        />
        <nav className="flex flex-col gap-1 text-sm">
          {/* Projects stays lit inside a project, as in the prototype. */}
          <NavLink
            end
            to={`/c/${company.slug}`}
            className={({ isActive }) =>
              link({ isActive: isActive || pathname.startsWith(`/c/${company.slug}/p/`) })
            }
          >
            <Icon name="grid" />
            {t("nav.projects")}
          </NavLink>
          {company.role === "owner" && (
            <NavLink to={`/c/${company.slug}/manage`} className={link}>
              <Icon name="building" />
              {t("nav.manage")}
            </NavLink>
          )}
          {company.role === "owner" && (
            <NavLink to={`/c/${company.slug}/settings`} className={link}>
              <Icon name="gear" />
              {t("nav.settings")}
            </NavLink>
          )}
        </nav>
        <div className="mt-auto flex items-center gap-3 text-sm">
          <Initials name={me.name || me.email} />
          <span className="min-w-0 flex-1">
            <span className="block truncate font-semibold">{me.name || me.email}</span>
            {me.is_super_admin && (
              <span className="block text-xs text-muted">{t("nav.superAdmin")}</span>
            )}
          </span>
        </div>
        <SignOutButton />
      </aside>
      <main className="min-w-0 flex-1 p-7">
        <Outlet context={context} />
      </main>
    </div>
  );
}
