import { useState } from "react";
import { Link } from "react-router";
import type { Project } from "@/features/projects";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { Icon } from "@/shared/ui/Icon";
import { InlineEdit } from "@/shared/ui/InlineEdit";
import { editsBoards, editsCards } from "../access";
import { updateBoard, type Board } from "../api";

/**
 * The bars above a board's lists (prototype .bt, .bh and .ro-banner): the way
 * back to the company and the project, the board name (renamed in place by
 * owners and members), and one note when the board is read-only.
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
  onChange: (board: Board) => void;
}) {
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const projectPath = `/c/${slug}/p/${project.id}/boards`;

  async function save(changes: { name?: string; archived?: boolean }) {
    setProblem(null);
    setBusy(true);
    try {
      onChange(await updateBoard(slug, board, changes));
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
    } finally {
      setBusy(false);
    }
  }

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
        {problem && (
          <p role="alert" className="rounded-md bg-surface px-2 py-1 text-sm text-danger">
            {problem}
          </p>
        )}
      </div>
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
