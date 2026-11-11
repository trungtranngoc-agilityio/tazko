use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use tower::ServiceExt;

use tazko::{
    config::Config,
    server::{router, AppState},
};

#[tokio::test]
async fn health_returns_200() {
    let config = Config::from_lookup(|_| None).unwrap();
    let app = router(AppState::new(config));

    let response = app
        .oneshot(Request::get("/health").body(Body::empty()).unwrap())
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
}
