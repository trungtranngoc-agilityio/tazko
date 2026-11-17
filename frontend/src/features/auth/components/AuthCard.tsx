import type { ReactNode } from "react";
import { LogoMark } from "./LogoMark";

/** The centred card of the Sign in and Sign-in refused screens. */
export function AuthCard({ children }: { children: ReactNode }) {
  return (
    <div className="auth-backdrop grid min-h-screen place-items-center px-4 py-6 text-ink">
      <main className="w-full max-w-[420px] rounded-2xl border border-line bg-surface px-7 py-8 text-center shadow-card">
        <LogoMark className="mx-auto mb-[18px]" />
        {children}
      </main>
    </div>
  );
}

/** The grey explanation box under the heading. */
export function AuthNote({ children, role }: { children: ReactNode; role?: "alert" }) {
  return (
    <div
      role={role}
      className="mt-4 rounded-md bg-sunken px-3.5 py-2.5 text-left text-[0.85rem] text-muted"
    >
      {children}
    </div>
  );
}

/** The full-width outlined button that sends the browser to Google. */
export function GoogleButton({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a
      href={href}
      className="mt-[22px] flex h-11 w-full items-center justify-center gap-3 rounded-md border border-line bg-surface text-[0.95rem] font-semibold hover:bg-sunken"
    >
      {children}
    </a>
  );
}

/** The four-colour ring of the Google button. */
export function GoogleDot() {
  return (
    <span
      aria-hidden="true"
      className="inline-grid size-5 place-items-center rounded-full"
      style={{
        background: "conic-gradient(#ea4335 0 25%, #fbbc05 0 50%, #34a853 0 75%, #4285f4 0)",
      }}
    >
      <i className="block size-3 rounded-full bg-surface" />
    </span>
  );
}
