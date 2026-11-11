//! Handle to exactly one company database. No org_id anywhere.
//!
//! Milestone: M1-03, M2-01. Empty until then; see docs/milestones/.
//!
//! - TODO: One writer thread owns the write connection; a small read pool serves queries.
//! - TODO: Every change writes an events row in the same transaction; after commit it is published to the realtime hub.
//! - TODO: Fractional rank strings with rebalance past 32 characters (M2-01).
