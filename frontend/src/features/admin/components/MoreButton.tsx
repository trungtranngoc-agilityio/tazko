import { errorText, t } from "@/shared/i18n";

/** Show more under a paged list; nothing when there is no next page. */
export function MoreButton({
  next,
  problem,
  onClick,
}: {
  next: number | null;
  problem: string | null;
  onClick: () => void;
}) {
  if (next === null) return null;
  return (
    <div className="mt-4 flex items-center gap-3">
      <button
        type="button"
        onClick={onClick}
        className="h-9 rounded-md border border-line bg-surface px-4 font-semibold hover:bg-sunken"
      >
        {t("admin.more")}
      </button>
      {problem && (
        <p role="alert" className="text-sm text-danger">
          {errorText(problem)}
        </p>
      )}
    </div>
  );
}
