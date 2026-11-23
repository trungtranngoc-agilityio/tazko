"""Projects, boards and lists, with server-side permissions.

- access.py: the project permission matrix (D39), one pure function every service asks.
- service.py, repository.py, router.py, schemas.py: projects and project members
  under /api/orgs/{slug}/projects (M2-02 part 1).

- TODO(M2-02 part 2): boards in a project; restricted boards are hidden (404) from
  members not on their list (KNOWN-DEVIATIONS #1); company owners open boards only
  after adding themselves.
- TODO(M2-02 part 3): a project invite adds a new email to the company as a plain member.
- TODO(M2-03): lists and cards on a board, moved with tazko.db.rank.
"""
