import { useEffect, useState } from "react";
import {
  AuthCard,
  AuthNote,
  GoogleButton,
  googleSignInUrl,
  refusal,
  type Refusal,
} from "@/features/auth";
import { t } from "@/shared/i18n";

// Sign-in refused (design: 02-refused). The API keeps the refused address in a
// short-lived cookie, so it never travels in the URL. A member whose companies
// are all suspended is told so; every other reason reads as not invited.
export function RefusedPage() {
  const [found, setFound] = useState<Refusal | null | undefined>(undefined);

  useEffect(() => {
    let live = true;
    refusal().then(
      (value) => live && setFound(value),
      () => live && setFound(null),
    );
    return () => {
      live = false;
    };
  }, []);

  const suspended = found?.reason === "company_suspended";
  return (
    <AuthCard>
      <h1 className="text-[1.6rem] font-bold tracking-tight">
        {suspended ? t("refused.suspendedTitle") : t("refused.title")}
      </h1>
      <p className="mt-2 min-h-6 text-muted">
        {found === null && t("refused.leadUnknown")}
        {found && (
          <>
            <b className="font-semibold">{found.email}</b>{" "}
            {suspended ? t("refused.suspendedLead") : t("refused.lead")}
          </>
        )}
      </p>
      <AuthNote>{suspended ? t("company.isSuspended") : t("refused.help")}</AuthNote>
      <GoogleButton href={googleSignInUrl()}>{t("refused.another")}</GoogleButton>
    </AuthCard>
  );
}
