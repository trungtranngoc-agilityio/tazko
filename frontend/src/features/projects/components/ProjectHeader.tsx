import { Link, NavLink } from "react-router";
import { t } from "@/shared/i18n";
import { editsSettings } from "../access";
import type { Project } from "../api";
import { ProjectBadge } from "./ProjectBadge";

/** The top of a project's pages (prototype): breadcrumb, badge, name and
 * description, the person's role, and the tabs. Settings is a project
 * owner's tab. */
export function ProjectHeader({
  slug,
  project,
  members,
}: {
  slug: string;
  project: Project;
  members: number | null;
}) {
  const base = `/c/${slug}/p/${project.id}`;
  const tab = ({ isActive }: { isActive: boolean }) =>
    `-mb-px border-b-2 px-3.5 py-2.5 ${isActive ? "border-accent font-semibold text-accent" : "border-transparent text-muted hover:text-ink"}`;
  return (
    <header>
      <nav aria-label={t("project.breadcrumb")} className="text-sm text-muted">
        <Link to={`/c/${slug}`} className="underline">
          {t("nav.projects")}
        </Link>{" "}
        / {project.name}
      </nav>
      <div className="mt-3 flex items-start gap-3">
        <ProjectBadge name={project.name} color={project.color} size="lg" />
        <div className="min-w-0">
          <h1 className="flex flex-wrap items-center gap-3 text-[1.75rem] font-bold leading-tight">
            {project.name}
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${project.role === "owner" ? "bg-accent-soft text-accent" : "bg-sunken text-muted"}`}
            >
              {t(project.role ? `project.role.${project.role}` : "project.role.companyOwner")}
            </span>
            {project.archived_at && (
              <span className="rounded-full bg-sunken px-2.5 py-0.5 text-xs font-semibold text-muted">
                {t("projects.archived")}
              </span>
            )}
          </h1>
          {project.description && <p className="text-muted">{project.description}</p>}
        </div>
      </div>
      <nav aria-label={t("project.tabs")} className="mt-5 flex border-b border-line text-sm">
        <NavLink to={`${base}/boards`} className={tab}>
          {t("project.boards")}
        </NavLink>
        <NavLink to={`${base}/members`} className={tab}>
          {members === null ? t("project.members") : t("project.membersCount", { count: members })}
        </NavLink>
        {editsSettings(project) && (
          <NavLink to={`${base}/settings`} className={tab}>
            {t("project.settings")}
          </NavLink>
        )}
      </nav>
      {project.archived_at && (
        <p role="note" className="mt-4 rounded-lg bg-sunken px-4 py-3 text-sm text-muted">
          {t("project.archivedNote")}
        </p>
      )}
    </header>
  );
}
