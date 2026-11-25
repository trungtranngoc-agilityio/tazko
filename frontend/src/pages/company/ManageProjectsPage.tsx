import { useState } from "react";
import { Navigate, useNavigate } from "react-router";
import { useMe } from "@/features/auth";
import { companyBase, members, useCompany } from "@/features/orgs";
import { ManageProjectsTable, NewProjectDialog, manageProjects } from "@/features/projects";
import { errorText, t } from "@/shared/i18n";
import { useAsync } from "@/shared/lib/useAsync";
import { Icon } from "@/shared/ui/Icon";

// Manage projects (prototype, company owners): every project with its owners,
// New project, Archive or Restore, Delete. The API answers 403 to anyone else.
export function ManageProjectsPage() {
  const { company } = useCompany();
  if (company.role !== "owner") {
    return (
      <p role="alert" className="text-ink">
        {t("manage.ownersOnly")}
      </p>
    );
  }
  return <ManageProjects />;
}

function ManageProjects() {
  const { company } = useCompany();
  const me = useMe();
  const navigate = useNavigate();
  const slug = company.slug;
  const [rows, reload] = useAsync(() => manageProjects(slug), `manage:${slug}`);
  const [people, reloadPeople] = useAsync(() => members(companyBase(slug)), `members:${slug}`);
  const [creating, setCreating] = useState(false);

  const failed = rows.kind === "failed" ? rows : people.kind === "failed" ? people : null;
  if (failed?.status === 401) return <Navigate to="/signin" replace />;
  return (
    <>
      <div className="flex flex-wrap items-start gap-4">
        <div className="min-w-0 flex-1">
          <h1 className="text-[1.75rem] font-bold">{t("manage.title")}</h1>
          <p className="mt-1 text-muted">{t("manage.lead", { company: company.name })}</p>
        </div>
        <button
          type="button"
          onClick={() => setCreating(true)}
          disabled={people.kind !== "ready"}
          className="flex h-10 items-center gap-2 rounded-md bg-accent px-4 font-semibold text-white disabled:opacity-60"
        >
          <Icon name="plus" />
          {t("manage.new")}
        </button>
      </div>
      <p className="mt-6 rounded-lg bg-sunken px-4 py-3 text-sm text-muted">{t("manage.note")}</p>
      <div className="mt-4">
        {failed ? (
          <div>
            <p role="alert">{errorText(failed.code)}</p>
            <button
              type="button"
              onClick={() => {
                reload();
                reloadPeople();
              }}
              className="mt-3 h-9 rounded-md border border-line bg-surface px-4 font-semibold hover:bg-sunken"
            >
              {t("session.retry")}
            </button>
          </div>
        ) : rows.kind === "ready" && people.kind === "ready" ? (
          <ManageProjectsTable
            slug={slug}
            projects={rows.value}
            people={people.value}
            onChanged={reload}
          />
        ) : (
          <p role="status" className="text-muted">
            {t("session.loading")}
          </p>
        )}
      </div>
      {creating && people.kind === "ready" && (
        <NewProjectDialog
          slug={slug}
          people={people.value}
          meId={me.id}
          onClose={() => setCreating(false)}
          onCreated={(made) => {
            setCreating(false);
            // The creator is in it only if they chose themselves as its owner.
            if (made.role) navigate(`/c/${slug}/p/${made.id}`);
            else reload();
          }}
        />
      )}
    </>
  );
}
