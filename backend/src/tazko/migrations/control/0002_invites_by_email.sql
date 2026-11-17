-- Sign-in refusals look up the newest unused invite for an email, revoked or
-- expired ones included, which the partial index invites_pending_by_email does
-- not cover. Anyone can trigger that lookup by signing in, so it needs an index.
CREATE INDEX invites_unused_by_email ON invites (email, id) WHERE accepted_at IS NULL;
