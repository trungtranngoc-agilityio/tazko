// Every user-visible string lives here (Vietnamese comes later as vi.ts).
export const en = {
  "app.name": "Tazko",
  "admin.title": "Tazko admin",
  "admin.empty": "Admin console (M1-06)",
  "home.empty": "No projects yet.",
  "signin.google": "Sign in with Google",
  notFound: "Page not found",

  // API error codes (D19). Show with errorText(error.code); add a key for each
  // code the UI must explain. Unknown codes fall back to error.UNKNOWN.
  "error.UNKNOWN": "Something went wrong. Try again.",
  "error.BAD_REQUEST": "The request could not be read. Reload the page and try again.",
  "error.UNAUTHENTICATED": "Your session has ended. Sign in again.",
  "error.FORBIDDEN": "You do not have access to this.",
  "error.NOT_FOUND": "This no longer exists, or you do not have access to it.",
  "error.CONFLICT": "This was changed by someone else. Reload and try again.",
  "error.VALIDATION_ERROR": "Some fields need fixing.",
  "error.RATE_LIMITED": "Too many requests. Wait a moment and try again.",
  "error.INTERNAL": "Something went wrong on our side. Try again.",
  "error.SLUG_TAKEN": "That address is already used by another company.",
} as const;

export type MessageKey = keyof typeof en;
