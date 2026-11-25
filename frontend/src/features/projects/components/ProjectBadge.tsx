import { Initials } from "@/features/orgs";

const TONES = ["c0", "c1", "c2", "c3", "c4"] as const;
export type ProjectColor = (typeof TONES)[number];
export const PROJECT_COLORS: readonly ProjectColor[] = TONES;

/** The project's square initials in its colour; without one (or with a key
 * this version does not know), the tone the name picks, as for people. */
export function ProjectBadge({
  name,
  color,
  size = "md",
}: {
  name: string;
  color: string | null;
  size?: "md" | "lg";
}) {
  const known = color !== null && (TONES as readonly string[]).includes(color);
  return (
    <Initials name={name} size={size === "lg" ? "xl" : "lg"} tone={known ? color : undefined} />
  );
}
