import { createContext, useContext } from "react";
import type { Me } from "./api";

/** The signed-in person, provided by RequireSession. */
export const Session = createContext<Me | null>(null);

/** The signed-in person; only inside RequireSession. */
export function useMe(): Me {
  const me = useContext(Session);
  if (!me) throw new Error("useMe() outside RequireSession");
  return me;
}
