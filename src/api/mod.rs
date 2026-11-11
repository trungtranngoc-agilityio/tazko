//! Public REST API, tokens and webhooks.
//!
//! Milestone: M6-01 … M6-03. Empty until then; see docs/milestones/.
//!
//! - TODO: REST under /api/v1 with an OpenAPI document and a reference page at /api/docs.
//! - TODO: Company and personal tokens stored as hashes, shown once, scoped by project; never open restricted boards (D7).
//! - TODO: Webhooks: HMAC signed, retried with backoff for a day; refuse private addresses after DNS resolution.
