import { useEffect, useState, type ReactNode } from "react";
import { Navigate } from "react-router";
import { ApiError } from "@/shared/api";
import { currentUser, type Me } from "../api";

type State =
  { kind: "loading" } | { kind: "signed-out" } | { kind: "failed" } | { kind: "signed-in"; me: Me };

/** Shows its children to a signed-in person; anyone else goes to /signin. */
export function RequireSession({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let live = true;
    currentUser().then(
      (me) => {
        if (live) setState({ kind: "signed-in", me });
      },
      (error: unknown) => {
        if (!live) return;
        const signedOut = error instanceof ApiError && error.status === 401;
        setState({ kind: signedOut ? "signed-out" : "failed" });
      },
    );
    return () => {
      live = false;
    };
  }, []);

  if (state.kind === "loading") return null;
  if (state.kind === "signed-out") return <Navigate to="/signin" replace />;
  if (state.kind === "failed") throw new Error("could not load the signed-in person");
  return children;
}
