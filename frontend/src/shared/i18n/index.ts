import { en, type MessageKey } from "./en";

/** Look up a UI string. Placeholders like `{name}` are filled from `vars`. */
export function t(key: MessageKey, vars?: Record<string, string | number>): string {
  const text: string = en[key];
  if (!vars) return text;
  return text.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in vars ? String(vars[name]) : match,
  );
}
