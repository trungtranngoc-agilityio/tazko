# Frontend layers

Each layer imports only from the layers below it. ESLint enforces this
(`no-restricted-imports` in `eslint.config.js`).

| Layer              | Holds                                                                                            | May import                                    |
| ------------------ | ------------------------------------------------------------------------------------------------ | --------------------------------------------- |
| `app/`             | Providers, router, layouts, global styles                                                        | everything                                    |
| `pages/<screen>/`  | One routed screen; composes features                                                             | `features`, `shared`                          |
| `features/<name>/` | One product area: `components/`, `api.ts`, `hooks/`, its tests; public surface in `index.ts`     | other features via their `index.ts`, `shared` |
| `shared/`          | `api/` (the only fetch wrapper), `i18n/` (every UI string), `ui/` (generated primitives), `lib/` | nothing above it                              |

Planned features: `auth`, `orgs` (company switcher), `boards`, `cards`, `search`,
`notifications`, `admin` (console screens), `settings`.
