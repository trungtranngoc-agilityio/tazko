import { Navigate } from "react-router";
import {
  LoadFailed,
  Loading,
  PageHead,
  ServerPanel,
  WorkspaceDomains,
  server,
  workspaceDomains,
} from "@/features/admin";
import { t } from "@/shared/i18n";
import { useAsync } from "@/shared/lib/useAsync";

// Console: Server (prototype admin-server) and Workspace domains.
export function ServerPage() {
  const [info, reloadInfo] = useAsync(server, "admin:server");
  const [domains, reloadDomains] = useAsync(workspaceDomains, "admin:domains");

  if (info.kind === "failed" && info.status === 401) return <Navigate to="/signin" replace />;
  return (
    <>
      <PageHead
        title={t("admin.server")}
        lead={info.kind === "ready" ? info.value.public_url : ""}
      />
      {info.kind === "loading" && <Loading />}
      {info.kind === "failed" && <LoadFailed code={info.code} onRetry={reloadInfo} />}
      {info.kind === "ready" && <ServerPanel info={info.value} />}
      {domains.kind === "failed" && <LoadFailed code={domains.code} onRetry={reloadDomains} />}
      {domains.kind === "ready" && (
        <WorkspaceDomains domains={domains.value} onChanged={reloadDomains} />
      )}
    </>
  );
}
