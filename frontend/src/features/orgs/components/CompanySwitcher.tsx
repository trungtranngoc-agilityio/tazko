import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { Link, useNavigate } from "react-router";
import { t } from "@/shared/i18n";
import type { Company } from "../api";
import { Initials } from "./Initials";

interface Props {
  companies: Company[];
  current: Company;
  superAdmin: boolean;
}

/**
 * The company card at the top of the sidebar and its menu (prototype rail):
 * the person's own companies with a check on the current one, a suspended one
 * shown but not openable (M1.md Q2), and Admin console below a line for super
 * admins. Escape and a click outside close it; focus moves in and back.
 */
export function CompanySwitcher({ companies, current, superAdmin }: Props) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLUListElement>(null);

  useEffect(() => {
    if (!open) return;
    menu.current
      ?.querySelector<HTMLElement>('[role="menuitem"]:not([aria-disabled="true"])')
      ?.focus();
    const outside = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", outside);
    return () => document.removeEventListener("mousedown", outside);
  }, [open]);

  function close() {
    setOpen(false);
    button.current?.focus();
  }

  function go(company: Company) {
    if (company.status === "suspended") return;
    setOpen(false);
    navigate(`/c/${company.slug}`);
  }

  function keys(event: KeyboardEvent<HTMLUListElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      close();
      return;
    }
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    event.preventDefault();
    const items = [
      ...(menu.current?.querySelectorAll<HTMLElement>(
        '[role="menuitem"]:not([aria-disabled="true"])',
      ) ?? []),
    ];
    const at = items.indexOf(document.activeElement as HTMLElement);
    const next = event.key === "ArrowDown" ? at + 1 : at - 1;
    items[(next + items.length) % items.length]?.focus();
  }

  return (
    <div ref={root} className="relative">
      <button
        ref={button}
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
          ref={menu}
          role="menu"
          aria-label={t("company.switch")}
          onKeyDown={keys}
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
                onClick={() => go(company)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    go(company);
                  }
                }}
                className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-sm ${
                  suspended ? "cursor-not-allowed text-muted" : "cursor-pointer hover:bg-sunken"
                }`}
              >
                <Initials name={company.name} />
                <span className="flex-1 truncate">{company.name}</span>
                {suspended && <span className="text-xs">{t("company.suspended")}</span>}
                {company.slug === current.slug && (
                  <span aria-hidden="true" className="text-accent">
                    ✓
                  </span>
                )}
              </li>
            );
          })}
          {superAdmin && (
            <>
              <li role="separator" className="my-1 border-t border-line" />
              <li role="none">
                <Link
                  role="menuitem"
                  to="/admin"
                  className="block rounded-md px-2 py-1.5 text-sm hover:bg-sunken"
                >
                  {t("nav.admin")}
                </Link>
              </li>
            </>
          )}
        </ul>
      )}
    </div>
  );
}
