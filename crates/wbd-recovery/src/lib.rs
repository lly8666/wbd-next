//! R1/R2 scoped worker **bootstrap only**, not recovery implementation.
//! The recovery worker owns receipt/retransmit state; no socket, crypto,
//! engine or platform dependency may be introduced into this pure crate.
#![forbid(unsafe_code)]
pub use wbd_types::{LaneKey, MonoNs, RecordPn};

/// A build-time API anchor, deliberately not a recovery algorithm.
pub const RECOVERY_ENGINE_READY: bool = false;

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn bootstrap_is_not_product_qualification() {
        assert!(!RECOVERY_ENGINE_READY);
        let now = MonoNs(9);
        assert_eq!(now.checked_after(1), Some(MonoNs(10)));
        let pn = RecordPn(u64::MAX);
        assert_eq!(pn.0, u64::MAX);
    }
}
