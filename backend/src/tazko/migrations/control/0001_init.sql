-- control.db: people, companies, memberships, invites, sessions, audit log.
-- Times are UTC ISO 8601 text ('2026-11-16T09:30:00.000Z'), written by tazko.core.clock.

CREATE TABLE users (
    id             INTEGER PRIMARY KEY,
    email          TEXT    NOT NULL UNIQUE CHECK (email = lower(email) AND email LIKE '%_@_%'),
    google_sub     TEXT    UNIQUE,
    name           TEXT    NOT NULL DEFAULT '',
    avatar_url     TEXT,
    hd             TEXT,                          -- Workspace domain, shown only
    is_super_admin INTEGER NOT NULL DEFAULT 0 CHECK (is_super_admin IN (0, 1)),
    disabled_at    TEXT,
    created_at     TEXT    NOT NULL,
    last_seen_at   TEXT
) STRICT;

CREATE TABLE orgs (
    id                  INTEGER PRIMARY KEY,
    slug                TEXT    NOT NULL UNIQUE,
    name                TEXT    NOT NULL CHECK (length(name) BETWEEN 1 AND 100),
    status              TEXT    NOT NULL DEFAULT 'active'
                                CHECK (status IN ('active', 'suspended', 'deleted')),
    storage_limit_bytes INTEGER CHECK (storage_limit_bytes IS NULL OR storage_limit_bytes >= 0),
    created_at          TEXT    NOT NULL,
    deleted_at          TEXT
) STRICT;

CREATE TABLE org_members (
    org_id     INTEGER NOT NULL REFERENCES orgs (id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    role       TEXT    NOT NULL CHECK (role IN ('owner', 'member')),
    created_at TEXT    NOT NULL,
    PRIMARY KEY (org_id, user_id)
) STRICT, WITHOUT ROWID;
CREATE INDEX org_members_by_user ON org_members (user_id);

-- One invite authorizes one email for one company (and optionally one project).
CREATE TABLE invites (
    id           INTEGER PRIMARY KEY,
    org_id       INTEGER NOT NULL REFERENCES orgs (id) ON DELETE CASCADE,
    email        TEXT    NOT NULL CHECK (email = lower(email)),
    role         TEXT    NOT NULL CHECK (role IN ('owner', 'member')),
    project_id   INTEGER,                        -- id in the company file
    project_role TEXT    CHECK (project_role IN ('owner', 'member', 'observer')),
    created_by   INTEGER REFERENCES users (id) ON DELETE SET NULL,
    created_at   TEXT    NOT NULL,
    expires_at   TEXT    NOT NULL,
    accepted_at  TEXT,
    accepted_by  INTEGER REFERENCES users (id) ON DELETE SET NULL,
    revoked_at   TEXT,
    CHECK ((project_id IS NULL) = (project_role IS NULL))
) STRICT;
CREATE INDEX invites_pending_by_email ON invites (email)
    WHERE accepted_at IS NULL AND revoked_at IS NULL;
CREATE INDEX invites_by_org ON invites (org_id);

-- The cookie holds a random token; only its SHA-256 is stored.
CREATE TABLE sessions (
    token_hash   TEXT    PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    created_at   TEXT    NOT NULL,
    last_used_at TEXT    NOT NULL,
    expires_at   TEXT    NOT NULL,
    ip           TEXT,
    user_agent   TEXT
) STRICT, WITHOUT ROWID;
CREATE INDEX sessions_by_user ON sessions (user_id);

CREATE TABLE audit_log (
    id       INTEGER PRIMARY KEY,
    at       TEXT    NOT NULL,
    actor_id INTEGER REFERENCES users (id) ON DELETE SET NULL,  -- NULL: command line or system
    action   TEXT    NOT NULL,                                  -- e.g. company.created
    org_id   INTEGER REFERENCES orgs (id) ON DELETE SET NULL,
    target   TEXT,                                              -- email, slug, ...
    detail   TEXT    CHECK (detail IS NULL OR json_valid(detail)),
    ip       TEXT
) STRICT;
CREATE INDEX audit_log_by_at ON audit_log (at);
CREATE INDEX audit_log_by_org ON audit_log (org_id, at);
