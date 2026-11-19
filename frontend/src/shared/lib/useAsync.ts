import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/shared/api";

export type Async<T> =
  | { kind: "loading" }
  | { kind: "failed"; code: string; status: number }
  | { kind: "ready"; value: T };

type Held<T> = { key: string; state: Async<T> };

/** A failed load as the screens show it: the API error code (D19) and status. */
export function toFailure(error: unknown): { code: string; status: number } {
  const api = error instanceof ApiError ? error : null;
  return { code: api?.code ?? "UNKNOWN", status: api?.status ?? 0 };
}

/**
 * Load something once per `key`, and again on `reload()`. A reload keeps the
 * shown value until the new one arrives; a new `key` (another company) starts
 * from loading, so one company's data is never shown under another. A failure
 * keeps the API error code (D19) for errorText(code).
 */
export function useAsync<T>(load: () => Promise<T>, key: string): [Async<T>, () => void] {
  const [held, setHeld] = useState<Held<T>>({ key, state: { kind: "loading" } });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let live = true;
    setHeld((current) =>
      current.key === key && current.state.kind === "ready"
        ? current
        : { key, state: { kind: "loading" } },
    );
    load().then(
      (value) => {
        if (live) setHeld({ key, state: { kind: "ready", value } });
      },
      (error: unknown) => {
        if (live) setHeld({ key, state: { kind: "failed", ...toFailure(error) } });
      },
    );
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `load` is new every render; `key` and `attempt` decide when to load
  }, [key, attempt]);

  const reload = useCallback(() => setAttempt((n) => n + 1), []);
  // Until the effect runs for a new key, the held state belongs to the old one.
  return [held.key === key ? held.state : { kind: "loading" }, reload];
}
