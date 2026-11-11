import { Outlet } from "react-router";
import { t } from "@/shared/i18n";

// Super admin console shell (M1-06): Companies, Company detail, People,
// Invites, Audit log, Server.
export function AdminLayout() {
  return (
    <div className="min-h-screen bg-bg text-ink">
      <header className="flex h-12 items-center border-b border-line bg-surface px-4">
        <span className="font-semibold">{t("admin.title")}</span>
      </header>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
