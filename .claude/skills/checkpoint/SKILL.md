---
name: checkpoint
description: Bring docs/status.md up to date before a session ends, before switching task, or when asked for a checkpoint, so the next session starts from the file instead of the conversation.
---
1. Read docs/status.md, `git status`, `git log --oneline -10` and the open PRs (`gh pr list`).
2. Rewrite only what changed, in the file's own sections and words:
   - the `Updated` line: date, `dev` commit, open PRs and local branches;
   - **Now**: each milestone task in progress, with its PR or branch;
   - **Next**: the exact next steps, owner steps marked "Owner:";
   - **Waiting on the owner** and **Housekeeping**.
3. Name tests that failed or were not run, and anything left unverified.
4. Do not touch decisions (docs/decisions.md), milestone task rows or other files; never log issue bookkeeping here.
5. Commit it with the task's branch (`docs(claude): update docs/status.md`), never straight to `dev` or `main`.
