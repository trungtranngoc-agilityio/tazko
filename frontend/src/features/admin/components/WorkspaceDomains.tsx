import { useState } from "react";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { when } from "@/shared/lib/when";
import { forgetWorkspaceDomain, type WorkspaceDomain } from "../api";
import { tableHead } from "./parts";

/** Recorded Google Workspace domains, with Forget for a company that
 * left Workspace. Not in the prototype; placed on the Server page. */
export function WorkspaceDomains({
  domains,
  onChanged,
}: {
  domains: WorkspaceDomain[];
  onChanged: () => void;
}) {
  const [problem, setProblem] = useState<string | null>(null);

  async function forget(domain: string) {
    if (!window.confirm(t("admin.confirmForget", { domain }))) return;
    setProblem(null);
    try {
      await forgetWorkspaceDomain(domain);
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
    }
    onChanged();
  }

  return (
    <section className="mt-5 rounded-xl border border-line bg-surface">
      <h2 className="px-5 pt-5 text-lg font-semibold">{t("admin.domains")}</h2>
      <p className="max-w-2xl px-5 pt-1 text-sm text-muted">{t("admin.domainsHelp")}</p>
      {problem && (
        <p role="alert" className="px-5 pt-2 text-sm text-danger">
          {problem}
        </p>
      )}
      {domains.length === 0 ? (
        <p className="px-5 py-4 text-sm text-muted">{t("admin.domainsNone")}</p>
      ) : (
        <table aria-label={t("admin.domains")} className="mt-3 w-full text-sm">
          <thead className={tableHead}>
            <tr>
              <th className="px-5 py-2 font-semibold">{t("admin.domains")}</th>
              <th className="px-3 py-2 font-semibold">{t("admin.firstSeen")}</th>
              <th className="px-3 py-2">
                <span className="sr-only">{t("admin.forget")}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {domains.map((d) => (
              <tr key={d.domain} className="border-t border-line">
                <td className="px-5 py-3 font-mono">{d.domain}</td>
                <td className="px-3 text-muted">{when(d.first_seen_at, { dateOnly: true })}</td>
                <td className="px-3">
                  <button
                    type="button"
                    aria-label={t("admin.forgetOf", { domain: d.domain })}
                    onClick={() => void forget(d.domain)}
                    className="h-8 rounded-md border border-line px-3 hover:bg-sunken"
                  >
                    {t("admin.forget")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
