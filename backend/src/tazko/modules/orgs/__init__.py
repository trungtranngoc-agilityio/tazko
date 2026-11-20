"""Companies in control.db and the cache of open company databases.

service.py: create a company (row, folder, migrated database), add members,
list a person's companies, and `open_company`, the membership check that is
the only way to reach a company's file (M1-03).

- TODO(M1-06): change role, remove member; last owner cannot be removed (KNOWN-DEVIATIONS #5).
- Suspend, resume and delete to data/trash/ for 30 days (M1-07, D35).
"""
