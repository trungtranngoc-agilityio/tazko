import { useState } from "react";
import { Link, Navigate, useParams } from "react-router";
import { BoardHeader, getBoard, type Board } from "@/features/boards";
import { BoardLists, boardLists, type List } from "@/features/cards";
import { useCompany } from "@/features/orgs";
import { project as loadProject, type Project } from "@/features/projects";
import { errorText, t } from "@/shared/i18n";
import { useAsync } from "@/shared/lib/useAsync";

// A board (prototype Board): the bars on top and its lists, filling the
// window on the board's background.
export function BoardPage() {
  const { company } = useCompany();
  const params = useParams();
  const projectId = Number(params.projectId);
  const boardId = Number(params.boardId);
  const slug = company.slug;
  const key = `${slug}:${projectId}:${boardId}`;
  const [project, reloadProject] = useAsync(() => loadProject(slug, projectId), `project:${key}`);
  const [board, reloadBoard] = useAsync(() => getBoard(slug, projectId, boardId), `board:${key}`);
  const [lists, reloadLists] = useAsync(
    () => boardLists(slug, { id: boardId, project_id: projectId }),
    `lists:${key}`,
  );
  const states = [project, board, lists];
  const reload = () => {
    if (project.kind === "failed") reloadProject();
    if (board.kind === "failed") reloadBoard();
    if (lists.kind === "failed") reloadLists();
  };
  const failed = states.find((s) => s.kind === "failed");

  if (failed?.kind === "failed" && failed.status === 401) return <Navigate to="/signin" replace />;
  const back = `/c/${slug}/p/${projectId}/boards`;
  if (board.kind === "failed" && board.status === 404) return <Missing to={back} />;
  if (failed?.kind === "failed") {
    // A refusal (403) stays a refusal; only other failures may clear on a retry.
    const retry = failed.status !== 403 && failed.status !== 404;
    return (
      <div className="p-7">
        <p role="alert">{errorText(failed.code)}</p>
        <div className="mt-3 flex items-center gap-4">
          {retry && (
            <button
              type="button"
              onClick={reload}
              className="h-9 rounded-md border border-line bg-surface px-4 font-semibold hover:bg-sunken"
            >
              {t("session.retry")}
            </button>
          )}
          <BackLink to={back} />
        </div>
      </div>
    );
  }
  if (project.kind !== "ready" || board.kind !== "ready" || lists.kind !== "ready") {
    return (
      <p role="status" className="p-7 text-muted">
        {t("session.loading")}
      </p>
    );
  }
  return (
    <Screen
      key={key}
      slug={slug}
      company={company.name}
      project={project.value}
      board={board.value}
      lists={lists.value}
    />
  );
}

function Screen({
  slug,
  company,
  project,
  board: loaded,
  lists,
}: {
  slug: string;
  company: string;
  project: Project;
  board: Board;
  lists: List[];
}) {
  const [board, setBoard] = useState(loaded);
  return (
    <div className={`board-bg-${board.background ?? "dusk"} flex h-screen min-w-0 flex-col`}>
      <BoardHeader
        slug={slug}
        company={company}
        project={project}
        board={board}
        onChange={setBoard}
      />
      <BoardLists lists={lists} />
    </div>
  );
}

function Missing({ to }: { to: string }) {
  return (
    <div className="p-7">
      <h1 className="text-lg font-semibold">{t("board.notFound")}</h1>
      <p className="mt-2">
        <BackLink to={to} />
      </p>
    </div>
  );
}

function BackLink({ to }: { to: string }) {
  return (
    <Link to={to} className="text-accent hover:underline">
      {t("board.backToProject")}
    </Link>
  );
}
