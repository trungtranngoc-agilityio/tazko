# Decisions

Every judgment call, with date and reason. Status `proposed` means the owner has not confirmed it yet.
Format for new entries: `## Dn — question`, then date, choice, why, affects.

| # | Question | Choice | Affects | Status |
|---|---|---|---|---|
| D1 | Due reminders per card (prototype) or per person (plan)? | Per person, as in the plan. Remove “Remind me” from the Dates popup. | M2, M6 | proposed |
| D2 | Show M3/M4 items (custom fields, save as template, palette) in the M2 board menu? | Hide them until their milestone ships. No dead buttons. | M2–M4 | proposed |
| D3 | Do invites expire? | Yes, after 14 days by default. Show the expiry date; allow re-invite. | M1 | proposed |
| D4 | Confirm “Delete forever” and “Remove member”? | Yes. Block removing the last owner. Removing yourself asks first. | M1, M2 | proposed |
| D5 | Can observers comment? | No. Observers are fully read-only. | M2 | proposed |
| D6 | Cards assigned to someone removed from the project? | Unassign automatically, log an event, keep the card. | M2 | proposed |
| D7 | Can a company “manage” token open restricted boards? | No. Tokens follow the same rules as people. | M6 | proposed |
| D8 | Where do builds run? | In CI or a build machine. Only the built bundle goes to the server. | M1 | proposed |
| D9 | Off-machine backup required? | Yes, one copy off the machine, with a monthly restore test. | M1 | proposed |
| D10 | May the agent run sudo or systemd commands? | No. It writes scripts in `deploy/`; you read and run them. | M1 | proposed |
| D11 | AI attribution in commits | None: no Co-Authored-By or "generated with" lines in commits or PRs. `attribution` is empty in `.claude/settings.json`. | All | decided 2026-11-11 |
| D12 | Allow the permissive licenses Unicode-3.0 and Zlib in `deny.toml`? | Unicode-3.0 is allowed (unicode-ident needs it, no way around it). Zlib is not allowed yet, so rusqlite stays pinned at 0.32: 0.33+ pulls in foldhash (Zlib). If Zlib is accepted, add it to `deny.toml` and move to the newest rusqlite. | M1 | proposed |

## Log

<!-- 2026-11-11 · D? · question · choice · why -->
