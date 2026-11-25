import { t } from "@/shared/i18n";
import { size } from "@/shared/lib/size";
import type { ServerInfo } from "../api";

function uptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  if (days === 1) return t("admin.uptimeDay", { hours });
  if (days > 1) return t("admin.uptimeDays", { days, hours });
  return t("admin.uptimeHours", { hours, minutes: Math.floor((seconds % 3600) / 60) });
}

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-4">
      <small className="block text-xs text-muted">{label}</small>
      <b className="mt-1 block text-lg">{children}</b>
    </div>
  );
}

/** Server page stats and email (prototype admin-server). The API does not
 * report backups yet, so Last backup says it is not set up. */
export function ServerPanel({ info }: { info: ServerInfo }) {
  const { email } = info;
  return (
    <>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label={t("admin.version")}>
          <span className="font-mono">{info.version}</span>
        </Stat>
        <Stat label={t("admin.uptime")}>{uptime(info.uptime_seconds)}</Stat>
        <Stat label={t("admin.dataSize")}>{size(info.data_bytes)}</Stat>
        <Stat label={t("admin.lastBackup")}>
          <span className="text-muted">{t("admin.noBackup")}</span>
        </Stat>
      </div>
      <section className="mt-5 rounded-xl border border-line bg-surface p-5">
        <h2 className="text-lg font-semibold">{t("admin.email")}</h2>
        <p className="mt-3 flex flex-wrap items-center gap-3 text-sm">
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-semibold ${email.enabled ? "bg-success/15 text-success" : "bg-sunken text-muted"}`}
          >
            {email.enabled ? t("admin.emailOn") : t("admin.emailOff")}
          </span>
          {email.enabled && (
            <span className="text-muted">
              {t("admin.emailSender", {
                host: email.host ?? "",
                port: email.port ?? "",
                sender: email.sender ?? "",
              })}
            </span>
          )}
        </p>
        <p className="mt-3 text-sm text-muted">{t("admin.emailHelp")}</p>
      </section>
    </>
  );
}
