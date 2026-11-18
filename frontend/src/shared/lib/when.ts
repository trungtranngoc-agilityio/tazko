import { t } from "@/shared/i18n";

const DAY = 24 * 60 * 60 * 1000;

function startOfDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

/**
 * A past moment as the prototype writes it: "Today 09:12", "Yesterday",
 * "3 days ago", then "12 Oct". `now` is a parameter so tests can fix it.
 */
export function when(iso: string, now: Date = new Date()): string {
  const at = new Date(iso);
  const days = Math.round((startOfDay(now) - startOfDay(at)) / DAY);
  if (days <= 0) {
    const time = at.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
    return t("when.today", { time });
  }
  if (days === 1) return t("when.yesterday");
  if (days < 7) return t("when.daysAgo", { days });
  return at.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}
