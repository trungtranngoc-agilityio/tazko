import { t } from "@/shared/i18n";
import { googleSignInUrl } from "../api";

export function GoogleSignInButton() {
  return (
    <a href={googleSignInUrl()} className="rounded-md bg-accent px-4 py-2 font-medium text-white">
      {t("signin.google")}
    </a>
  );
}
