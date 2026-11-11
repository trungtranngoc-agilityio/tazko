//! Settings from the environment. Production values live in
//! /etc/tazko/tazko.env (set by the owner); see .env.example for the list.
//!
//! TODO(M1-02): Google client id/secret, TAZKO_SECRET (or the generated
//! secret file), SMTP settings; clear error for each missing required value.

use std::{
    net::{IpAddr, SocketAddr},
    path::PathBuf,
};

use anyhow::Context;

#[derive(Debug, Clone)]
pub struct Config {
    pub host: IpAddr,
    pub port: u16,
    /// Public base URL; OAuth redirect addresses start with it.
    pub public_url: String,
    pub data_dir: PathBuf,
}

impl Config {
    pub fn from_env() -> anyhow::Result<Self> {
        Self::from_lookup(|key| std::env::var(key).ok())
    }

    /// Reads settings through `lookup`, so tests do not touch the process env.
    pub fn from_lookup(lookup: impl Fn(&str) -> Option<String>) -> anyhow::Result<Self> {
        let get = |key: &str, default: &str| lookup(key).unwrap_or_else(|| default.to_string());

        let host = get("TAZKO_HOST", "127.0.0.1")
            .parse()
            .context("TAZKO_HOST must be an IP address")?;
        let port = get("TAZKO_PORT", "8791")
            .parse()
            .context("TAZKO_PORT must be a port number")?;
        let public_url = get("TAZKO_PUBLIC_URL", &format!("http://{host}:{port}"));
        let data_dir = PathBuf::from(get("TAZKO_DATA_DIR", "./data"));

        Ok(Self {
            host,
            port,
            public_url,
            data_dir,
        })
    }

    pub fn addr(&self) -> SocketAddr {
        SocketAddr::new(self.host, self.port)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_listen_on_loopback_8791() {
        let config = Config::from_lookup(|_| None).unwrap();
        assert_eq!(config.addr().to_string(), "127.0.0.1:8791");
    }

    #[test]
    fn bad_port_gives_a_clear_error() {
        let err = Config::from_lookup(|k| (k == "TAZKO_PORT").then(|| "abc".into())).unwrap_err();
        assert!(err.to_string().contains("TAZKO_PORT"));
    }
}
