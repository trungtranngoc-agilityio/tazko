import { t } from "@/shared/i18n";

export function Loading() {
  return (
    <p role="status" className="text-muted">
      {t("session.loading")}
    </p>
  );
}

export function Failed({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div>
      <p role="alert">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-3 h-9 rounded-md border border-line bg-surface px-4 font-semibold hover:bg-sunken"
      >
        {t("session.retry")}
      </button>
    </div>
  );
}
