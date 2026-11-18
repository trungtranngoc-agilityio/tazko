import { t } from "@/shared/i18n";
import type { Account } from "../api";

/** "Workspace" or "Personal Gmail"; nothing when it is not known yet. */
export function AccountBadge({ account }: { account: Account }) {
  if (!account) return null;
  const style = account === "workspace" ? "bg-accent-soft text-accent" : "bg-sunken text-muted";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${style}`}>
      {t(`account.${account}`)}
    </span>
  );
}
