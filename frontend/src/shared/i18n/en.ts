// Every user-visible string lives here (Vietnamese comes later as vi.ts).
export const en = {
  "app.name": "Tazko",
  "admin.title": "Tazko admin",
  "admin.empty": "Admin console (M1-06)",
  "home.empty": "No projects yet.",
  "signin.title": "Sign in to Tazko",
  "signin.lead":
    "Use the Google account your administrator invited. Workspace and personal accounts both work.",
  "signin.google": "Continue with Google",
  "signin.inviteOnly":
    "Access is by invitation only. If you cannot sign in, ask your company owner to invite your email address.",
  "signin.failed": "Sign-in did not finish. Try again.",
  "signin.signOut": "Sign out",
  "refused.title": "This account is not invited",
  "refused.lead": "is not on the list for Tazko.",
  "refused.leadUnknown": "This Google account is not on the list for Tazko.",
  "refused.help":
    "Ask the owner of your company to invite this exact email address, then sign in again. If you meant to use a different Google account, choose it below.",
  "refused.another": "Try another Google account",
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
