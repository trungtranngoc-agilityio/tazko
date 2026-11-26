import { useId } from "react";
import { Link, Navigate } from "react-router";
import { StarredBoards, starredBoards } from "@/features/boards";
import { useCompany } from "@/features/orgs";
import { ProjectCard, myProjects } from "@/features/projects";
import { errorText, t } from "@/shared/i18n";
import { useAsync } from "@/shared/lib/useAsync";
import { Icon } from "@/shared/ui/Icon";

// Company home (prototype Your projects): the projects the person is in, and
// the empty state when there are none. Company owners get Manage projects.
export function CompanyHomePage() {
  const { company } = useCompany();
  const [projects, reload] = useAsync(() => myProjects(company.slug), `projects:${company.slug}`);
  const [starred, reloadStarred] = useAsync(
    () => starredBoards(company.slug),
    `starred:${company.slug}`,
  );
  const yours = useId();
  const owner = company.role === "owner";

  if (projects.kind === "failed" && projects.status === 401) {
    return <Navigate to="/signin" replace />;
  }
  return (
    <>
      <div className="flex flex-wrap items-start gap-4">
        <div className="min-w-0 flex-1">
          <h1 className="text-[1.75rem] font-bold">{t("projects.title")}</h1>
          <p className="mt-1 text-muted">{t("projects.lead", { company: company.name })}</p>
        </div>
        {owner && (
          <Link
            to={`/c/${company.slug}/manage`}
            className="flex h-10 items-center gap-2 rounded-md border border-line bg-surface px-4 font-semibold hover:bg-sunken"
          >
            <Icon name="building" />
            {t("nav.manage")}
          </Link>
        )}
      </div>
      {projects.kind === "loading" && (
        <p role="status" className="mt-8 text-muted">
          {t("session.loading")}
        </p>
      )}
      {projects.kind === "failed" && (
        <div className="mt-8">
          <p role="alert">{errorText(projects.code)}</p>
          <button
            type="button"
            onClick={reload}
            className="mt-3 h-9 rounded-md border border-line bg-surface px-4 font-semibold hover:bg-sunken"
          >
            {t("session.retry")}
          </button>
        </div>
      )}
      {projects.kind === "ready" && projects.value.length === 0 && (
        <Empty owner={owner} company={company.name} />
      )}
      {projects.kind === "ready" && projects.value.length > 0 && starred.kind === "ready" && (
        <div className="mt-8">
          <StarredBoards key={company.slug} slug={company.slug} boards={starred.value} />
        </div>
      )}
      {projects.kind === "ready" && projects.value.length > 0 && starred.kind === "failed" && (
        <div className="mt-8 flex items-center gap-3 text-sm">
          <p role="alert">{t("boards.starredFailed")}</p>
          <button
            type="button"
            onClick={reloadStarred}
            className="h-8 rounded-md border border-line bg-surface px-3 font-semibold hover:bg-sunken"
          >
            {t("session.retry")}
          </button>
        </div>
      )}
      {projects.kind === "ready" && projects.value.length > 0 && (
        <section aria-labelledby={yours} className="mt-8">
          <h2 id={yours} className="mb-3 flex items-center gap-2 font-semibold">
            <Icon name="folder" />
            {t("projects.yours")}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {projects.value.map((card) => (
              <ProjectCard key={card.id} slug={company.slug} card={card} />
            ))}
          </div>
        </section>
      )}
    </>
  );
}

function Empty({ owner, company }: { owner: boolean; company: string }) {
  return (
    <section className="mt-8 rounded-xl border border-dashed border-line px-6 py-14 text-center">
      {/* Three board columns, as in the prototype's empty state. */}
      <svg aria-hidden="true" viewBox="0 0 108 64" className="mx-auto mb-5 h-16 w-28">
        <rect x="0" y="0" width="30" height="64" rx="6" className="fill-accent-soft" />
        <rect x="39" y="0" width="30" height="40" rx="6" className="fill-accent/30" />
        <rect x="78" y="0" width="30" height="52" rx="6" className="fill-accent-soft" />
      </svg>
      <h2 className="font-semibold">{t("projects.empty")}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-muted">
        {owner ? t("projects.emptyOwner") : t("projects.emptyMember", { company })}
      </p>
    </section>
  );
}
