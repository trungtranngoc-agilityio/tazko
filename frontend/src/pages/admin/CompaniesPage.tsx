import { useState } from "react";
import { Navigate, useNavigate } from "react-router";
import {
  CompaniesTable,
  LoadFailed,
  Loading,
  NewCompanyDialog,
  PageHead,
  companies,
} from "@/features/admin";
import { t } from "@/shared/i18n";
import { useAsync } from "@/shared/lib/useAsync";

// Console: Companies (prototype admin-companies), with New company.
export function CompaniesPage() {
  const [list, reload] = useAsync(companies, "admin:companies");
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  if (list.kind === "failed" && list.status === 401) return <Navigate to="/signin" replace />;
  return (
    <>
      <PageHead title={t("admin.companies")} lead={t("admin.companiesLead")}>
        <button
          type="button"
          onClick={() => setCreating(true)}
          className="h-10 rounded-md bg-accent px-4 font-semibold text-white"
        >
          <span aria-hidden="true">+ </span>
          {t("admin.newCompany")}
        </button>
      </PageHead>
      {list.kind === "loading" && <Loading />}
      {list.kind === "failed" && <LoadFailed code={list.code} onRetry={reload} />}
      {list.kind === "ready" && <CompaniesTable companies={list.value} />}
      {creating && (
        <NewCompanyDialog
          onClose={() => setCreating(false)}
          onCreated={(slug, problem) =>
            navigate(`/admin/companies/${encodeURIComponent(slug)}`, { state: { problem } })
          }
        />
      )}
    </>
  );
}
