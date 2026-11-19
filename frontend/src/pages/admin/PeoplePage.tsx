import { useState } from "react";
import { Navigate } from "react-router";
import { LoadFailed, Loading, PageHead, PeopleTable, people, usePages } from "@/features/admin";
import { t } from "@/shared/i18n";
import { MoreButton } from "./MoreButton";

// Console: People (prototype admin-people). The search runs on the server,
// since only one page of people is loaded at a time.
export function PeoplePage() {
  const [q, setQ] = useState("");
  const [attempt, setAttempt] = useState(0);
  const { pages, showMore, replace } = usePages(
    (after) => people(q, after),
    `people:${attempt}:${q.trim()}`,
  );

  if (pages.kind === "failed" && pages.status === 401) return <Navigate to="/signin" replace />;
  return (
    <>
      <PageHead title={t("admin.people")} lead={t("admin.peopleLead")}>
        <input
          type="search"
          value={q}
          maxLength={100}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t("admin.searchPlaceholder")}
          aria-label={t("admin.searchPeople")}
          className="h-10 w-64 max-w-full rounded-md border border-line bg-surface px-3"
        />
      </PageHead>
      {pages.kind === "loading" && <Loading />}
      {pages.kind === "failed" && (
        <LoadFailed code={pages.code} onRetry={() => setAttempt((n) => n + 1)} />
      )}
      {pages.kind === "ready" && (
        <>
          <PeopleTable
            people={pages.items}
            onChanged={(person) => replace((p) => p.id === person.id, person)}
          />
          <MoreButton next={pages.next} problem={pages.more} onClick={showMore} />
        </>
      )}
    </>
  );
}
