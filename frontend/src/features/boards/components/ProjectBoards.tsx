import { useState } from "react";
import type { Project } from "@/features/projects";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { Icon } from "@/shared/ui/Icon";
import { createsBoards, editsBoards } from "../access";
import { setStar, updateBoard, type Board } from "../api";
import { BoardTile } from "./BoardTile";
import { NewBoardDialog } from "./NewBoardDialog";
import { Grid, Section } from "./Section";

// The API lists boards by name; a new one goes where a reload would put it.
const byName = (boards: Board[]) =>
  [...boards].sort(
    (a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }) || a.id - b.id,
  );

/** A project's Boards tab (prototype pBoards): Starred, All boards with
 * Create new board, and the closed boards on request with Reopen. */
export function ProjectBoards({
  slug,
  project,
  boards: loaded,
}: {
  slug: string;
  project: Project;
  boards: Board[];
}) {
  const [boards, setBoards] = useState(loaded);
  const [creating, setCreating] = useState(false);
  const [showClosed, setShowClosed] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const open = boards.filter((b) => !b.archived_at);
  const closed = boards.filter((b) => b.archived_at);
  const starred = open.filter((b) => b.starred);

  const replace = (next: Board) =>
    setBoards((all) => all.map((b) => (b.id === next.id ? next : b)));
  async function run(action: () => Promise<void>) {
    setProblem(null);
    try {
      await action();
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
    }
  }
  const star = (board: Board, on: boolean) =>
    run(async () => {
      await setStar(slug, board, on);
      replace({ ...board, starred: on });
    });
  const reopen = (board: Board) =>
    run(async () => replace(await updateBoard(slug, board, { archived: false })));
  const tiles = (list: Board[]) =>
    list.map((b) => <BoardTile key={b.id} board={b} onStar={(on) => void star(b, on)} />);

  return (
    <div className="mt-6">
      {closed.length > 0 && (
        <div className="mb-4">
          <button
            type="button"
            onClick={() => setShowClosed((v) => !v)}
            className="h-9 rounded-md px-3 text-sm font-semibold text-muted hover:bg-sunken"
          >
            {t(showClosed ? "boards.hideClosed" : "boards.showClosed", { count: closed.length })}
          </button>
        </div>
      )}
      {problem && (
        <p role="alert" className="mb-4 text-danger">
          {problem}
        </p>
      )}
      {starred.length > 0 && (
        <Section icon="star" title={t("boards.starred")}>
          <Grid>{tiles(starred)}</Grid>
        </Section>
      )}
      <Section icon="board" title={t("boards.all")}>
        <Grid>
          {tiles(open)}
          {createsBoards(project) && (
            <button
              type="button"
              onClick={() => setCreating(true)}
              className="flex h-[104px] items-center justify-center gap-1.5 rounded-xl border-[1.5px] border-dashed border-line bg-sunken text-muted hover:border-accent hover:text-accent"
            >
              <Icon name="plus" />
              {t("boards.new")}
            </button>
          )}
        </Grid>
        {open.length === 0 && !createsBoards(project) && (
          <p className="text-sm text-muted">{t("boards.none")}</p>
        )}
        {!createsBoards(project) && !project.archived_at && (
          <p className="mt-3 max-w-[60ch] text-[0.82rem] text-muted">{t("boards.ownersOnly")}</p>
        )}
      </Section>
      {showClosed && closed.length > 0 && (
        <Section icon="archive" title={t("boards.closed")}>
          <ul className="divide-y divide-line rounded-xl border border-line bg-surface">
            {closed.map((b) => (
              <li key={b.id} className="flex items-center gap-3 px-4 py-3">
                <b className="min-w-0 flex-1 truncate">{b.name}</b>
                {editsBoards(project) && (
                  <button
                    type="button"
                    aria-label={t("boards.reopenNamed", { name: b.name })}
                    onClick={() => void reopen(b)}
                    className="h-8 rounded-md border border-line px-3 text-sm font-semibold hover:bg-sunken"
                  >
                    {t("boards.reopen")}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}
      {creating && (
        <NewBoardDialog
          slug={slug}
          projectId={project.id}
          background={project.default_background}
          onClose={() => setCreating(false)}
          onCreated={(board) => {
            setBoards((all) => byName([...all, board]));
            setCreating(false);
          }}
        />
      )}
    </div>
  );
}
