import { Navigate } from "react-router";
import { AllInvitesTable, LoadFailed, Loading, PageHead, allInvites } from "@/features/admin";
import { t } from "@/shared/i18n";
import { useAsync } from "@/shared/lib/useAsync";

// Console: Invites (prototype admin-invites), every company's pending invites.
export function InvitesPage() {
  const [list, reload] = useAsync(allInvites, "admin:invites");

  if (list.kind === "failed" && list.status === 401) return <Navigate to="/signin" replace />;
  return (
    <>
      <PageHead title={t("admin.invites")} lead={t("admin.invitesLead")} />
      {list.kind === "loading" && <Loading />}
      {list.kind === "failed" && <LoadFailed code={list.code} onRetry={reload} />}
      {list.kind === "ready" && <AllInvitesTable invites={list.value} onChanged={reload} />}
    </>
  );
}
