import { Navigate } from "react-router";
import { myCompanies } from "@/features/orgs";
import { errorText, t } from "@/shared/i18n";
import { useAsync } from "@/shared/lib/useAsync";

// "/": open the person's first active company, or say they are in none yet.
export function HomePage() {
  const [companies] = useAsync(myCompanies, "companies");

  if (companies.kind === "loading") {
    return (
      <p role="status" className="text-muted">
        {t("session.loading")}
      </p>
    );
  }
  if (companies.kind === "failed") return <p role="alert">{errorText(companies.code)}</p>;
  const first = companies.value.find((c) => c.status === "active");
  if (first) return <Navigate to={`/c/${first.slug}`} replace />;
  return (
    <div className="mx-auto mt-16 max-w-md text-center">
      <h1 className="text-lg font-semibold">{t("home.noCompany")}</h1>
      <p className="mt-2 text-sm text-muted">{t("home.noCompanyHelp")}</p>
    </div>
  );
}
