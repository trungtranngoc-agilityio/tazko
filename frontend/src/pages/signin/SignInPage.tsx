import { GoogleSignInButton } from "@/features/auth";

// Sign in and Sign-in refused screens (M1-04).
export function SignInPage() {
  return (
    <div className="grid min-h-screen place-items-center bg-bg text-ink">
      <GoogleSignInButton />
    </div>
  );
}
