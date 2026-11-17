import { api, apiUrl } from "@/shared/api";

/** The signed-in person (GET /api/me). */
export interface Me {
  id: number;
  email: string;
  name: string;
  avatar_url: string | null;
  is_super_admin: boolean;
}

// Sign-in starts on the API host; after the Google callback the API sets the
// session cookie and redirects back to the web origin (D13).
export function googleSignInUrl(): string {
  return apiUrl("/auth/google/start");
}

export function currentUser(): Promise<Me> {
  return api<Me>("/api/me");
}

export function signOut(): Promise<void> {
  return api<void>("/auth/signout", { method: "POST" });
}

/** The Google account the API just refused, kept for 10 minutes in a cookie. */
export async function refusedEmail(): Promise<string> {
  return (await api<{ email: string }>("/auth/refusal")).email;
}
