# Prototype behaviour we must NOT copy

Each line was reproduced by clicking through the prototype. Each has a regression test.

| # | Prototype does | Product must | Test | Milestone |
|---|---|---|---|---|
| 1 | Restricted board is listed and opens for project members not on its list | Hide it and return 404 | tests/perm_restricted_board.rs | M2 |
| 2 | Observer can delete a custom field | Observer is read-only: 403 | tests/perm_observer_fields.rs | M3 |
| 3 | "Remind me" in the Dates popup is shown but never saved | Remove the field (decision D1) | e2e/dates_popup.spec.ts | M2 |
| 4 | "Delete forever" in Archived items deletes with no confirmation | Ask to confirm, name the card | e2e/archive_purge.spec.ts | M2 |
| 5 | "Remove" member acts at once, owner can remove themselves | Confirm; block removing the last owner | tests/perm_last_owner.rs | M1, M2 |
