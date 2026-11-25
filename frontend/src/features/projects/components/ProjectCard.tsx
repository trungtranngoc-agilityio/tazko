import { Link } from "react-router";
import { Initials } from "@/features/orgs";
import { t } from "@/shared/i18n";
import type { ProjectCard as Card } from "../api";
import { ProjectBadge } from "./ProjectBadge";

/** One project on Your projects (prototype .pgrid): badge, name, description,
 * up to four people, the boards you can open, and your role. */
export function ProjectCard({ slug, card }: { slug: string; card: Card }) {
  return (
    <Link
      to={`/c/${slug}/p/${card.id}`}
      className="flex flex-col gap-3 rounded-xl border border-line bg-surface p-4 hover:border-accent"
    >
      <span className="flex items-center gap-3">
        <ProjectBadge name={card.name} color={card.color} />
        <span className="truncate text-lg font-semibold">{card.name}</span>
      </span>
      {card.description && (
        <span className="line-clamp-2 text-sm text-muted">{card.description}</span>
      )}
      <span className="mt-auto flex items-center gap-2 text-sm text-muted">
        <span
          className="flex gap-1"
          aria-label={t(card.members === 1 ? "projects.person" : "projects.people", {
            count: card.members,
          })}
        >
          {card.people.map((p) => (
            <Initials key={p.user_id} name={p.name} />
          ))}
        </span>
        <span>
          {t(card.boards === 1 ? "projects.board" : "projects.boards", { count: card.boards })}
        </span>
        {card.archived_at && (
          <span className="rounded-full bg-sunken px-2 py-0.5 text-xs">
            {t("projects.archived")}
          </span>
        )}
        {card.role && (
          <span className="ml-auto rounded-full bg-accent-soft px-2 py-0.5 text-xs font-semibold text-accent">
            {t(`rolePill.${card.role}`)}
          </span>
        )}
      </span>
    </Link>
  );
}
