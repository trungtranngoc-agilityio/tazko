import { useState } from "react";
import { ApiError } from "@/shared/api";
import { errorText, t } from "@/shared/i18n";
import { signOut } from "../api";

export function SignOutButton() {
  const [problem, setProblem] = useState<string | null>(null);

  async function onClick() {
    setProblem(null);
    try {
      await signOut();
    } catch (error) {
      setProblem(errorText(error instanceof ApiError ? error.code : "UNKNOWN"));
      return;
    }
    window.location.assign("/signin");
  }

  return (
    <span className="flex items-center gap-3">
      {problem && (
        <span role="alert" className="text-sm text-danger">
          {problem}
        </span>
      )}
      <button type="button" onClick={onClick} className="text-sm text-muted hover:text-ink">
        {t("signin.signOut")}
      </button>
    </span>
  );
}
