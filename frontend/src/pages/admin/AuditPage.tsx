import { useState } from "react";
import { Navigate } from "react-router";
import {
  AUDIT_KINDS,
  AuditList,
  LoadFailed,
  Loading,
  MoreButton,
  PageHead,
  auditLog,
  usePages,
  type AuditKind,
} from "@/features/admin";
import { t } from "@/shared/i18n";

// Console: Audit log (prototype admin-audit), filtered by kind on the server.
export function AuditPage() {
  const [kind, setKind] = useState<AuditKind | null>(null);
  const [attempt, setAttempt] = useState(0);
  const { pages, showMore } = usePages(
    (before) => auditLog(kind, before),
    `audit:${attempt}:${kind ?? "all"}`,
  );

  if (pages.kind === "failed" && pages.status === 401) return <Navigate to="/signin" replace />;
  return (
    <>
      <PageHead title={t("admin.audit")} lead={t("admin.auditLead")}>
        <select
          aria-label={t("admin.filter")}
          value={kind ?? ""}
          onChange={(e) => setKind((e.target.value || null) as AuditKind | null)}
          className="h-10 rounded-md border border-line bg-surface px-3"
        >
          <option value="">{t("audit.all")}</option>
          {AUDIT_KINDS.map((k) => (
            <option key={k} value={k}>
              {t(`audit.${k}`)}
            </option>
          ))}
        </select>
      </PageHead>
      {pages.kind === "loading" && <Loading />}
      {pages.kind === "failed" && (
        <LoadFailed code={pages.code} onRetry={() => setAttempt((n) => n + 1)} />
      )}
      {pages.kind === "ready" && (
        <>
          <AuditList entries={pages.items} />
          <MoreButton next={pages.next} problem={pages.more} onClick={showMore} />
        </>
      )}
    </>
  );
}
