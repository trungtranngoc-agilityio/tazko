# design/ — the UI specification (read-only)

Nobody edits this folder. If something here should change, ask the owner.

| File | What it is |
|---|---|
| `tazko-prototype.html` | The whole clickable prototype in one file. Open it in a browser and start from the index page (one tile per screen, grouped by round). |
| `tokens.css` | Colors, spacing, radii, shadows and type for light and dark, taken from the prototype. `web/src/styles/index.css` turns it into the Tailwind theme. |
| `KNOWN-DEVIATIONS.md` | Prototype behaviour the product must **not** copy. Each line has a regression test. |

Precedence: the build plan wins on data, permissions and limits; the prototype wins on look and interaction. If neither says, stop and ask.

The prototype's **View as** switch shows what each role sees (super admin, company owner, project owner, member, observer). Build the same differences, enforced on the server.

Things the prototype only pretends: sample data, live updates between browsers, email delivery, file uploads, the command line.

## Screen index by milestone

| Milestone | Prototype screens |
|---|---|
| M1 | Sign in, Sign-in refused, Company home (switcher, empty state), Company settings (members and invites), Manage projects, Admin: Companies, Company detail, People, Invites, Audit log, Server |
| M2 | Your projects, Project boards, Project members, Project settings (incl. card aging), Board (drag, composer, shortcuts), Card, Filter, Search with operators, Zen mode, Command palette, Settings: profile and appearance |
| M3 | Attachments (upload, link, cover), Custom fields, Live updates and presence, Notifications, Reactions, Board background upload |
| M4 | Templates, Table view, Dashboard, My cards |
| M5 | Checklist items with assignee and due date, Recurring cards, Linked cards, Rich text, Voting, Card aging, Long cards |
| M6 | Settings: notifications, access tokens and command line; Authorize the command line; Integrations: API tokens and webhooks; Email previews; Admin: email status |
