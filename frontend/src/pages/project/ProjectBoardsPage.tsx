import { Navigate, useParams } from "react-router";
import { ProjectBoards, projectBoards } from "@/features/boards";
import { useCompany } from "@/features/orgs";
import { ProjectHeader, project as loadProject, projectMembers } from "@/features/projects";
import { errorText } from "@/shared/i18n";
import { useAsync } from "@/shared/lib/useAsync";
import { Failed, Loading } from "./parts";

// A project's Boards tab (prototype Project boards), where a project opens.
// A company owner outside the project sees the header and is told to join.
export function ProjectBoardsPage() {
  const { company } = useCompany();
  const id = Number(useParams().projectId);
  const slug = company.slug;
  const key = `${slug}:${id}`;
  const [loaded, reload] = useAsync(() => loadProject(slug, id), `project:${key}`);
  const [boards, reloadBoards] = useAsync(() => projectBoards(slug, id), `boards:${key}`);
  const [people] = useAsync(() => projectMembers(slug, id), `pmembers:${key}`);

  if (loaded.kind === "failed" && loaded.status === 401) return <Navigate to="/signin" replace />;
  if (loaded.kind === "failed") return <Failed message={errorText(loaded.code)} onRetry={reload} />;
  if (loaded.kind !== "ready") return <Loading />;
  return (
    <>
      <ProjectHeader
        slug={slug}
        project={loaded.value}
        members={people.kind === "ready" ? people.value.length : null}
      />
      <div className="mt-6">
        {boards.kind === "loading" && <Loading />}
        {boards.kind === "failed" && (
          <Failed message={errorText(boards.code)} onRetry={reloadBoards} />
        )}
        {boards.kind === "ready" && (
          <ProjectBoards key={key} slug={slug} project={loaded.value} boards={boards.value} />
        )}
      </div>
    </>
  );
}
