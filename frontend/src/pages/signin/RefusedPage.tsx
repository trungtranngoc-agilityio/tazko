import { useEffect, useState } from "react";
import { AuthCard, AuthNote, GoogleButton, googleSignInUrl, refusedEmail } from "@/features/auth";
import { t } from "@/shared/i18n";

// Sign-in refused (design: 02-refused). The API keeps the refused address in a
// short-lived cookie, so it never travels in the URL.
export function RefusedPage() {
  const [email, setEmail] = useState<string | null | undefined>(undefined);

  useEffect(() => {
    let live = true;
    refusedEmail().then(
      (value) => live && setEmail(value),
      () => live && setEmail(null),
    );
    return () => {
      live = false;
    };
  }, []);

  return (
    <AuthCard>
      <h1 className="text-[1.6rem] font-bold tracking-tight">{t("refused.title")}</h1>
      <p className="mt-2 min-h-6 text-muted">
        {email === null && t("refused.leadUnknown")}
        {email && (
          <>
            <b className="font-semibold">{email}</b> {t("refused.lead")}
          </>
        )}
      </p>
      <AuthNote>{t("refused.help")}</AuthNote>
      <GoogleButton href={googleSignInUrl()}>{t("refused.another")}</GoogleButton>
    </AuthCard>
  );
}
