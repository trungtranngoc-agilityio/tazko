import { useState } from "react";
import { useNavigate } from "react-router";
import { t } from "@/shared/i18n";
import type { Company } from "../api";
import { Initials } from "./Initials";

/**
 * The company card at the top of the sidebar. It lists only the person's own
 * companies; a suspended one is shown but cannot be opened (M1.md Q2).
 */
export function CompanySwitcher({
  companies,
  current,
}: {
  companies: Company[];
  current: Company;
}) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <div className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 rounded-lg border border-line bg-surface px-3 py-2.5 text-left hover:bg-sunken"
      >
        <Initials name={current.name} size="lg" />
        <span className="min-w-0 flex-1">
          <span className="block truncate font-semibold">{current.name}</span>
          <span className="block text-xs text-muted">{t(`role.${current.role}`)}</span>
        </span>
        <span aria-hidden="true" className="text-muted">
          ▾
        </span>
      </button>
      {open && (
        <ul
          role="menu"
          aria-label={t("company.switch")}
          className="absolute inset-x-0 top-full z-10 mt-1 rounded-lg border border-line bg-surface p-1 shadow-card"
        >
          {companies.map((company) => {
            const suspended = company.status === "suspended";
            return (
              <li
                key={company.slug}
                role="menuitem"
                aria-disabled={suspended}
                tabIndex={suspended ? -1 : 0}
                onClick={() => {
                  if (suspended) return;
                  setOpen(false);
                  navigate(`/c/${company.slug}`);
                }}
                onKeyDown={(event) => {
                  if (!suspended && (event.key === "Enter" || event.key === " ")) {
                    event.preventDefault();
                    setOpen(false);
                    navigate(`/c/${company.slug}`);
                  }
                }}
                className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-sm ${
                  suspended ? "cursor-not-allowed text-muted" : "cursor-pointer hover:bg-sunken"
                } ${company.slug === current.slug ? "font-semibold" : ""}`}
              >
                <span className="flex-1 truncate">{company.name}</span>
                <span className="text-xs text-muted">
                  {suspended ? t("company.suspended") : t(`role.${company.role}`)}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
