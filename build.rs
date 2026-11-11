//! Build step for the embedded web app.
//!
//! The release binary embeds `web/dist` (see `src/web.rs`). In debug builds
//! rust-embed reads the folder from disk, so `npm --prefix web run build`
//! is picked up without recompiling.
//!
//! If `web/dist` does not exist yet, a placeholder page is written so the
//! crate still compiles (e.g. `cargo test` on a fresh clone).
//! TODO(M1-01): brotli pre-compression of the bundle for release builds.

use std::{fs, path::Path};

fn main() {
    println!("cargo:rerun-if-changed=web/dist");
    let dist = Path::new("web/dist");
    let index = dist.join("index.html");
    if !index.exists() {
        fs::create_dir_all(dist).expect("create web/dist");
        fs::write(
            &index,
            "<!doctype html><meta charset=utf-8><title>Tazko</title>\
             <p>The web app is not built. Run <code>npm --prefix web run build</code>.</p>",
        )
        .expect("write placeholder web/dist/index.html");
    }
}
