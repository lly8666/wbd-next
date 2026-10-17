//! Frozen M1-012 directional owner API. Production/default worker builds
//! retain the old bounded std sync_channel compatibility implementation.
//! M0-provided =0.3.2 rtrb only selected by explicit shared feature
//! `m1_rtrb`, whose root definition/locked CI belongs to M0.
//! No unsafe SPSC or chunk API is implemented by M1.
#![forbid(unsafe_code)]
pub(crate) use super::{TxKind,wake};

#[cfg(feature="m1_rtrb")]
#[path="directional_rtrb.rs"]
mod selected;
#[cfg(not(feature="m1_rtrb"))]
#[path="directional_compat.rs"]
mod selected;

pub use selected::*;
