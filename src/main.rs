use clap::Parser;
use tracing_subscriber::EnvFilter;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| EnvFilter::new("tazko=info,tower_http=info")),
        )
        .init();

    let cli = tazko::cli::Cli::parse();
    tazko::cli::run(cli).await
}
