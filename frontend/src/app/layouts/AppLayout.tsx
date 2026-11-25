import { Outlet } from "react-router";
import { RequireSession, SignOutButton } from "@/features/auth";
import { t } from "@/shared/i18n";

// App shell: header with company switcher, then the routed page.
export function AppLayout() {
  return (
    <RequireSession>
      <div className="min-h-screen bg-bg text-ink">
        <header className="flex h-12 items-center border-b border-line bg-surface px-4">
          <span className="font-semibold">{t("app.name")}</span>
          <span className="ml-auto">
            <SignOutButton />
          </span>
        </header>
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </RequireSession>
  );
}
