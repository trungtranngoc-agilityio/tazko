import { t } from "@/shared/i18n";

// Company home (M1): switcher and empty state, per the prototype.
export function HomePage() {
  return <p className="text-muted">{t("home.empty")}</p>;
}
