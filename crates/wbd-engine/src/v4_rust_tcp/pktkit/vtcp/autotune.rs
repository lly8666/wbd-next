//! Process-wide bound on buffer auto-tuning.
//!
//! Each connection grows its send and receive buffers past their initial
//! sizes as the path calls for (see [`ConnConfig::autotune`]), which with
//! enough connections could add up to more memory than the host has. Like
//! Linux's `tcp_mem`, one counter tracks what all connections have grown by
//! together; once it reaches the budget, buffers stay where they are until
//! other connections give some back, which they do when they close and
//! when they go idle. Running short only caps throughput: nothing fails.
//!
//! [`ConnConfig::autotune`]: super::ConnConfig::autotune

use crate::v4_rust_tcp::pktkit::time::Instant;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Duration;

use super::seqspace::seq_before;

/// What all connections together may grow their buffers by: room for 16
/// connections at the default maximum, both directions grown in full, or
/// many more that need less.
pub(crate) const AUTOTUNE_BUDGET: usize = 256 << 20;

/// Bytes of buffer growth handed out, against a cap.
#[derive(Debug)]
pub(crate) struct Budget {
    used: AtomicUsize,
    cap: usize,
}

/// The budget every connection draws on, unless a test gives it its own.
pub(crate) static GLOBAL: Budget = Budget::new(AUTOTUNE_BUDGET);

impl Budget {
    pub(crate) const fn new(cap: usize) -> Self {
        Self {
            used: AtomicUsize::new(0),
            cap,
        }
    }

    /// Take up to `want` bytes, as much as is left. Returns what was taken,
    /// which may be less, or nothing.
    pub(crate) fn reserve(&self, want: usize) -> usize {
        let mut cur = self.used.load(Ordering::Relaxed);
        loop {
            let got = want.min(self.cap.saturating_sub(cur));
            if got == 0 {
                return 0;
            }
            match self.used.compare_exchange_weak(
                cur,
                cur + got,
                Ordering::Relaxed,
                Ordering::Relaxed,
            ) {
                Ok(_) => return got,
                Err(actual) => cur = actual,
            }
        }
    }

    /// Give back `n` bytes taken by [`reserve`](Self::reserve).
    pub(crate) fn release(&self, n: usize) {
        if n > 0 {
            self.used.fetch_sub(n, Ordering::Relaxed);
        }
    }

    #[cfg(test)]
    pub(crate) fn used(&self) -> usize {
        self.used.load(Ordering::Relaxed)
    }
}

/// Receive-side dynamic right-sizing (Linux's `tcp_rcv_space_adjust`,
/// after Fisk and Feng's DRS): once per round trip, see how much the
/// application read in it. A window only as large as that holds the
/// sender to the rate the application already reached; twice as much
/// lets it double, as slow start does, and more still if it doubled last
/// time too.
#[derive(Debug)]
pub(crate) struct RcvSpace {
    /// Bytes the application has read, in all.
    copied: u64,
    /// `copied` and the time when the current measurement began.
    mark: u64,
    /// Distinct retained receive sequence progress at the same measurement edge.
    arrival_mark: u64,
    // One preceding measurement with distinct arrivals ahead of consumption.
    pair_previous: Option<(u64,u64,Duration)>,
    pair_hits: u64,
    time: Instant,
    /// The most read in one measurement so far.
    space: usize,
    /// The receiver's own round-trip estimate (Linux's `rcv_rtt_est`), for a
    /// connection that may send nothing to time: the least time a window's
    /// worth of data took to arrive, or smoothed timestamp echoes.
    rtt: Option<Duration>,
    /// Most recent timestamp echo considered by Linux-style receive RTT.
    last_tsecr: u32,
    /// While timing a window: the sequence number that ends it, and when it
    /// began.
    rtt_mark: Option<(u32, Instant)>,
}

impl RcvSpace {
    /// `space` is what a round trip is assumed to carry before any has
    /// been measured: the peer's initial window.
    pub(crate) fn new(space: usize) -> Self {
        Self {
            copied: 0,
            mark: 0,
            arrival_mark: 0,
            pair_previous: None,
            pair_hits: 0,
            time: Instant::now(),
            space: space.max(1),
            rtt: None,
            last_tsecr: 0,
            rtt_mark: None,
        }
    }

    /// Measure afresh from `space`, as a new connection would: after the
    /// buffer went back to its initial size, the most ever read in a
    /// round trip would hold its growth off until the application read
    /// more than that again.
    pub(crate) fn restart(&mut self, space: usize, now: Instant, arrived: u64) {
        self.space = space.max(1);
        self.mark = self.copied;
        self.arrival_mark = arrived;
        self.pair_previous = None;
        self.time = now;
    }

    pub(crate) fn pair_hits(&self)->u64{self.pair_hits}

    /// Move the start of the current measurement `by` into the past, as if
    /// that much time had gone by since.
    #[cfg(test)]
    pub(crate) fn backdate(&mut self, by: Duration) {
        self.time = self.time.checked_sub(by).unwrap_or(self.time);
    }

    /// The application read `n` bytes.
    #[inline]
    pub(crate) fn on_read(&mut self, n: usize) {
        self.copied += n as u64;
    }

    /// In-order data advanced RCV.NXT to `rcv_nxt`, with `edge` the right
    /// edge of the window last advertised (Linux's `tcp_rcv_rtt_measure`).
    /// Filling a window takes at least a round trip, more when the sender is
    /// held back by something else, so the smallest of these is the
    /// estimate.
    pub(crate) fn measure_window(&mut self, rcv_nxt: u32, edge: u32, now: Instant) {
        if let Some((end, start)) = self.rtt_mark {
            if seq_before(rcv_nxt, end) {
                return;
            }
            let sample = now.saturating_duration_since(start);
            if !sample.is_zero() {
                self.rtt = Some(self.rtt.map_or(sample, |r| r.min(sample)));
            }
        }
        self.rtt_mark = Some((edge, now));
    }

    /// A round-trip sample from a timestamp echo on a full-sized segment
    /// (Linux's `tcp_rcv_rtt_measure_ts`), smoothed as RFC 6298 does SRTT.
    pub(crate) fn measure_ts(&mut self, sample: Duration) {
        if sample.is_zero() {
            return;
        }
        self.rtt = Some(self.rtt.map_or(sample, |r| (r * 7 + sample) / 8));
    }

    /// Linux tcp_rcv_rtt_measure_ts/tcp_rcv_rtt_update: one observation per
    /// new echo, only on a full-sized segment. A shorter observation can
    /// replace the estimate immediately; a longer one is usable only if
    /// the application has drained the in-order queue before this arrival.
    pub(crate) fn measure_ts_linux(&mut self, ecr:u32, sample:Duration, full:bool, unread:usize) {
        if ecr == self.last_tsecr { return; }
        self.last_tsecr = ecr;
        if !full || sample.is_zero() { return; }
        match self.rtt {
            None => self.rtt = Some(sample),
            Some(old) if sample < old => self.rtt = Some(sample),
            Some(old) if unread == 0 => self.rtt = Some((old * 7 + sample) / 8),
            _ => {}
        }
    }

    /// The receiver's round-trip estimate, and the most read in a round
    /// trip so far, for `TcpInfo`.
    pub(crate) fn snapshot(&self) -> (Option<Duration>, usize) {
        (self.rtt, self.space)
    }

    /// The round trip that paces the measurement: the receiver's own
    /// estimate, or `srtt` from our sending if smaller (or the only one).
    fn rtt(&self, srtt: Option<Duration>) -> Option<Duration> {
        match (self.rtt, srtt) {
            (Some(a), Some(b)) => Some(a.min(b)),
            (a, b) => a.or(b),
        }
    }

    /// Linux v7.0 tcp_rcv_space_adjust/tcp_rcvbuf_grow expressed in
    /// payload-window units. The receiver RTT is the actual interval, not
    /// one eighth of it: Linux's stored estimator is scaled by eight.
    /// Kernel skb truesize conversion has no equivalent in this byte ring.
    /// Adapt its growth input to a relay: releasing an old OFO backlog to
    /// the next TCP leg is not a new network arrival. Measure both actual
    /// consumption and distinct retained arrivals over the same elapsed
    /// interval, expressed per receiver RTT. Preserve the growth equation.
    pub(crate) fn adjust_linux(&mut self, now: Instant, unread: usize, ooo_span: usize, arrived: u64, pair:bool) -> Option<usize> {
        let rtt = self.rtt?;
        let elapsed = now.saturating_duration_since(self.time);
        if elapsed < rtt { return None; }
        let copied = (self.copied - self.mark).saturating_sub(unread as u64);
        let fresh = arrived.saturating_sub(self.arrival_mark);
        self.mark = self.copied;
        self.arrival_mark = arrived;
        self.time = now;
        let normalize=|c:u64,f:u64,dt:Duration| ((u128::from(c.min(f))*rtt.as_nanos()/dt.as_nanos()).min(usize::MAX as u128)) as usize;
        let mut measured=normalize(copied,fresh,elapsed);
        // A gap can put retention and consumption in adjacent epochs. Use
        // both real intervals once, only when their imbalances complement
        // each other. Old released bytes alone cannot grow the estimate.
        if pair {
            if let Some((c,f,dt))=self.pair_previous.take(){
                if copied>fresh {
                    let combined=normalize(c.saturating_add(copied),f.saturating_add(fresh),dt+elapsed);
                    if combined>measured && combined>self.space {measured=combined;self.pair_hits+=1;}
                }
            }
            if ooo_span>0 && fresh>copied {self.pair_previous=Some((copied,fresh,elapsed));}
        }
        let copied=measured;
        if copied <= self.space { return None; }
        let window = copied.saturating_mul(2);
        // Actual previous ARM fixture: tcp_rcvbuf_low_rtt=1000 us.
        let low_rtt = Duration::from_micros(1000);
        let growth = if rtt < low_rtt {
            (window as u128 * rtt.as_nanos() / low_rtt.as_nanos()) as usize
        } else {
            ((window as u128 * 2 * (copied - self.space) as u128 / self.space as u128).min(usize::MAX as u128)) as usize
        };
        self.space = copied;
        Some(window.saturating_add(growth).saturating_add(ooo_span))
    }

    /// Called after a read: once a round trip has passed since the last
    /// measurement, the buffer size wanted for what the application read
    /// in it, if that is more than ever before. `mss` is the largest
    /// segment we accept.
    pub(crate) fn adjust(
        &mut self,
        now: Instant,
        srtt: Option<Duration>,
        mss: usize,
    ) -> Option<usize> {
        let rtt = self.rtt(srtt)?;
        if now.saturating_duration_since(self.time) < rtt {
            return None;
        }
        let copied = usize::try_from(self.copied - self.mark).unwrap_or(usize::MAX);
        self.mark = self.copied;
        self.time = now;
        if copied <= self.space {
            return None;
        }
        // Linux's arithmetic: twice what was read, room for reordering and
        // SACKed data on top, and twice the growth over the last round
        // trip besides, since a sender in slow start keeps doubling.
        let mut want = copied
            .saturating_mul(2)
            .saturating_add(mss.saturating_mul(16));
        let grow = (want as u128 * (copied - self.space) as u128 / self.space as u128)
            .min(usize::MAX as u128) as usize;
        want = want.saturating_add(grow.saturating_mul(2));
        self.space = copied;
        Some(want)
    }
}

/// The send buffer wanted for a congestion window of `cwnd` bytes (Linux's
/// `tcp_sndbuf_expand`): the window in flight and as much again queued
/// behind it, so the application can refill what each ACK frees before
/// the window needs it, and so a window that grows by half or doubles in
/// the next round trip finds the data already there.
pub(crate) fn sndbuf_target(cwnd: u32, mss: u32) -> usize {
    // Never below the initial window, as Linux counts at least
    // TCP_INIT_CWND segments.
    sndbuf_target_with_factor(cwnd, mss, 2)
}

pub(crate) fn sndbuf_target_with_factor(cwnd: u32, mss: u32, factor: usize) -> usize {
    (cwnd.max(mss.saturating_mul(10)) as usize).saturating_mul(factor)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reserve_hands_out_what_is_left() {
        let b = Budget::new(1000);
        assert_eq!(b.reserve(600), 600);
        assert_eq!(b.reserve(600), 400);
        assert_eq!(b.reserve(1), 0);
        b.release(500);
        assert_eq!(b.used(), 500);
        assert_eq!(b.reserve(100), 100);
    }

    const MS: Duration = Duration::from_millis(1);

    #[test]
    fn waits_a_round_trip_and_grows_past_twice_the_rate() {
        let t0 = Instant::now();
        let mut r = RcvSpace::new(14600);
        r.time = t0;
        // No round trip known: nothing to pace by.
        r.on_read(100_000);
        assert_eq!(r.adjust(t0 + 100 * MS, None, 1460), None);
        // Known, but not yet elapsed.
        let srtt = Some(100 * MS);
        assert_eq!(r.adjust(t0 + 50 * MS, srtt, 1460), None);
        let want = r.adjust(t0 + 100 * MS, srtt, 1460).unwrap();
        assert!(want >= 2 * 100_000, "{want}");
        // The same rate again asks for nothing more.
        r.on_read(100_000);
        assert_eq!(r.adjust(t0 + 200 * MS, srtt, 1460), None);
        // Doubling it asks for well over twice as much.
        r.on_read(200_000);
        let more = r.adjust(t0 + 300 * MS, srtt, 1460).unwrap();
        assert!(more >= 4 * 200_000, "{more}");
    }

    #[test]
    fn linux_growth_uses_receive_rtt_unread_and_ooo_span() {
        let t = Instant::now();
        let mut r = RcvSpace::new(10_000);
        r.time = t;
        r.measure_ts(100 * MS);
        r.on_read(30_000);
        assert_eq!(r.adjust_linux(t + 50 * MS, 10_000, 500, 30_000, false), None);
        // copied=20k, window=40k, growth=80k, OOO span=500.
        assert_eq!(r.adjust_linux(t + 100 * MS, 10_000, 500, 30_000, false), Some(120_500));
        let mut low = RcvSpace::new(10_000);
        low.time = t;
        low.measure_ts(Duration::from_micros(500));
        low.on_read(20_000);
        assert_eq!(low.adjust_linux(t + Duration::from_micros(500), 0, 0, 20_000, false), Some(60_000));
    }

    #[test]
    fn relay_drs_measures_fresh_arrivals_not_old_ooo_release_or_long_interval() {
        let t = Instant::now();
        let mut r = RcvSpace::new(10_000);
        r.time = t;
        r.measure_ts(100 * MS);
        // 80k already retained, only 20k consumed during this RTT.
        r.on_read(20_000);
        assert_eq!(r.adjust_linux(t + 100 * MS, 0, 0, 80_000, false), Some(120_000));
        // A repaired hole releases 60k, but only 10k arrived this RTT.
        r.on_read(60_000);
        assert_eq!(r.adjust_linux(t + 200 * MS, 0, 0, 90_000, false), None);
        assert_eq!(r.snapshot().1, 20_000);
        // 60k genuinely new bytes, but over three RTTs, not one.
        r.on_read(60_000);
        assert_eq!(r.adjust_linux(t + 500 * MS, 0, 0, 150_000, false), None);
        assert_eq!(r.snapshot().1, 20_000);
        // Actual increased supply and consumption still grow the window.
        r.on_read(30_000);
        assert_eq!(r.adjust_linux(t + 600 * MS, 0, 0, 180_000, false), Some(120_000));
        assert_eq!(r.snapshot().1, 30_000);
        r.restart(10_000, t + 600 * MS, 180_000);
        r.on_read(5_000);
        assert_eq!(r.adjust_linux(t + 700 * MS, 0, 0, 185_000, false), None);
    }

    #[test]
    fn relay_drs_pairs_complementary_adjacent_arrival_and_consumption(){
        let t=Instant::now();
        let mut r=RcvSpace::new(10_000);
        r.time=t;
        r.measure_ts(100*MS);
        r.on_read(5_000);
        assert_eq!(r.adjust_linux(t+100*MS,0,45_000,50_000,true),None);
        r.on_read(45_000);
        assert_eq!(r.adjust_linux(t+200*MS,0,0,60_000,true),Some(200_000));
        assert_eq!(r.pair_hits(),1);
        r.on_read(45_000);
        assert_eq!(r.adjust_linux(t+300*MS,0,0,60_000,true),None);
        assert_eq!(r.pair_hits(),1);
    }

    #[test]
    fn linux_receive_rtt_counts_new_full_echo_and_not_unread_inflation() {
        let mut r = RcvSpace::new(10_000);
        r.measure_ts_linux(1, 400 * MS, true, 0);
        r.measure_ts_linux(1, 800 * MS, true, 0);
        assert_eq!(r.snapshot().0, Some(400 * MS));
        r.measure_ts_linux(2, 800 * MS, true, 1);
        assert_eq!(r.snapshot().0, Some(400 * MS));
        r.measure_ts_linux(3, 800 * MS, false, 0);
        r.measure_ts_linux(3, 800 * MS, true, 0);
        assert_eq!(r.snapshot().0, Some(400 * MS));
        r.measure_ts_linux(4, 380 * MS, true, 100);
        assert_eq!(r.snapshot().0, Some(380 * MS));
        r.measure_ts_linux(5, 460 * MS, true, 0);
        assert_eq!(r.snapshot().0, Some(390 * MS));
    }

    #[test]
    fn window_timing_keeps_the_fastest_fill() {
        let t0 = Instant::now();
        let mut r = RcvSpace::new(14600);
        r.measure_window(0, 1000, t0);
        r.measure_window(500, 1000, t0 + 10 * MS); // not yet at the edge
        assert_eq!(r.rtt, None);
        r.measure_window(1000, 5000, t0 + 80 * MS);
        assert_eq!(r.rtt, Some(80 * MS));
        r.measure_window(5000, 9000, t0 + 200 * MS);
        assert_eq!(r.rtt, Some(80 * MS));
        r.measure_window(9000, 9500, t0 + 250 * MS);
        assert_eq!(r.rtt, Some(50 * MS));
        // A smaller SRTT from our own sending wins.
        assert_eq!(r.rtt(Some(20 * MS)), Some(20 * MS));
        assert_eq!(r.rtt(None), Some(50 * MS));
    }

    #[test]
    fn send_target_is_twice_the_window() {
        assert_eq!(sndbuf_target(1 << 20, 1460), 2 << 20);
        assert_eq!(sndbuf_target(1460, 1460), 2 * 14600);
    }
}
