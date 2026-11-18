import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/shared/api";

export type Async<T> =
  | { kind: "loading" }
  | { kind: "failed"; code: string; status: number }
  | { kind: "ready"; value: T };

/**
 * Load something once per `key`, and again on `reload()`. A failure keeps the
 * API error code (D19) so the screen can explain it with errorText(code).
 */
export function useAsync<T>(load: () => Promise<T>, key: string): [Async<T>, () => void] {
  const [state, setState] = useState<Async<T>>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let live = true;
    setState((current) => (current.kind === "ready" ? current : { kind: "loading" }));
    load().then(
      (value) => {
        if (live) setState({ kind: "ready", value });
      },
      (error: unknown) => {
        if (!live) return;
        const api = error instanceof ApiError ? error : null;
        setState({ kind: "failed", code: api?.code ?? "UNKNOWN", status: api?.status ?? 0 });
      },
    );
    return () => {
      live = false;
    };
    // `load` changes every render; `key` and `attempt` say when to load again.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, attempt]);

  const reload = useCallback(() => setAttempt((n) => n + 1), []);
  return [state, reload];
}
