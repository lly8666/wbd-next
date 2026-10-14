//! M1-owned TX/RX runtime implementation entry point.
//! No loops, sockets or scheduling capability is enabled by this scaffold.
//! Production behavior will be integrated by M0 after separate worker proof.
#![forbid(unsafe_code)]
pub const OWNER_RUNTIME_READY: bool = false;
