import { Outlet } from "react-router";
import { t } from "@/lib/i18n";

// App shell: header with company switcher (M1-06), then the routed page.
export function AppLayout() {
  return (
    <div className="min-h-screen bg-bg text-ink">
      <header className="flex h-12 items-center border-b border-line bg-surface px-4">
        <span className="font-semibold">{t("app.name")}</span>
      </header>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
