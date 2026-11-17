-- Lookups that anyone can trigger by signing in, so neither may scan a table.

-- Why a sign-in was refused: the newest unused invite for an email, revoked or
-- expired ones included, which the partial index invites_pending_by_email does
-- not cover.
CREATE INDEX invites_unused_by_email ON invites (email, id) WHERE accepted_at IS NULL;

-- Whether an email domain is a Google Workspace: someone signed in with it as hd (D26).
CREATE INDEX users_by_hd ON users (hd) WHERE hd IS NOT NULL;
