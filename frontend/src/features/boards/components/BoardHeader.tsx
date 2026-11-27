import { useState } from "react";
import { Link } from "react-router";
import type { Project } from "@/features/projects";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { Icon } from "@/shared/ui/Icon";
import { InlineEdit } from "@/shared/ui/InlineEdit";
import { Popover } from "@/shared/ui/Popover";
import { editsBoards, editsCards, restrictsBoards } from "../access";
import { setStar, updateBoard, type Board } from "../api";
import { BoardAccess } from "./BoardAccess";
import { BoardMenu } from "./BoardMenu";

/**
 * The bars above a board's lists (prototype .bt, .bh and .ro-banner): the way
 * back to the company and the project, the board name (renamed in place by
 * owners and members), the star, who sees the board, the board menu, and one
 * note when the board is read-only.
 */
export function BoardHeader({
  slug,
  company,
  project,
  board,
  onChange,
}: {
  slug: string;
  company: string;
  project: Project;
  board: Board;
  onChange: (update: Board | ((board: Board) => Board)) => void;
}) {
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [panel, setPanel] = useState<"access" | "menu" | null>(null);
  const projectPath = `/c/${slug}/p/${project.id}/boards`;

  async function attempt(action: () => Promise<Board | ((board: Board) => Board)>) {
    setProblem(null);
    setBusy(true);
    try {
      onChange(await action());
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
    } finally {
      setBusy(false);
    }
  }
  const save = (changes: { name?: string; archived?: boolean }) =>
    attempt(() => updateBoard(slug, board, changes));
  const star = () =>
    attempt(async () => {
      const on = !board.starred;
      await setStar(slug, board, on);
      // Only the star changes: another change may have landed while this one ran.
      return (latest: Board) => ({ ...latest, starred: on });
    });
  const restricts = restrictsBoards(project, board);
  const closes = editsCards(project, board);

  return (
    <>
      <div className="flex flex-wrap items-center gap-2.5 bg-[rgb(12_12_32/0.5)] px-4 py-[7px] text-white">
        <Link
          to={projectPath}
          aria-label={t("board.backToProject")}
          className="grid size-8 place-items-center rounded-md hover:bg-white/20"
        >
          <Icon name="back" />
        </Link>
        <nav className="flex min-w-0 items-center gap-2 text-[0.88rem] opacity-95">
          <Link to={`/c/${slug}`} className="truncate hover:underline">
            {company}
          </Link>
          <span aria-hidden="true" className="opacity-60">
            {t("board.crumbSeparator")}
          </span>
          <Link to={projectPath} className="truncate hover:underline">
            {project.name}
          </Link>
        </nav>
      </div>
      <div className="flex flex-wrap items-center gap-2.5 bg-[rgb(12_12_32/0.32)] px-4 py-2 text-white">
        <InlineEdit
          as="h1"
          value={board.name}
          label={t("board.nameLabel")}
          title={t("board.rename")}
          editable={editsCards(project, board)}
          maxLength={100}
          onSave={(name) => void save({ name })}
          className="min-w-0 py-1 text-[1.15rem] font-bold [text-shadow:0_1px_2px_rgb(0_0_0/0.25)]"
          inputClassName="h-9 w-72 text-[1.05rem] font-bold"
        />
        <button
          type="button"
          aria-label={t("board.star")}
          title={t("board.star")}
          aria-pressed={board.starred}
          disabled={busy}
          onClick={() => void star()}
          className={`grid size-8 place-items-center rounded-md hover:bg-white/20 ${board.starred ? "[&_svg]:fill-amber-400 [&_svg]:stroke-amber-400" : ""}`}
        >
          <Icon name="star" />
        </button>
        <span className="relative">
          <button
            type="button"
            onClick={() => setPanel(panel === "access" ? null : "access")}
            className="inline-flex h-6 items-center gap-1.5 rounded-full bg-white/20 px-2.5 text-[0.78rem] font-semibold hover:bg-white/30"
          >
            <Icon name={board.restricted ? "lock" : "users"} className="size-3.5" />
            {board.restricted ? t("board.restricted") : t("board.wholeProject")}
          </button>
          {panel === "access" && (
            <Popover
              title={t("access.title")}
              closeLabel={t("access.close")}
              onClose={() => setPanel(null)}
              className="left-0 w-[340px]"
            >
              <BoardAccess slug={slug} project={project} board={board} onChange={onChange} />
            </Popover>
          )}
        </span>
        {problem && (
          <p role="alert" className="rounded-md bg-surface px-2 py-1 text-sm text-danger">
            {problem}
          </p>
        )}
        {(restricts || closes) && (
          <button
            type="button"
            aria-label={t("board.menu")}
            aria-expanded={panel === "menu"}
            onClick={() => setPanel(panel === "menu" ? null : "menu")}
            className="ml-auto grid size-8 place-items-center rounded-md hover:bg-white/20"
          >
            <Icon name="more" />
          </button>
        )}
      </div>
      {panel === "menu" && (
        <BoardMenu
          onAccess={restricts ? () => setPanel("access") : null}
          onCloseBoard={
            closes
              ? () => {
                  setPanel(null);
                  void save({ archived: true });
                }
              : null
          }
          onClose={() => setPanel(null)}
        />
      )}
      <ReadOnlyNote
        project={project}
        board={board}
        busy={busy}
        onReopen={() => void save({ archived: false })}
      />
    </>
  );
}

function ReadOnlyNote({
  project,
  board,
  busy,
  onReopen,
}: {
  project: Project;
  board: Board;
  busy: boolean;
  onReopen: () => void;
}) {
  // Only someone who may reopen is told to; an observer hears they only read.
  const reopens = !project.archived_at && board.archived_at !== null && editsBoards(project);
  const note = project.archived_at
    ? t("board.projectArchived")
    : reopens
      ? t("board.closedNote")
      : project.role === "observer"
        ? t("board.observer")
        : null;
  if (!note) return null;
  return (
    <div className="flex flex-wrap items-center gap-3 bg-warn-bg px-4 py-1.5 text-[0.85rem] font-semibold text-warn">
      <span>{note}</span>
      {reopens && (
        <button
          type="button"
          disabled={busy}
          onClick={onReopen}
          className="h-7 rounded-md border border-current px-3 hover:bg-black/5 disabled:opacity-60"
        >
          {t("board.reopen")}
        </button>
      )}
    </div>
  );
}
