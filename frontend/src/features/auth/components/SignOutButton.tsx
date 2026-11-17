import { t } from "@/shared/i18n";
import { signOut } from "../api";

export function SignOutButton() {
  async function onClick() {
    await signOut();
    window.location.assign("/signin");
  }
  return (
    <button type="button" onClick={onClick} className="text-sm text-muted hover:text-ink">
      {t("signin.signOut")}
    </button>
  );
}
