// Public surface of the auth feature. Pages and other features import from
// "@/features/auth" only, never from files inside it.
export { googleSignInUrl, refusal, type Me, type Refusal } from "./api";
export { AuthCard, AuthNote, GoogleButton, GoogleDot } from "./components/AuthCard";
export { RequireSession } from "./components/RequireSession";
export { useMe } from "./session";
export { SignOutButton } from "./components/SignOutButton";
