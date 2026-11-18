import { useEffect, useState, type ReactNode } from "react";
import { Navigate } from "react-router";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { currentUser, type Me } from "../api";
import { Session } from "../session";

type State =
  | { kind: "loading" }
  | { kind: "signed-out" }
  | { kind: "failed"; message: string }
  | { kind: "signed-in"; me: Me };

/** Shows its children to a signed-in person; anyone else goes to /signin. */
export function RequireSession({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let live = true;
    currentUser().then(
      (me) => {
        if (live) setState({ kind: "signed-in", me });
      },
      (error: unknown) => {
        if (!live) return;
        if (error instanceof ApiError && error.status === 401) {
          setState({ kind: "signed-out" });
        } else {
          const code = error instanceof ApiError ? error.code : "UNKNOWN";
          setState({ kind: "failed", message: errorText(code) });
        }
      },
    );
    return () => {
      live = false;
    };
  }, [attempt]);

  if (state.kind === "signed-out") return <Navigate to="/signin" replace />;
  if (state.kind === "signed-in")
    return <Session.Provider value={state.me}>{children}</Session.Provider>;
  return (
    <div className="grid min-h-screen place-items-center bg-bg px-4 text-center text-muted">
      {state.kind === "loading" ? (
        <p role="status">{t("session.loading")}</p>
      ) : (
        <div>
          <p role="alert" className="text-ink">
            {state.message}
          </p>
          <button
            type="button"
            onClick={() => {
              setState({ kind: "loading" });
              setAttempt((n) => n + 1);
            }}
            className="mt-4 h-9 rounded-md border border-line bg-surface px-4 font-semibold text-ink hover:bg-sunken"
          >
            {t("session.retry")}
          </button>
        </div>
      )}
    </div>
  );
}
