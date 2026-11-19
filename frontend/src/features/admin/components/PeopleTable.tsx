import { useState } from "react";
import { AccountBadge, Initials } from "@/features/orgs";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { when } from "@/shared/lib/when";
import { setPersonFlags, type Person } from "../api";
import { box, Switch, tableHead } from "./parts";

/** People page table (prototype admin-people): companies, last sign-in, and the
 * Super admin and Active switches. A switch shows what the server answered. */
export function PeopleTable({
  people,
  onChanged,
}: {
  people: Person[];
  onChanged: (person: Person) => void;
}) {
  const [problem, setProblem] = useState<string | null>(null);

  async function flip(person: Person, flags: { is_super_admin?: boolean; active?: boolean }) {
    setProblem(null);
    try {
      onChanged(await setPersonFlags(person.id, flags));
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
    }
  }

  return (
    <>
      {problem && (
        <p role="alert" className="mb-3 text-sm text-danger">
          {problem}
        </p>
      )}
      <div className={box}>
        <table aria-label={t("admin.people")} className="w-full text-sm">
          <thead className={tableHead}>
            <tr>
              <th className="px-5 py-2 font-semibold">{t("members.person")}</th>
              <th className="px-3 py-2 font-semibold">{t("members.account")}</th>
              <th className="px-3 py-2 font-semibold">{t("admin.companiesOf")}</th>
              <th className="px-3 py-2 font-semibold">{t("members.lastSeen")}</th>
              <th className="px-3 py-2 font-semibold">{t("admin.superAdmin")}</th>
              <th className="px-3 py-2 font-semibold">{t("admin.active")}</th>
            </tr>
          </thead>
          <tbody>
            {people.map((person) => {
              const label = person.name || person.email;
              return (
                <tr key={person.id} className="border-t border-line">
                  <td className="px-5 py-2.5">
                    <span className="flex items-center gap-3">
                      <Initials name={label} />
                      <span>
                        <span className="block font-semibold">{person.name}</span>
                        <span className="block text-xs text-muted">{person.email}</span>
                      </span>
                    </span>
                  </td>
                  <td className="px-3">
                    <AccountBadge account={person.account} />
                  </td>
                  <td className="px-3">
                    {person.companies.map((c) => (
                      <span
                        key={c.slug}
                        className="mr-1 inline-block rounded-full bg-sunken px-2 py-0.5 text-xs"
                      >
                        {c.name}
                      </span>
                    ))}
                  </td>
                  <td className="px-3 text-muted">
                    {person.last_seen_at ? when(person.last_seen_at) : t("members.never")}
                  </td>
                  <td className="px-3">
                    <Switch
                      on={person.is_super_admin}
                      label={t("admin.superAdminFor", { name: label })}
                      onToggle={() => void flip(person, { is_super_admin: !person.is_super_admin })}
                    />
                  </td>
                  <td className="px-3">
                    <Switch
                      on={person.active}
                      label={t("admin.activeFor", { name: label })}
                      onToggle={() => void flip(person, { active: !person.active })}
                    />
                  </td>
                </tr>
              );
            })}
            {people.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-4 text-muted">
                  {t("admin.noOne")}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
