//! Bounded per-authenticated-lane PN replay admission.
//! Important: no public method accepts a naked/unverified PN. The window only
//! changes after LaneRxCrypto's real AEAD AND inner kind/marker validation.
//! A 256-PN tagged page uses 40 bytes. A window of N bits requires N/256+1
//! pages, because an N-PN sliding interval may intersect N/256+1 pages.
#![forbid(unsafe_code)]

use crate::record_crypto::{CryptoError, DirectionKeys, LaneRxCrypto, OpenedRecord, RecordSuite};

const PAGE_PNS: u64 = 256;
const MAX_REPLAY_METADATA_BYTES: usize = 8 * 1024 * 1024;
const PAGE_UNSET: u64 = u64::MAX;
const PAGE_BYTES: usize = core::mem::size_of::<ReplayPage>();

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ReplayConfigError {
    ZeroPnRate,
    TooLittleMetadata,
    RequestedWindowOverflow,
    AllocationFailed,
    Crypto(CryptoError),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum UniqueOpenError {
    InvalidRecord(CryptoError),
    Duplicate,
    Retired,
}

#[derive(Debug, Clone, Copy)]
pub struct ReplayWindowConfig {
    pub pn_per_second: u64,
    /// Duration a FrozenRecord can still be retransmitted.
    pub cache_horizon_ms: u64,
    pub fec_horizon_ms: u64,
    pub rtt_ms: u64,
    /// Per-lane budget for the actual tagged-page array (not the owner's
    /// surrounding lane allocation); also hard-limited to 8 MiB.
    pub metadata_budget_bytes: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ReplayWindowInfo {
    /// Rounded-up, 256-PN-aligned, theoretical next-power-of-two request.
    pub requested_window_pn: u64,
    /// Actual guaranteed unique-PN interval, at most the requested width.
    pub effective_window_pn: u64,
    /// Actual metadata allocated; includes the extra boundary page.
    pub allocated_metadata_bytes: usize,
    pub hard_budget_bytes: usize,
    pub effective_reorder_ms: u64,
    pub required_horizon_ms: u64,
    pub limited_by_budget: bool,
    pub pages: usize,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct ReplayStats {
    pub delivered: u64,
    pub duplicates: u64,
    pub retired: u64,
    pub invalid_records: u64,
}

#[derive(Debug, Clone)]
struct ReplayPage {
    tag: u64,
    words: [u64; 4],
}

impl Default for ReplayPage {
    fn default() -> Self { Self { tag: PAGE_UNSET, words: [0;4] } }
}

struct ReplayWindow {
    pages: Vec<ReplayPage>,
    info: ReplayWindowInfo,
    max_seen: Option<u64>,
    retired_floor: u64,
    stats: ReplayStats,
}

impl ReplayWindow {
    fn new(config: ReplayWindowConfig) -> Result<Self, ReplayConfigError> {
        if config.pn_per_second == 0 { return Err(ReplayConfigError::ZeroPnRate); }
        // Computing in u128 avoids premature overflow for practical u64 rates.
        let horizon = u128::from(config.cache_horizon_ms.max(config.fec_horizon_ms))
            .checked_add(u128::from(config.rtt_ms)*2)
            .ok_or(ReplayConfigError::RequestedWindowOverflow)?;
        let numerator = u128::from(config.pn_per_second)
            .checked_mul(horizon)
            .and_then(|v|v.checked_mul(5))
            .ok_or(ReplayConfigError::RequestedWindowOverflow)?;
        // ceil(rate*milliseconds*1.25 / 1000)
        let raw = numerator / 4000 + u128::from(numerator % 4000 != 0);
        let requested = raw.max(PAGE_PNS as u128)
            .checked_next_power_of_two()
            .ok_or(ReplayConfigError::RequestedWindowOverflow)?;
        if requested > u64::MAX as u128 {
            return Err(ReplayConfigError::RequestedWindowOverflow);
        }
        let budget = config.metadata_budget_bytes.min(MAX_REPLAY_METADATA_BYTES);
        // The window's N consecutive PNs can straddle N/256+1 pages.
        // Reducing only the number of pages (without resizing the window)
        // would silently permit replay near a 256-PN boundary.
        let mut actual = requested as u64;
        while (actual / PAGE_PNS + 1) as u128 * PAGE_BYTES as u128 > budget as u128 {
            if actual <= PAGE_PNS { return Err(ReplayConfigError::TooLittleMetadata); }
            actual /= 2;
        }
        let count = (actual / PAGE_PNS + 1) as usize;
        let bytes = count * PAGE_BYTES;
        let mut pages = Vec::new();
        pages.try_reserve_exact(count).map_err(|_|ReplayConfigError::AllocationFailed)?;
        pages.resize_with(count, ReplayPage::default);
        let effective_ms = (u128::from(actual)*1000/u128::from(config.pn_per_second))
            .min(u64::MAX as u128) as u64;
        let info = ReplayWindowInfo {
            requested_window_pn: requested as u64,
            effective_window_pn: actual,
            allocated_metadata_bytes: bytes,
            hard_budget_bytes: budget,
            effective_reorder_ms: effective_ms,
            required_horizon_ms: horizon.min(u64::MAX as u128) as u64,
            limited_by_budget: actual != requested as u64,
            pages: count,
        };
        Ok(Self { pages, info, max_seen: None, retired_floor:0, stats:ReplayStats::default() })
    }

    /// Called only by ReplayProtectedLaneRx *after* authenticated OpenRecord.
    /// No modulo-number comparisons: u64 PN strictly increases, never wraps.
    /// A giant verified jump resets only its destination tagged page (O(1)).
    fn observe_authenticated(&mut self, pn: u64) -> Result<(), UniqueOpenError> {
        if self.max_seen.is_some() && pn < self.retired_floor {
            self.stats.retired = self.stats.retired.saturating_add(1);
            return Err(UniqueOpenError::Retired);
        }
        if self.max_seen.is_none_or(|prior|pn>prior) {
            self.max_seen = Some(pn);
            self.retired_floor = pn.saturating_sub(self.info.effective_window_pn - 1);
        }
        let tag=pn/PAGE_PNS;
        let slot=(tag % self.pages.len() as u64) as usize;
        let bit=pn%PAGE_PNS;
        let page=&mut self.pages[slot];
        if page.tag != tag {
            page.tag=tag;
            page.words=[0;4];
        }
        let word=&mut page.words[(bit/64) as usize];
        let mask=1u64 << (bit%64);
        if (*word & mask)!=0 {
            self.stats.duplicates=self.stats.duplicates.saturating_add(1);
            return Err(UniqueOpenError::Duplicate);
        }
        *word |= mask;
        self.stats.delivered=self.stats.delivered.saturating_add(1);
        Ok(())
    }
}

/// Exposes only a verified, unique business delivery path; the original
/// unwindowed LaneRxCrypto remains available for legacy M0 integration but
/// MUST NOT be used to deliver unfiltered bytes after adopting this owner.
pub struct ReplayProtectedLaneRx {
    crypto: LaneRxCrypto,
    replay: ReplayWindow,
}

impl ReplayProtectedLaneRx {
    pub fn new(keys: DirectionKeys, max_wire: usize, config: ReplayWindowConfig)
        -> Result<Self, ReplayConfigError>
    {
        Self::new_for_suite(keys, max_wire, RecordSuite::ChaCha20Poly1305, config)
    }

    pub fn new_for_suite(
        keys: DirectionKeys, max_wire: usize, suite: RecordSuite, config: ReplayWindowConfig
    ) -> Result<Self, ReplayConfigError> {
        let replay=ReplayWindow::new(config)?;
        let crypto=LaneRxCrypto::new_for_suite(keys,max_wire,suite)
            .map_err(ReplayConfigError::Crypto)?;
        Ok(Self {crypto,replay})
    }

    pub fn info(&self) -> ReplayWindowInfo { self.replay.info }
    pub fn stats(&self) -> ReplayStats { self.replay.stats }
    pub fn max_seen(&self) -> Option<u64> { self.replay.max_seen }
    pub fn retired_floor(&self) -> u64 { self.replay.retired_floor }

    /// Always performs real AEAD even for repeats or PNs below retired floor.
    /// No receiver path can observe unverified PN or mutate replay metadata.
    /// On Err, no application payload is released to LINK or Health.
    pub fn open_unique_in_place<'a>(&mut self, wire:&'a mut [u8])
        -> Result<OpenedRecord<'a>, UniqueOpenError>
    {
        let record=match self.crypto.open_in_place(wire) {
            Ok(record)=>record,
            Err(err)=>{
                self.replay.stats.invalid_records=self.replay.stats.invalid_records.saturating_add(1);
                return Err(UniqueOpenError::InvalidRecord(err));
            }
        };
        self.replay.observe_authenticated(record.pn)?;
        Ok(record)
    }
}
