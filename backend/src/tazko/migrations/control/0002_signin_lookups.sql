-- Lookups that anyone can trigger by signing in, so neither may scan a table.

-- Why a sign-in was refused: the newest unused invite for an email, revoked or
-- expired ones included, which the partial index invites_pending_by_email does
-- not cover.
CREATE INDEX invites_unused_by_email ON invites (email, id) WHERE accepted_at IS NULL;

-- Email domains known to be a Google Workspace: every sign-in with an hd
-- records the hd and the address's own domain (alias domains report the main
-- one as hd). Kept apart from users, so removing people never forgets a domain.
CREATE TABLE workspace_domains (
    domain        TEXT PRIMARY KEY
                  CHECK (domain = lower(domain) AND length(domain) BETWEEN 1 AND 253
                         AND domain NOT LIKE '%@%' AND domain NOT GLOB '*[ .]'),
    first_seen_at TEXT NOT NULL
) STRICT, WITHOUT ROWID;
