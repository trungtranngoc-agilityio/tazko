import { useCompany } from "@/features/orgs";
import { t } from "@/shared/i18n";

// Company home (M1): the Projects heading and its empty state. Projects,
// starred boards and Manage projects arrive with M2.
export function CompanyHomePage() {
  const { company } = useCompany();
  return (
    <>
      <h1 className="text-[1.75rem] font-bold">{t("projects.title")}</h1>
      <p className="mt-1 text-muted">{t("projects.lead", { company: company.name })}</p>
      <section className="mt-8 rounded-xl border border-dashed border-line px-6 py-14 text-center">
        <h2 className="font-semibold">{t("projects.empty")}</h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-muted">
          {company.role === "owner"
            ? t("projects.emptyOwner")
            : t("projects.emptyMember", { company: company.name })}
        </p>
      </section>
    </>
  );
}
