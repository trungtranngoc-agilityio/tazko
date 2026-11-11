//! Tazko: one binary that is the web server, the super admin console and
//! (from M6) the command-line client.
//!
//! Module map (see docs/build-plan.md, "Repository and handoff"):
//!
//! | Module          | Responsibility                                              | First milestone |
//! |-----------------|-------------------------------------------------------------|-----------------|
//! | `cli`           | `serve`, `admin`, `backup`, `check`; later the client verbs | M1, M6          |
//! | `config`        | Settings from the environment (`TAZKO_*`)                   | M1              |
//! | `server`        | Router, shared state, `/health`, graceful shutdown          | M1              |
//! | `web`           | Embedded web app (`web/dist`)                               | M1              |
//! | `error`         | One error type mapped to HTTP responses                     | M1              |
//! | `db`            | Connection setup, migrations by `user_version`              | M1              |
//! | `orgs`          | `control.db` companies, memberships, tenant handle cache    | M1              |
//! | `auth`          | Google OIDC + PKCE, sessions, Origin check, invites         | M1              |
//! | `admin`         | Super admin console API (`/admin`)                          | M1              |
//! | `tenant`        | Per-company database: writer thread + read pool, events     | M1, M2          |
//! | `boards`        | Projects, boards, lists, permissions                        | M2              |
//! | `cards`         | Cards, checklists, comments, search                         | M2              |
//! | `realtime`      | WebSocket per board, in-memory hub                          | M3              |
//! | `files`         | Content-hash storage, quotas, thumbnails                    | M3              |
//! | `notifications` | Mentions, bell, due-soon, email queue                       | M3, M6          |
//! | `api`           | REST `/api/v1`, OpenAPI, tokens, webhooks                   | M6              |

pub mod admin;
pub mod api;
pub mod auth;
pub mod boards;
pub mod cards;
pub mod cli;
pub mod config;
pub mod db;
pub mod error;
pub mod files;
pub mod notifications;
pub mod orgs;
pub mod realtime;
pub mod server;
pub mod tenant;
pub mod web;
