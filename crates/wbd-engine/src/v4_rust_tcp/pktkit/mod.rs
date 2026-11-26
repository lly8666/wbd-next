//! Local port of the upstream sans-I/O TCP implementation.
#![allow(dead_code, unused_imports, unexpected_cfgs)]
#[macro_use]
mod macros;
mod time;
mod rand;
mod stats;
pub(crate) mod vtcp;
