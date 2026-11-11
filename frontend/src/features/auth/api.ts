import { apiUrl } from "@/shared/api";

// Sign-in starts on the API host; after the Google callback the API sets the
// session cookie and redirects back to the web origin (D13).
export function googleSignInUrl(): string {
  return apiUrl("/auth/google/start");
}

// TODO(M1-04): currentUser() -> api<User>("/auth/me"), signOut().
