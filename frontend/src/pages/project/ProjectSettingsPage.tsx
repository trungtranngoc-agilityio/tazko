import { useState } from "react";
import { Navigate, useParams } from "react-router";
import { useCompany } from "@/features/orgs";
import {
  ProjectHeader,
  ProjectSettings,
  editsSettings,
  project as loadProject,
  projectMembers,
  type Project,
} from "@/features/projects";
import { errorText } from "@/shared/i18n";
import { useAsync } from "@/shared/lib/useAsync";
import { Failed, Loading } from "./parts";

// A project's settings (prototype Project settings), for its owners. Anyone
// else who opens the address is sent to the members page, which they can see.
export function ProjectSettingsPage() {
  const { company } = useCompany();
  const id = Number(useParams().projectId);
  const slug = company.slug;
  const key = `${slug}:${id}`;
  const [loaded, reload] = useAsync(() => loadProject(slug, id), `project:${key}`);
  const [people] = useAsync(() => projectMembers(slug, id), `pmembers:${key}`);
  const [saved, setSaved] = useState<Project | null>(null);

  if (loaded.kind === "failed" && loaded.status === 401) return <Navigate to="/signin" replace />;
  if (loaded.kind === "failed") return <Failed message={errorText(loaded.code)} onRetry={reload} />;
  if (loaded.kind !== "ready") return <Loading />;
  const p = saved?.id === id ? saved : loaded.value;
  if (!editsSettings(p)) return <Navigate to={`/c/${slug}/p/${id}/members`} replace />;
  return (
    <>
      <ProjectHeader
        slug={slug}
        project={p}
        members={people.kind === "ready" ? people.value.length : null}
      />
      <div className="mt-6">
        <ProjectSettings
          key={p.id}
          slug={slug}
          project={p}
          companyOwner={company.role === "owner"}
          onSaved={setSaved}
        />
      </div>
    </>
  );
}
