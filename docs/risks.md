# Risk register

| Risk | Likelihood | Impact | Mitigation | When |
|---|---|---|---|---|
| The agent copies a prototype permission bug | Medium | High | KNOWN-DEVIATIONS.md, regression tests, reviewer check | M2, M3 |
| Account takeover through a reissued email | Low | High | Match by `sub` first; security review in M1 | M1 |
| A deploy breaks the other service on the machine | Low | High | You run the scripts; sandboxed unit; only add a new tunnel rule | M1 |
| Data loss when the disk fails | Low | High | Off-machine backup, monthly restore test | M1 on |
| M2 runs late because it is large | High | Medium | Nine tasks; after M2-05 the team can already try it internally | M2 |
| The UI slowly drifts from the prototype | Medium | Medium | Compare screens after every UI task, not only at the end | All |
| Merge conflicts from parallel work | Medium | Low | Split files up front; number migrations up front | M3, M5 |
| Long agent sessions forget the rules | High | Medium | One task per prompt, `/clear` between tasks, memory in files | All |
| Webhooks used to reach the internal network | Medium | High | Check addresses after DNS; security review in M6 | M6 |
