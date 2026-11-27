import { useState } from "react";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { boardPath, setStar, type Board } from "../api";
import { BoardTile } from "./BoardTile";
import { Grid, Section } from "./Section";

/** Starred boards on Your projects: the open boards you starred, across your
 * projects. Unstarring one takes it off; the section goes when none is left. */
export function StarredBoards({ slug, boards: loaded }: { slug: string; boards: Board[] }) {
  const [boards, setBoards] = useState(loaded);
  const [problem, setProblem] = useState<string | null>(null);

  async function unstar(board: Board) {
    setProblem(null);
    try {
      await setStar(slug, board, false);
      setBoards((all) => all.filter((b) => b.id !== board.id));
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
    }
  }

  if (boards.length === 0) return null;
  return (
    <Section icon="star" title={t("projects.starred")}>
      {problem && (
        <p role="alert" className="mb-3 text-danger">
          {problem}
        </p>
      )}
      <Grid>
        {boards.map((b) => (
          <BoardTile key={b.id} board={b} to={boardPath(slug, b)} onStar={() => void unstar(b)} />
        ))}
      </Grid>
    </Section>
  );
}
