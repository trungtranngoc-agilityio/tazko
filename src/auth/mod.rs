//! Sign-in and request guards.
//!
//! Milestone: M1-04, M1-05. Empty until then; see docs/milestones/.
//!
//! - TODO: Google OIDC with PKCE, state and nonce; verify ID token signature, audience, expiry, nonce; require email_verified.
//! - TODO: Match by sub first; by email only when the person has no sub yet. Otherwise a pending invite, else refuse and audit-log.
//! - TODO: Sessions: HttpOnly, Secure, SameSite=Lax cookie, 30 days from last use, stored in control.db.
//! - TODO: Invites with 14-day expiry (D3). Origin check on every state-changing request. Client IP from CF-Connecting-IP.
