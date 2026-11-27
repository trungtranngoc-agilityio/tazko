import { useState } from "react";
import { Initials } from "@/features/orgs";
import { projectMembers, type Project, type ProjectMember } from "@/features/projects";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { useAsync } from "@/shared/lib/useAsync";
import { Switch } from "@/shared/ui/Switch";
import { restrictsBoards } from "../access";
import { setAccess, type Board } from "../api";

/**
 * Board access (prototype pAccess): who sees the board. Project owners turn
 * the restriction on and off and tick the members who may open it; owners
 * always see it, so they show ticked. Everyone else reads one sentence.
 */
export function BoardAccess({
  slug,
  project,
  board,
  onChange,
}: {
  slug: string;
  project: Project;
  board: Board;
  onChange: (board: Board) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  async function send(restricted: boolean, people: number[]) {
    setBusy(true);
    setProblem(null);
    try {
      onChange(await setAccess(slug, board, restricted, people));
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <p className="mb-2 text-muted">{t("access.hint")}</p>
      {restrictsBoards(project, board) ? (
        <>
          <div className="flex items-center justify-between gap-3.5 border-b border-line py-3">
            <div>
              <b>{t("access.restrict")}</b>
              <small className="block text-muted">{t("access.restrictHint")}</small>
            </div>
            <Switch
              on={board.restricted}
              label={t("access.restrict")}
              disabled={busy}
              onToggle={() => void send(!board.restricted, [])}
            />
          </div>
          {board.restricted && (
            <People
              slug={slug}
              projectId={project.id}
              chosen={board.access ?? []}
              busy={busy}
              onChoose={(people) => void send(true, people)}
            />
          )}
        </>
      ) : (
        <p className="font-semibold">
          {board.restricted ? t("access.isRestricted") : t("access.isOpen")}
        </p>
      )}
      {problem && (
        <p role="alert" className="mt-2 text-danger">
          {problem}
        </p>
      )}
    </>
  );
}

function People({
  slug,
  projectId,
  chosen,
  busy,
  onChoose,
}: {
  slug: string;
  projectId: number;
  chosen: number[];
  busy: boolean;
  onChoose: (people: number[]) => void;
}) {
  const [members] = useAsync(() => projectMembers(slug, projectId), `${slug}:${projectId}`);
  if (members.kind === "loading") {
    return <p className="mt-2 text-muted">{t("session.loading")}</p>;
  }
  if (members.kind === "failed") {
    return (
      <p role="alert" className="mt-2 text-danger">
        {errorText(members.code)}
      </p>
    );
  }
  const toggle = (m: ProjectMember) =>
    onChoose(
      chosen.includes(m.user_id)
        ? chosen.filter((id) => id !== m.user_id)
        : [...chosen, m.user_id].sort((a, b) => a - b),
    );
  return (
    <div className="mt-2">
      {members.value.map((m) => {
        const owner = m.role === "owner";
        return (
          <label
            key={m.user_id}
            className="flex cursor-pointer items-center gap-2 rounded-lg px-1 py-1.5 hover:bg-sunken"
          >
            <input
              type="checkbox"
              checked={owner || chosen.includes(m.user_id)}
              disabled={owner || busy}
              onChange={() => toggle(m)}
              className="accent-accent"
            />
            <Initials name={m.name} />
            <span className="min-w-0 flex-1 truncate">
              {m.name} <small className="text-muted">{t(`project.role.${m.role}`)}</small>
            </span>
          </label>
        );
      })}
      <p className="mt-1 text-muted">{t("access.ownersAlways")}</p>
    </div>
  );
}
