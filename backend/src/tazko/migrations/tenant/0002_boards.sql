-- readers: 1
-- Projects, boards, lists and cards (M2-01). Only adds tables, indexes and
-- triggers on new tables, so release 0.1.0 (migration 0001) still runs on
-- the file after it (D21).
--
-- Ordered rows carry a fractional rank (tazko.db.rank): digits 0-9A-Za-z,
-- compared as text (BINARY), never ending in "0" so a key always fits below.
-- Ranks are kept unique per list or board by the code that writes them (one
-- writer thread per company); there is no UNIQUE index because rebalancing a
-- list rewrites every rank in it and SQLite checks uniqueness row by row.
-- Times are UTC ISO 8601 text, as in control.db. people.id is users.id there.
-- Projects, boards, lists, cards and labels use AUTOINCREMENT: events and share
-- links name them by id, so a deleted row's id is never given to a new one.
-- Rules that need the actor or several tables stay in the services (M2-02):
-- a project keeps an owner; board_access, card_members and card_watchers name
-- project members only and are cleared when someone leaves the project (D6).

CREATE TABLE projects (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    name                      TEXT    NOT NULL CHECK (trim(name) <> '' AND length(name) <= 100),
    description               TEXT    NOT NULL DEFAULT '' CHECK (length(description) <= 2000),
    color                     TEXT    CHECK (length(color) BETWEEN 1 AND 32),
    default_background        TEXT    CHECK (length(default_background) BETWEEN 1 AND 64),
    members_can_create_boards INTEGER NOT NULL DEFAULT 1 CHECK (members_can_create_boards IN (0, 1)),
    members_can_invite        INTEGER NOT NULL DEFAULT 0 CHECK (members_can_invite IN (0, 1)),
    aging_enabled             INTEGER NOT NULL DEFAULT 1 CHECK (aging_enabled IN (0, 1)),
    aging_days                INTEGER NOT NULL DEFAULT 7 CHECK (aging_days IN (3, 7, 14, 30)),
    created_by                INTEGER REFERENCES people (id) ON DELETE SET NULL,
    created_at                TEXT    NOT NULL,
    archived_at               TEXT,
    deleted_at                TEXT                -- in trash; removed for good after 30 days
) STRICT;

CREATE TABLE project_members (
    project_id INTEGER NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    person_id  INTEGER NOT NULL REFERENCES people (id) ON DELETE CASCADE,
    role       TEXT    NOT NULL CHECK (role IN ('owner', 'member', 'observer')),
    created_at TEXT    NOT NULL,
    PRIMARY KEY (project_id, person_id)
) STRICT, WITHOUT ROWID;
CREATE INDEX project_members_by_person ON project_members (person_id);

CREATE TABLE boards (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    name        TEXT    NOT NULL CHECK (trim(name) <> '' AND length(name) <= 100),
    background  TEXT    CHECK (length(background) BETWEEN 1 AND 64),  -- preset key; uploads in M3
    restricted  INTEGER NOT NULL DEFAULT 0 CHECK (restricted IN (0, 1)),
    created_by  INTEGER REFERENCES people (id) ON DELETE SET NULL,
    created_at  TEXT    NOT NULL,
    archived_at TEXT                              -- "Close board"
) STRICT;
CREATE INDEX boards_by_project ON boards (project_id);

-- Who may open a restricted board: only the project members listed here.
CREATE TABLE board_access (
    board_id  INTEGER NOT NULL REFERENCES boards (id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES people (id) ON DELETE CASCADE,
    PRIMARY KEY (board_id, person_id)
) STRICT, WITHOUT ROWID;
CREATE INDEX board_access_by_person ON board_access (person_id);

CREATE TABLE board_stars (
    person_id  INTEGER NOT NULL REFERENCES people (id) ON DELETE CASCADE,
    board_id   INTEGER NOT NULL REFERENCES boards (id) ON DELETE CASCADE,
    created_at TEXT    NOT NULL,
    PRIMARY KEY (person_id, board_id)
) STRICT, WITHOUT ROWID;
CREATE INDEX board_stars_by_board ON board_stars (board_id);

CREATE TABLE lists (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    board_id    INTEGER NOT NULL REFERENCES boards (id) ON DELETE CASCADE,
    name        TEXT    NOT NULL CHECK (trim(name) <> '' AND length(name) <= 100),
    rank        TEXT    NOT NULL COLLATE BINARY CHECK (length(rank) BETWEEN 1 AND 32
                                        AND rank NOT GLOB '*[^0-9A-Za-z]*'
                                        AND rank NOT GLOB '*0'),
    created_at  TEXT    NOT NULL,
    archived_at TEXT
) STRICT;
CREATE INDEX lists_by_board ON lists (board_id, rank);

CREATE TABLE cards (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    list_id     INTEGER NOT NULL REFERENCES lists (id) ON DELETE CASCADE,
    title       TEXT    NOT NULL CHECK (trim(title) <> '' AND length(title) <= 512),
    description TEXT    NOT NULL DEFAULT '',      -- rich-text HTML, sanitized and capped by the server (M2-04)
    rank        TEXT    NOT NULL COLLATE BINARY CHECK (length(rank) BETWEEN 1 AND 32
                                        AND rank NOT GLOB '*[^0-9A-Za-z]*'
                                        AND rank NOT GLOB '*0'),
    due_at      TEXT,
    done_at     TEXT,
    cover_color TEXT    CHECK (length(cover_color) BETWEEN 1 AND 32),  -- picture covers in M3
    created_by  INTEGER REFERENCES people (id) ON DELETE SET NULL,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL,                 -- last activity, for card aging
    archived_at TEXT
) STRICT;
CREATE INDEX cards_by_list ON cards (list_id, rank);

CREATE TABLE labels (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    board_id   INTEGER NOT NULL REFERENCES boards (id) ON DELETE CASCADE,
    name       TEXT    NOT NULL DEFAULT '' CHECK (length(name) <= 100),  -- a label may be a colour only
    color      TEXT    NOT NULL CHECK (length(color) BETWEEN 1 AND 32),
    created_at TEXT    NOT NULL
) STRICT;
CREATE INDEX labels_by_board ON labels (board_id);

CREATE TABLE card_labels (
    card_id  INTEGER NOT NULL REFERENCES cards (id) ON DELETE CASCADE,
    label_id INTEGER NOT NULL REFERENCES labels (id) ON DELETE CASCADE,
    PRIMARY KEY (card_id, label_id)
) STRICT, WITHOUT ROWID;
CREATE INDEX card_labels_by_label ON card_labels (label_id);

-- A card only wears labels of its own board: a label of another board is
-- refused, and moving a card or a list to another board drops those labels.
CREATE TRIGGER card_labels_same_board
BEFORE INSERT ON card_labels
WHEN (SELECT board_id FROM labels WHERE id = NEW.label_id)
     IS NOT (SELECT l.board_id FROM cards c JOIN lists l ON l.id = c.list_id WHERE c.id = NEW.card_id)
BEGIN
    SELECT RAISE(ABORT, 'label belongs to another board');
END;

CREATE TRIGGER card_labels_same_board_on_change
BEFORE UPDATE OF card_id, label_id ON card_labels
WHEN (SELECT board_id FROM labels WHERE id = NEW.label_id)
     IS NOT (SELECT l.board_id FROM cards c JOIN lists l ON l.id = c.list_id WHERE c.id = NEW.card_id)
BEGIN
    SELECT RAISE(ABORT, 'label belongs to another board');
END;

CREATE TRIGGER cards_moved_drop_labels
AFTER UPDATE OF list_id ON cards
WHEN (SELECT board_id FROM lists WHERE id = NEW.list_id)
     IS NOT (SELECT board_id FROM lists WHERE id = OLD.list_id)
BEGIN
    DELETE FROM card_labels WHERE card_id = NEW.id;
END;

CREATE TRIGGER lists_moved_drop_labels
AFTER UPDATE OF board_id ON lists
WHEN NEW.board_id IS NOT OLD.board_id
BEGIN
    DELETE FROM card_labels WHERE card_id IN (SELECT id FROM cards WHERE list_id = NEW.id);
END;

CREATE TABLE card_members (
    card_id   INTEGER NOT NULL REFERENCES cards (id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES people (id) ON DELETE CASCADE,
    PRIMARY KEY (card_id, person_id)
) STRICT, WITHOUT ROWID;
CREATE INDEX card_members_by_person ON card_members (person_id);

CREATE TABLE card_watchers (
    card_id   INTEGER NOT NULL REFERENCES cards (id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES people (id) ON DELETE CASCADE,
    PRIMARY KEY (card_id, person_id)
) STRICT, WITHOUT ROWID;
CREATE INDEX card_watchers_by_person ON card_watchers (person_id);
