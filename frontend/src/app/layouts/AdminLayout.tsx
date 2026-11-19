import { Link, NavLink, Outlet } from "react-router";
import { RequireSession, SignOutButton, useMe } from "@/features/auth";
import { Initials } from "@/features/orgs";
import { t } from "@/shared/i18n";
import { Icon } from "@/shared/ui/Icon";

// Super admin console shell (prototype rail in admin mode): Back to app, the
// console pages, and the signed-in person. The API refuses everyone else with
// 403; the shell says so instead of calling it.
export function AdminLayout() {
  return (
    <RequireSession>
      <AdminShell />
    </RequireSession>
  );
}

const PAGES = [
  { to: "/admin", label: "admin.companies", icon: "building", end: true },
  { to: "/admin/people", label: "admin.people", icon: "users", end: false },
  { to: "/admin/invites", label: "admin.invites", icon: "mail", end: false },
  { to: "/admin/audit", label: "admin.audit", icon: "log", end: false },
  { to: "/admin/server", label: "admin.server", icon: "server", end: false },
] as const;

function AdminShell() {
  const me = useMe();
  const link = ({ isActive }: { isActive: boolean }) =>
    `flex h-9 items-center gap-3 rounded-md px-3 ${isActive ? "bg-accent-soft font-semibold text-accent" : "hover:bg-sunken"}`;

  return (
    <div className="flex min-h-screen bg-bg text-ink">
      <aside className="flex w-64 shrink-0 flex-col gap-4 border-r border-line bg-surface p-4">
        <nav aria-label={t("admin.title")} className="flex flex-col gap-1 text-sm">
          <Link to="/" className="flex h-9 items-center gap-3 rounded-md px-3 hover:bg-sunken">
            <Icon name="back" />
            {t("admin.back")}
          </Link>
          <h2 className="px-3 pt-3 pb-1 text-xs font-semibold uppercase tracking-wide text-muted">
            {t("admin.title")}
          </h2>
          {PAGES.map((page) => (
            <NavLink key={page.to} to={page.to} end={page.end} className={link}>
              <Icon name={page.icon} />
              {t(page.label)}
            </NavLink>
          ))}
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
        {me.is_super_admin ? <Outlet /> : <p role="alert">{t("admin.onlySuperAdmins")}</p>}
      </main>
    </div>
  );
}
