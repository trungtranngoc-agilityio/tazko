import { useSearchParams } from "react-router";
import { AuthCard, AuthNote, GoogleButton, GoogleDot, googleSignInUrl } from "@/features/auth";
import { t } from "@/shared/i18n";

// Sign in (design: 01-signin). `?error=failed` comes from the API when the
// Google round trip could not be trusted or finished.
export function SignInPage() {
  const [params] = useSearchParams();
  return (
    <AuthCard>
      <h1 className="text-[1.6rem] font-bold tracking-tight">{t("signin.title")}</h1>
      <p className="mt-2 text-muted">{t("signin.lead")}</p>
      {params.get("error") === "failed" && <AuthNote role="alert">{t("signin.failed")}</AuthNote>}
      <GoogleButton href={googleSignInUrl()}>
        <GoogleDot />
        {t("signin.google")}
      </GoogleButton>
      <AuthNote>{t("signin.inviteOnly")}</AuthNote>
    </AuthCard>
  );
}
