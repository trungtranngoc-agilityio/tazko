import { useState } from "react";
import type { Member } from "@/features/orgs";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { Icon } from "@/shared/ui/Icon";
import {
  addProjectMember,
  deleteProject,
  setProjectRole,
  updateProject,
  type ProjectSummary,
} from "../api";

/** Every project of the company for its owners (prototype Manage projects):
 * owners with "+ Owner", member and board counts, Archive or Restore, Delete.
 * Deleting asks first; archiving does not (the prototype's one click). */
export function ManageProjectsTable({
  slug,
  projects,
  people,
  onChanged,
}: {
  slug: string;
  projects: ProjectSummary[];
  people: Member[];
  onChanged: () => void;
}) {
  const [problem, setProblem] = useState<string | null>(null);

  async function act(run: () => Promise<unknown>) {
    setProblem(null);
    try {
      await run();
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
    }
    onChanged();
  }

  async function makeOwner(project: ProjectSummary, userId: number) {
    try {
      await addProjectMember(slug, project.id, userId, "owner");
    } catch (error) {
      // Already in the project as a member or observer: promote them instead.
      if (!(error instanceof ApiError) || error.code !== "ALREADY_PROJECT_MEMBER") throw error;
      await setProjectRole(slug, project.id, userId, "owner");
    }
  }

  function remove(project: ProjectSummary) {
    if (!window.confirm(t("manage.confirmDelete", { name: project.name }))) return;
    void act(() => deleteProject(slug, project.id));
  }

  return (
    <section className="rounded-xl border border-line bg-surface">
      {problem && (
        <p role="alert" className="px-5 pt-4 text-sm text-danger">
          {problem}
        </p>
      )}
      {projects.length === 0 ? (
        <p className="px-5 py-6 text-sm text-muted">{t("manage.none")}</p>
      ) : (
        <table aria-label={t("manage.title")} className="w-full text-sm">
          <thead className="bg-sunken text-left text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-5 py-2 font-semibold">{t("manage.project")}</th>
              <th className="px-3 py-2 font-semibold">{t("manage.owners")}</th>
              <th className="px-3 py-2 text-right font-semibold">{t("manage.members")}</th>
              <th className="px-3 py-2 text-right font-semibold">{t("manage.boards")}</th>
              <th className="px-3 py-2 font-semibold">{t("manage.status")}</th>
              <th className="px-3 py-2">
                <span className="sr-only">{t("manage.actions")}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {projects.map((project) => {
              const owners = new Set(project.owners.map((o) => o.user_id));
              const candidates = people.filter((p) => !owners.has(p.user_id));
              const archived = project.archived_at !== null;
              return (
                <tr key={project.id} className="border-t border-line">
                  <td className="max-w-64 truncate px-5 py-3 font-semibold">{project.name}</td>
                  <td className="px-3">
                    <span className="flex flex-wrap items-center gap-2">
                      {project.owners.length === 0 ? (
                        <span className="rounded-full bg-warning/20 px-2 py-0.5 text-xs font-semibold text-ink">
                          {t("manage.noOwner")}
                        </span>
                      ) : (
                        project.owners.map((o) => (
                          <span
                            key={o.user_id}
                            className="rounded-full bg-sunken px-2 py-0.5 text-xs"
                          >
                            {o.name}
                          </span>
                        ))
                      )}
                      {!archived && candidates.length > 0 && (
                        <OwnerPicker
                          project={project.name}
                          candidates={candidates}
                          onPick={(userId) => void act(() => makeOwner(project, userId))}
                        />
                      )}
                    </span>
                  </td>
                  <td className="px-3 text-right">{project.members}</td>
                  <td className="px-3 text-right">{project.boards}</td>
                  <td className="px-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-semibold ${archived ? "bg-sunken text-muted" : "bg-success/15 text-success"}`}
                    >
                      {t(archived ? "manage.archived" : "manage.active")}
                    </span>
                  </td>
                  <td className="px-3">
                    <span className="flex justify-end gap-2">
                      <button
                        type="button"
                        aria-label={t(archived ? "manage.restoreOf" : "manage.archiveOf", {
                          name: project.name,
                        })}
                        onClick={() =>
                          void act(() => updateProject(slug, project.id, { archived: !archived }))
                        }
                        className="h-8 rounded-md border border-line px-3 hover:bg-sunken"
                      >
                        {t(archived ? "manage.restore" : "manage.archive")}
                      </button>
                      <button
                        type="button"
                        aria-label={t("manage.deleteOf", { name: project.name })}
                        onClick={() => remove(project)}
                        className="h-8 rounded-md border border-danger px-3 text-danger hover:bg-danger/10"
                      >
                        {t("manage.delete")}
                      </button>
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </section>
  );
}

/** "+ Owner" (prototype): a company member becomes one of the project's owners. */
function OwnerPicker({
  project,
  candidates,
  onPick,
}: {
  project: string;
  candidates: Member[];
  onPick: (userId: number) => void;
}) {
  return (
    <label className="relative flex items-center gap-1 text-muted hover:text-ink">
      <Icon name="plus" className="size-4" />
      <span>{t("manage.addOwner")}</span>
      <select
        aria-label={t("manage.addOwnerTo", { name: project })}
        value=""
        onChange={(e) => onPick(Number(e.target.value))}
        className="absolute inset-0 cursor-pointer opacity-0"
      >
        <option value="" disabled>
          {t("manage.addOwner")}
        </option>
        {candidates.map((p) => (
          <option key={p.user_id} value={p.user_id}>
            {p.name || p.email}
          </option>
        ))}
      </select>
    </label>
  );
}
