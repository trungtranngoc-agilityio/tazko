import { useCompany } from "@/features/orgs";
import { t } from "@/shared/i18n";

// Company home: the Projects heading and its empty state.
export function CompanyHomePage() {
  const { company } = useCompany();
  return (
    <>
      <h1 className="text-[1.75rem] font-bold">{t("projects.title")}</h1>
      <p className="mt-1 text-muted">{t("projects.lead", { company: company.name })}</p>
      <section className="mt-8 rounded-xl border border-dashed border-line px-6 py-14 text-center">
        {/* Three board columns, as in the prototype's empty state. */}
        <svg aria-hidden="true" viewBox="0 0 108 64" className="mx-auto mb-5 h-16 w-28">
          <rect x="0" y="0" width="30" height="64" rx="6" className="fill-accent-soft" />
          <rect x="39" y="0" width="30" height="40" rx="6" className="fill-accent/30" />
          <rect x="78" y="0" width="30" height="52" rx="6" className="fill-accent-soft" />
        </svg>
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
