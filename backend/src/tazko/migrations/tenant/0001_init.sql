-- One company's file. Projects, boards and cards arrive in M2-01.

-- A copy of the control.db person (id is users.id there), so names and
-- avatars render without reaching into control.db.
CREATE TABLE people (
    id         INTEGER PRIMARY KEY,
    name       TEXT    NOT NULL DEFAULT '',
    email      TEXT    NOT NULL,
    avatar_url TEXT,
    updated_at TEXT    NOT NULL
) STRICT;

-- Every change writes one row here in the same transaction.
CREATE TABLE events (
    id         INTEGER PRIMARY KEY,
    type       TEXT    NOT NULL,                 -- e.g. member.added
    actor_id   INTEGER,                          -- people.id; NULL for the system
    board_id   INTEGER,
    payload    TEXT    NOT NULL DEFAULT '{}' CHECK (json_valid(payload)),
    created_at TEXT    NOT NULL
) STRICT;
CREATE INDEX events_by_board ON events (board_id, id);
CREATE INDEX events_by_created ON events (created_at);
