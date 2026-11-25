import { en, type MessageKey } from "./en";

export type { MessageKey };

/** Look up a UI string. Placeholders like `{name}` are filled from `vars`. */
export function t(key: MessageKey, vars?: Record<string, string | number>): string {
  const text: string = en[key];
  if (!vars) return text;
  return text.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in vars ? String(vars[name]) : match,
  );
}

function isMessageKey(key: string): key is MessageKey {
  return Object.hasOwn(en, key);
}

/** The message for an API error code: `error.<code>`, else a generic one. */
export function errorText(code: string): string {
  const key = `error.${code}`;
  return isMessageKey(key) ? t(key) : t("error.UNKNOWN");
}
