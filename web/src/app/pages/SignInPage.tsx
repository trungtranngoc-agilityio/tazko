import { t } from "@/lib/i18n";

// Sign in and Sign-in refused screens (M1-04).
export function SignInPage() {
  return (
    <div className="grid min-h-screen place-items-center bg-bg text-ink">
      <a
        href="/auth/google/start"
        className="rounded-md bg-accent px-4 py-2 font-medium text-white"
      >
        {t("signin.google")}
      </a>
    </div>
  );
}
