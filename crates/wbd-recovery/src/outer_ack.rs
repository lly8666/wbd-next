//! PLAN027 outer TCP-like ACK/SACK hints for bounded immutable repair caches.
//! This is a pure per-lane/epoch index, NOT authenticated business delivery.
//! Only definite kernel first sends enter; the owner still owns AEAD/PN,
//! frozen ciphertext, global byte quota, and driver completion/Stop.
use std::collections::BTreeMap;
use wbd_types::{LaneKey, MonoNs, RecordPn};

const HALF_SEQ: u64 = 1 << 31;
const FULL_SEQ: u64 = 1 << 32;
const MAX_ENTRIES: usize = 24_576;
const MAX_SACK_RANGES: usize = 8;
const MAX_GAPS_PER_FEEDBACK: usize = 32;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum OuterAckError {
    InvalidConfig,
    WrongScope,
    InvalidSend,
    OutOfRange,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SackRange32 {
    pub start: u32,
    pub end: u32,
}

#[derive(Debug, Default, Eq, PartialEq)]
pub struct OuterAckUpdate {
    /// May release OPTIONAL frozen repair storage; never application delivery.
    pub retired: Vec<RecordPn>,
    /// Only an opportunity. Owner must recheck shadow, age and byte budget.
    pub gap_candidates: Vec<RecordPn>,
}

#[derive(Clone, Copy)]
struct SentSpan {
    end: u64,
    pn: RecordPn,
    at: MonoNs,
}

/// One owner instance per lane+epoch. No per-packet allocations after
/// BTreeMap capacity is exhausted: missing optional cache never blocks DATA.
pub struct OuterAckIndex {
    lane: LaneKey,
    epoch: [u8; 16],
    highest_sent_end: u64,
    cumulative_ack: u64,
    last_sent_at: MonoNs,
    capacity: usize,
    sent: BTreeMap<u64, SentSpan>,
}

fn extend_near(reference: u64, low: u32) -> Result<u64, OuterAckError> {
    let mut value = (reference & !0xffff_ffff_u64) | u64::from(low);
    if value > reference && value - reference > HALF_SEQ {
        value = value.checked_sub(FULL_SEQ).ok_or(OuterAckError::OutOfRange)?;
    } else if reference > value && reference - value > HALF_SEQ {
        value = value.checked_add(FULL_SEQ).ok_or(OuterAckError::OutOfRange)?;
    }
    Ok(value)
}

impl OuterAckIndex {
    pub fn new(lane: LaneKey, epoch: [u8; 16], initial_seq: u64,
        capacity: usize) -> Result<Self, OuterAckError>
    {
        if capacity == 0 || capacity > MAX_ENTRIES {
            return Err(OuterAckError::InvalidConfig);
        }
        Ok(Self {
            lane, epoch, highest_sent_end: initial_seq,
            cumulative_ack: initial_seq, last_sent_at: MonoNs(0),
            capacity, sent: BTreeMap::new(),
        })
    }

    pub fn outstanding(&self) -> usize { self.sent.len() }
    pub fn highest_sent_end(&self) -> u64 { self.highest_sent_end }

    /// Returns false only when the optional repair index is full. A skipped
    /// span still advances the actual sent-range bound for ACK validation.
    pub fn on_definitely_sent(&mut self, pn: RecordPn, seq_start: u64,
        wire_len: u32, now: MonoNs) -> Result<bool, OuterAckError>
    {
        let end = seq_start.checked_add(u64::from(wire_len))
            .ok_or(OuterAckError::InvalidSend)?;
        if wire_len == 0 || seq_start < self.highest_sent_end
            || now < self.last_sent_at {
            return Err(OuterAckError::InvalidSend);
        }
        self.highest_sent_end = end;
        self.last_sent_at = now;
        if self.sent.len() >= self.capacity { return Ok(false); }
        self.sent.insert(seq_start, SentSpan { end, pn, at: now });
        Ok(true)
    }

    /// Amortized removal from the oldest sent sequence; caller supplies the
    /// bounded RTT-derived retention deadline, never a per-packet full scan.
    pub fn expire(&mut self, now: MonoNs, retention_ns: u64) -> Vec<RecordPn> {
        let mut expired = Vec::new();
        while let Some((&seq, span)) = self.sent.first_key_value() {
            if now.0.saturating_sub(span.at.0) < retention_ns { break; }
            if let Some(span) = self.sent.remove(&seq) {
                expired.push(span.pn);
            }
        }
        expired
    }

    /// Raw presentation ACK/SACK is untrusted: it can only retire optional
    /// shadow or nominate a bounded gap. It must not refresh Health, mark
    /// business delivered, increase first-send F, or bypass AEAD replay.
    pub fn on_feedback(&mut self, lane: LaneKey, epoch: [u8; 16],
        ack32: u32, sacks: &[SackRange32], now: MonoNs,
        reorder_guard_ns: u64) -> Result<OuterAckUpdate, OuterAckError>
    {
        if lane != self.lane || epoch != self.epoch {
            return Err(OuterAckError::WrongScope);
        }
        if sacks.len() > MAX_SACK_RANGES {
            return Err(OuterAckError::OutOfRange);
        }
        let ack = extend_near(self.highest_sent_end, ack32)?;
        if ack > self.highest_sent_end {
            return Err(OuterAckError::OutOfRange);
        }
        if ack < self.cumulative_ack {
            return Ok(OuterAckUpdate::default());
        }
        // Validate every SACK BEFORE releasing any shadow on a hostile hint.
        let mut ranges = Vec::with_capacity(sacks.len());
        let mut highest_positive = ack;
        for range in sacks {
            let start = extend_near(self.highest_sent_end, range.start)?;
            let end = extend_near(self.highest_sent_end, range.end)?;
            if start < ack || start >= end || end > self.highest_sent_end {
                return Err(OuterAckError::OutOfRange);
            }
            highest_positive = highest_positive.max(end);
            ranges.push((start, end));
        }

        let mut result = OuterAckUpdate::default();
        let cumulative: Vec<_> = self.sent.range(..ack)
            .filter_map(|(&seq, span)| (span.end <= ack).then_some(seq))
            .collect();
        for seq in cumulative {
            if let Some(span) = self.sent.remove(&seq) {
                result.retired.push(span.pn);
            }
        }
        for (start, end) in ranges {
            let positive: Vec<_> = self.sent.range(start..end)
                .filter_map(|(&seq, span)| (span.end <= end).then_some(seq))
                .collect();
            for seq in positive {
                if let Some(span) = self.sent.remove(&seq) {
                    result.retired.push(span.pn);
                }
            }
        }
        self.cumulative_ack = ack;
        // A later SACK is evidence of an OUTER sequence gap, not of inner
        // loss. Bounded candidates only; no periodic blind DATA PTO.
        for (&seq, span) in self.sent.range(ack..highest_positive) {
            if result.gap_candidates.len() >= MAX_GAPS_PER_FEEDBACK { break; }
            if span.end <= highest_positive
                && now.0.saturating_sub(span.at.0) >= reorder_guard_ns {
                let _ = seq;
                result.gap_candidates.push(span.pn);
            }
        }
        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use wbd_types::TunnelKey;

    fn lane() -> LaneKey {
        LaneKey {
            tunnel: TunnelKey { slot: 3, generation: 4 },
            slot: 2, generation: 5,
        }
    }
    fn index(initial: u64, capacity: usize) -> OuterAckIndex {
        OuterAckIndex::new(lane(), [7; 16], initial, capacity).unwrap()
    }
    #[test]
    fn r2_plan027_ack_sack_gap_only_after_guard_and_exact_retirement() {
        let mut x = index(100, 8);
        for i in 0..3 {
            assert_eq!(x.on_definitely_sent(RecordPn(i + 1),
                100 + i * 100, 100, MonoNs(10)), Ok(true));
        }
        let sacks = [SackRange32 { start: 300, end: 400 }];
        let early = x.on_feedback(lane(), [7; 16], 200, &sacks,
            MonoNs(15), 20).unwrap();
        assert_eq!(early.retired, vec![RecordPn(1), RecordPn(3)]);
        assert!(early.gap_candidates.is_empty());
        let late = x.on_feedback(lane(), [7; 16], 200, &sacks,
            MonoNs(31), 20).unwrap();
        assert!(late.retired.is_empty());
        assert_eq!(late.gap_candidates, vec![RecordPn(2)]);
        assert_eq!(x.outstanding(), 1);
        assert_eq!(x.on_feedback(lane(), [7; 16], 400, &[],
            MonoNs(32), 20).unwrap().retired, vec![RecordPn(2)]);
    }
    #[test]
    fn r2_plan027_wrap32_and_wrong_epoch_never_release() {
        let base = (1_u64 << 32) - 16;
        let mut x = index(base, 4);
        x.on_definitely_sent(RecordPn(1), base, 32, MonoNs(1)).unwrap();
        assert_eq!(x.on_feedback(lane(), [8; 16], 16, &[],
            MonoNs(2), 20), Err(OuterAckError::WrongScope));
        assert_eq!(x.on_feedback(lane(), [7; 16], 17, &[],
            MonoNs(2), 20), Err(OuterAckError::OutOfRange));
        assert_eq!(x.outstanding(), 1);
        assert_eq!(x.on_feedback(lane(), [7; 16], 16, &[],
            MonoNs(2), 20).unwrap().retired, vec![RecordPn(1)]);
    }
    #[test]
    fn r2_plan027_partial_ack_stale_ack_and_invalid_sack_are_safe() {
        let mut x = index(100, 4);
        x.on_definitely_sent(RecordPn(1), 100, 100, MonoNs(1)).unwrap();
        assert!(x.on_feedback(lane(), [7; 16], 150, &[],
            MonoNs(2), 20).unwrap().retired.is_empty());
        assert_eq!(x.on_feedback(lane(), [7; 16], 150,
            &[SackRange32 { start: 160, end: 201 }],
            MonoNs(2), 20), Err(OuterAckError::OutOfRange));
        assert_eq!(x.outstanding(), 1);
        assert!(x.on_feedback(lane(), [7; 16], 140, &[],
            MonoNs(2), 20).unwrap().retired.is_empty());
        assert_eq!(x.on_feedback(lane(), [7; 16], 200, &[],
            MonoNs(3), 20).unwrap().retired, vec![RecordPn(1)]);
    }
    #[test]
    fn r2_plan027_cache_full_does_not_block_sent_bounds_and_expires() {
        let mut x = index(0, 1);
        assert_eq!(x.on_definitely_sent(RecordPn(1), 0, 100, MonoNs(1)), Ok(true));
        assert_eq!(x.on_definitely_sent(RecordPn(2), 100, 100, MonoNs(2)), Ok(false));
        assert_eq!(x.highest_sent_end(), 200);
        assert_eq!(x.expire(MonoNs(10), 10), Vec::<RecordPn>::new());
        assert_eq!(x.expire(MonoNs(11), 10), vec![RecordPn(1)]);
        assert_eq!(x.outstanding(), 0);
        assert!(x.on_feedback(lane(), [7; 16], 200, &[],
            MonoNs(12), 20).unwrap().retired.is_empty());
    }
}
