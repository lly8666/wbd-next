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
const COSMETIC_SHADOW_AGE_NS: u64 = 1_400_000_000;

/// Half of the *feedback-nominated* gaps, not half of all fresh DATA.
/// A stable PN parity hash is cheap, needs no sampling table/timer and
/// never resubmits an expired shadow. Normal first sends always take priority.
pub fn cosmetic_half_gap(pn: RecordPn) -> bool {
    pn.0.count_ones() & 1 == 0
}

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
    duplicate_acks: u8,
    // One cumulative-only gap nomination per unchanged ACK: later sends
    // alone are not a positive peer SACK and cannot prove new gaps.
    nominated_stalled_ack: Option<u64>,
    // Strictly forward across *actual unacknowledged SACK gaps*, not all
    // unacked shadows or newest 256 ciphertexts.
    last_sack_examined_seq:Option<u64>,
    gap_scanned:u64,
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
            cumulative_ack: initial_seq, duplicate_acks: 0,
            nominated_stalled_ack: None,last_sack_examined_seq:None,
            gap_scanned:0,last_sent_at: MonoNs(0),
            capacity, sent: BTreeMap::new(),
        })
    }

    pub fn outstanding(&self) -> usize { self.sent.len() }
    pub fn highest_sent_end(&self) -> u64 { self.highest_sent_end }
    pub fn gap_scanned_once(&self)->u64{self.gap_scanned}

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
        if self.sent.len() >= self.capacity {
            // The optional ACK index must recover after two seconds of
            // missing feedback. No background timer, heap scan or DATA
            // admission wait: release at most ONE oldest already-stale
            // metadata entry on an actual next kernel firstsend.
            // Shadow ciphertext has an independent <=1.5s hard expiry.
            let stale = self.sent.first_key_value().is_some_and(|(_,old)|
                now.0.saturating_sub(old.at.0) >= 2_000_000_000);
            if stale { self.sent.pop_first(); }
        }
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

        // Production currently carries cumulative ACK without negotiated
        // SACK. Three repeated, in-range ACKs may nominate only the earliest
        // outstanding gap when a genuinely later first-send exists. This is
        // an inexpensive *opportunity*, never a claim of peer delivery.
        if ack == self.cumulative_ack && sacks.is_empty() {
            self.duplicate_acks=self.duplicate_acks.saturating_add(1);
        } else {
            self.duplicate_acks=0;
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
        // At most one bounded oldest cohort per real feedback. The optional
        // ACK index can outlive its immutable <=1.5s ciphertext shadow if a
        // cumulative hole persists. No full-map scan or DATA admission gate.
        for _ in 0..64 {
            if !self.sent.first_key_value().is_some_and(|(_,span)|
                now.0.saturating_sub(span.at.0)>=900_000_000){break}
            self.sent.pop_first();
        }
        // SACK positive bytes bound an actual missing range. Walk original
        // sent order, not newest-256 tails (which can all be too young at
        // high PPS). Cursor advances over no more than 32 inspected gaps
        // per real feedback and never skips a not-yet-mature send. A stale
        // SACK is finite: it cannot nominate newly sent unrelated DATA.
        if highest_positive>ack {
            let start=self.last_sack_examined_seq
                .map_or(ack,|seq|seq.saturating_add(1).max(ack));
            let mut examined=0usize;
            let mut last=None;
            // Out-of-order older SACK summaries may have a lower bound
            // than a previously examined newer one. Empty, not panic.
            let end=highest_positive.max(start);
            for (&seq,span) in self.sent.range(start..end){
                if examined>=MAX_GAPS_PER_FEEDBACK{break}
                let age=now.0.saturating_sub(span.at.0);
                if age<50_000_000{break}
                examined+=1;
                last=Some(seq);
                if span.end<=highest_positive && age<COSMETIC_SHADOW_AGE_NS{
                    result.gap_candidates.push(span.pn);
                }
            }
            if let Some(seq)=last{self.last_sack_examined_seq=Some(seq)}
            self.gap_scanned=self.gap_scanned.saturating_add(examined as u64);
        }
        if sacks.is_empty() && self.duplicate_acks>=3 &&
            self.nominated_stalled_ack!=Some(ack) {
            if let Some((_,head))=self.sent.range(ack..).next() {
                if self.sent.range(head.end..).next().is_some() &&
                    now.0.saturating_sub(head.at.0)>=reorder_guard_ns &&
                    !result.gap_candidates.contains(&head.pn) {
                    result.gap_candidates.push(head.pn);
                    // Once this head expires, its successor is NOT a new
                    // proven gap merely because old ACKs keep arriving.
                    // Genuine SACK ranges can independently nominate later
                    // missing spans; without negotiation we wait for real
                    // cumulative progress instead of repairing on no loss.
                    self.nominated_stalled_ack=Some(ack);
                }
            }
        }
        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn h505_stalled_ack_cannot_generate_fake_loss_after_old_shadow_expires(){
        let mut x=index(100,128);
        for i in 0..3u64{
            x.on_definitely_sent(RecordPn(i+1),100+i*10,10,
                MonoNs(i*1_000_000)).unwrap();
        }
        let mut first=Vec::new();
        for now in [40_000_000,50_000_000,60_000_000]{
            first=x.on_feedback(lane(),[7;16],100,&[],MonoNs(now),
                20_000_000).unwrap().gap_candidates;
        }
        assert_eq!(first,vec![RecordPn(1)]);
        let _=x.expire(MonoNs(1_100_000_000),900_000_000);
        for i in 0..3u64{
            x.on_definitely_sent(RecordPn(i+201),130+i*10,10,
                MonoNs(1_200_000_000+i*1_000_000)).unwrap();
        }
        for now in [1_250_000_000,1_260_000_000,1_270_000_000]{
            assert!(x.on_feedback(lane(),[7;16],100,&[],MonoNs(now),
                20_000_000).unwrap().gap_candidates.is_empty());
        }
        // Only actual cumulative progress can re-arm the next eligible gap.
        assert!(x.on_feedback(lane(),[7;16],130,&[],
            MonoNs(1_280_000_000),20_000_000).unwrap()
            .gap_candidates.is_empty());
        for now in [1_300_000_000,1_310_000_000,1_320_000_000]{
            first=x.on_feedback(lane(),[7;16],130,&[],MonoNs(now),
                20_000_000).unwrap().gap_candidates;
        }
        assert_eq!(first,vec![RecordPn(201)]);
    }

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
    fn h539_half_gap_sample_and_recent_first_hints(){
        assert_eq!((0..4096).filter(|&pn|super::cosmetic_half_gap(RecordPn(pn))).count(),2048);
        assert_eq!(super::cosmetic_half_gap(RecordPn(7)),super::cosmetic_half_gap(RecordPn(7)));
        let mut x=index(0,128);
        for i in 0..100u64{
            x.on_definitely_sent(RecordPn(i),i*100,100,MonoNs(1)).unwrap();
        }
        let r=x.on_feedback(lane(),[7;16],0,
            &[SackRange32{start:9700,end:10000}],MonoNs(60_000_000),20).unwrap();
        assert!(r.gap_candidates.len()<=32);
        assert!(r.gap_candidates.iter().all(|pn|pn.0<97));
        assert!(r.gap_candidates[0].0<r.gap_candidates.last().unwrap().0);
    }
    #[test]
    fn plan027_sack_cursor_ages_old_real_gaps_without_ever_fabricating_new_ones(){
        let mut x=index(0,512);
        for i in 0..400u64{
            let at=if i<100{0}else{55_000_000};
            x.on_definitely_sent(RecordPn(i+1),i*100,100,MonoNs(at)).unwrap();
        }
        // One genuine positive SACK from the end; old gaps are older
        // than50ms, newest256 mostly too young. Only 32 visited per call.
        let sack=[SackRange32{start:39900,end:40000}];
        let first=x.on_feedback(lane(),[7;16],0,&sack,MonoNs(60_000_000),20).unwrap();
        assert_eq!(first.gap_candidates.len(),32);
        assert_eq!(first.gap_candidates[0],RecordPn(1));
        let second=x.on_feedback(lane(),[7;16],0,&sack,MonoNs(60_000_001),20).unwrap();
        assert_eq!(second.gap_candidates[0],RecordPn(33));
        assert_eq!(x.gap_scanned_once(),64);
        let third=x.on_feedback(lane(),[7;16],0,&sack,MonoNs(60_000_002),20).unwrap();
        assert_eq!(third.gap_candidates[0],RecordPn(65));
        let waiting=x.on_feedback(lane(),[7;16],0,&sack,MonoNs(60_000_003),20).unwrap();
        assert_eq!(waiting.gap_candidates.len(),4);
        // A valid but older/out-of-order SACK has a lower positive end
        // than our forward cursor. It must be harmless and cannot rewind.
        assert!(x.on_feedback(lane(),[7;16],0,
            &[SackRange32{start:4500,end:5000}],MonoNs(60_000_003),20)
            .unwrap().gap_candidates.is_empty());
        assert!(x.on_feedback(lane(),[7;16],0,&sack,MonoNs(60_000_004),20)
            .unwrap().gap_candidates.is_empty());
        // The original SACK can only continue when other candidates age;
        // already scanned PNs remain unique, not 4/7/12 per ACK cadence.
        let older=x.on_feedback(lane(),[7;16],0,&sack,MonoNs(110_000_000),20).unwrap();
        assert_eq!(older.gap_candidates[0],RecordPn(101));
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
            MonoNs(60_000_010), 20).unwrap();
        assert!(late.retired.is_empty());
        assert_eq!(late.gap_candidates, vec![RecordPn(2)]);
        assert_eq!(x.outstanding(), 1);
        assert_eq!(x.on_feedback(lane(), [7; 16], 400, &[],
            MonoNs(60_000_011), 20).unwrap().retired, vec![RecordPn(2)]);
    }
    #[test]
    fn plan027_live_cumulative_duplicate_ack_nominates_one_bounded_gap(){
        let mut x=index(100,8);
        for i in 0..3 {
            assert_eq!(x.on_definitely_sent(RecordPn(i+1),100+i*100,100,
                MonoNs(10)),Ok(true));
        }
        for _ in 0..2 {
            assert!(x.on_feedback(lane(),[7;16],100,&[],
                MonoNs(20),20).unwrap().gap_candidates.is_empty());
        }
        let late=x.on_feedback(lane(),[7;16],100,&[],
            MonoNs(31),20).unwrap();
        assert_eq!(late.gap_candidates,vec![RecordPn(1)]);
        assert!(late.retired.is_empty());
        assert_eq!(x.on_feedback(lane(),[8;16],100,&[],
            MonoNs(32),20),Err(OuterAckError::WrongScope));
        let advanced=x.on_feedback(lane(),[7;16],200,&[],
            MonoNs(33),20).unwrap();
        assert_eq!(advanced.retired,vec![RecordPn(1)]);
        assert!(advanced.gap_candidates.is_empty());
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
    fn r2_plan027_saturated_optional_outer_index_recovers_on_new_real_firstsend(){
        let mut x=index(0,2);
        assert_eq!(x.on_definitely_sent(RecordPn(1),0,100,MonoNs(1)),
            Ok(true));
        assert_eq!(x.on_definitely_sent(RecordPn(2),100,100,MonoNs(2)),
            Ok(true));
        assert_eq!(x.on_definitely_sent(RecordPn(3),200,100,
            MonoNs(1_900_000_000)),Ok(false));
        assert_eq!(x.outstanding(),2);
        assert_eq!(x.on_definitely_sent(RecordPn(4),300,100,
            MonoNs(2_000_000_002)),Ok(true));
        // One stale entry per admitted M4 result. A newer outstanding
        // index never loses its predecessor without the full 2s age.
        assert_eq!(x.outstanding(),2);
        assert_eq!(x.on_feedback(lane(),[7;16],400,&[],
            MonoNs(2_000_000_003),20).unwrap().retired,
            vec![RecordPn(2),RecordPn(4)]);
        assert_eq!(x.outstanding(),0);
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
