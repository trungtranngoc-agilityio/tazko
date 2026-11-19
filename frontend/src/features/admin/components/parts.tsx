import type { ReactNode } from "react";
import { errorText, t } from "@/shared/i18n";

/** The heading row every console page starts with. */
export function PageHead({
  title,
  lead,
  children,
}: {
  title: string;
  lead: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start gap-4">
      <div>
        <h1 className="text-[1.75rem] font-bold">{title}</h1>
        <p className="mt-1 text-muted">{lead}</p>
      </div>
      {children && <div className="ml-auto flex items-center gap-3">{children}</div>}
    </div>
  );
}

/** A load that failed: the reason, and Try again. */
export function LoadFailed({ code, onRetry }: { code: string; onRetry: () => void }) {
  return (
    <div>
      <p role="alert">{errorText(code)}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 h-9 rounded-md border border-line bg-surface px-4 font-semibold hover:bg-sunken"
      >
        {t("session.retry")}
      </button>
    </div>
  );
}

export function Loading() {
  return (
    <p role="status" className="text-muted">
      {t("session.loading")}
    </p>
  );
}

export function StatusPill({ status }: { status: "active" | "suspended" }) {
  const style = status === "active" ? "bg-success/15 text-success" : "bg-warning/20 text-ink";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${style}`}>
      {status === "active" ? t("admin.active") : t("company.suspended")}
    </span>
  );
}

/** An on/off switch (prototype People page). */
export function Switch({
  on,
  label,
  onToggle,
}: {
  on: boolean;
  label: string;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      onClick={onToggle}
      className={`relative h-5 w-9 rounded-full transition-colors ${on ? "bg-accent" : "bg-line"}`}
    >
      <span
        aria-hidden="true"
        className={`absolute top-0.5 size-4 rounded-full bg-white shadow transition-[left] ${on ? "left-[1.125rem]" : "left-0.5"}`}
      />
    </button>
  );
}

export const tableHead = "bg-sunken text-left text-xs uppercase tracking-wide text-muted";
export const box = "overflow-x-auto rounded-xl border border-line bg-surface";
