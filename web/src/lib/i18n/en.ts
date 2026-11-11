// Every user-visible string lives here (Vietnamese comes later as vi.ts).
export const en = {
  "app.name": "Tazko",
  "admin.title": "Tazko admin",
  "home.empty": "No projects yet.",
  "signin.google": "Sign in with Google",
  notFound: "Page not found",
} as const;

export type MessageKey = keyof typeof en;
