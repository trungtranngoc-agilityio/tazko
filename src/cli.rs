//! Command line. Server commands now; the client commands (`auth`, `project`,
//! `board`, `card`, `my`, `search`, `token`, `webhook`, `api`, `config`,
//! `completion`, `update`) are added in M6-04.
//!
//! Exit codes (build plan): 0 success, 1 failure, 2 wrong usage, 4 not signed in.

use std::path::PathBuf;

use clap::{Parser, Subcommand};

use crate::config::Config;

#[derive(Debug, Parser)]
#[command(
    name = "tazko",
    version,
    about = "Tazko server and command-line client"
)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Command,
}

#[derive(Debug, Subcommand)]
pub enum Command {
    /// Run the web server (settings from TAZKO_* environment variables).
    Serve,
    /// Create a person with the super admin flag, or grant it to an existing one.
    Admin {
        /// Data folder; defaults to TAZKO_DATA_DIR.
        #[arg(long)]
        data: Option<PathBuf>,
        /// Google account email of the person.
        #[arg(long)]
        email: String,
    },
    /// Copy every database (online backup API) and file folder into a dated snapshot.
    Backup {
        #[arg(long)]
        data: Option<PathBuf>,
        #[arg(long)]
        to: PathBuf,
        #[arg(long, default_value_t = 30)]
        keep_days: u32,
    },
    /// Open every database, run integrity_check and verify attachment hashes.
    Check {
        #[arg(long)]
        data: Option<PathBuf>,
    },
}

pub async fn run(cli: Cli) -> anyhow::Result<()> {
    match cli.command {
        Command::Serve => {
            let config = Config::from_env()?;
            crate::server::serve(config).await
        }
        Command::Admin { data, email } => {
            let _ = (data, email);
            not_yet("admin", "M1-02")
        }
        Command::Backup {
            data,
            to,
            keep_days,
        } => {
            let _ = (data, to, keep_days);
            not_yet("backup", "M1-08")
        }
        Command::Check { data } => {
            let _ = data;
            not_yet("check", "M1-08")
        }
    }
}

fn not_yet(command: &str, task: &str) -> anyhow::Result<()> {
    anyhow::bail!("`tazko {command}` is not implemented yet (task {task})")
}
