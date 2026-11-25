import { Link } from "react-router";
import { Initials } from "@/features/orgs";
import { t } from "@/shared/i18n";
import { size } from "@/shared/lib/size";
import { when } from "@/shared/lib/when";
import type { CompanySummary } from "../api";
import { box, StatusPill, tableHead } from "./parts";

/** Companies page table (prototype admin-companies). */
export function CompaniesTable({ companies }: { companies: CompanySummary[] }) {
  if (companies.length === 0) {
    return <p className="text-muted">{t("admin.noCompanies")}</p>;
  }
  return (
    <div className={box}>
      <table aria-label={t("admin.companies")} className="w-full text-sm">
        <thead className={tableHead}>
          <tr>
            <th className="px-5 py-2 font-semibold">{t("admin.company")}</th>
            <th className="px-3 py-2 font-semibold">{t("admin.status")}</th>
            <th className="px-3 py-2 text-right font-semibold">{t("admin.members")}</th>
            <th className="px-3 py-2 font-semibold">{t("admin.storage")}</th>
            <th className="px-3 py-2 font-semibold">{t("admin.lastActivity")}</th>
          </tr>
        </thead>
        <tbody>
          {companies.map((company) => (
            <tr key={company.slug} className="border-t border-line hover:bg-sunken">
              <td className="px-5 py-2.5">
                <Link
                  to={`/admin/companies/${encodeURIComponent(company.slug)}`}
                  className="flex items-center gap-3"
                >
                  <Initials name={company.name} size="lg" />
                  <span>
                    <span className="block font-semibold">{company.name}</span>
                    <span className="block font-mono text-xs text-muted">{company.slug}</span>
                  </span>
                </Link>
              </td>
              <td className="px-3">
                <StatusPill status={company.status} />
              </td>
              <td className="px-3 text-right tabular-nums">{company.members}</td>
              <td className="px-3">
                <Storage used={company.storage_bytes} limit={company.storage_limit_bytes} />
              </td>
              <td className="px-3 text-muted">
                {company.last_activity_at ? when(company.last_activity_at) : ""}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Storage({ used, limit: given }: { used: number; limit: number | null }) {
  const limit = given !== null && given > 0 ? given : null;
  const percent = limit ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  return (
    <span className="block w-32">
      {limit !== null && (
        <span aria-hidden="true" className="block h-1.5 overflow-hidden rounded-full bg-sunken">
          <span className="block h-full bg-accent" style={{ width: `${percent}%` }} />
        </span>
      )}
      <span className="text-xs text-muted">
        {limit === null ? size(used) : `${size(used)} / ${size(limit)}`}
      </span>
    </span>
  );
}
