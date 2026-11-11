import { t } from "@/lib/i18n";

export function NotFoundPage() {
  return (
    <div className="grid min-h-screen place-items-center bg-bg text-muted">{t("notFound")}</div>
  );
}
