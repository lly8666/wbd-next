//! B55 pure scheduling for original Android Game2/4 TUN TX and RAW RX.
//! No new crypto/protocol, worker, TUN reader or data queue.
pub(crate) const IDLE_WAKE_MAX_MS:i32=1_000;
// RAW RX has no Health/Game4/FEC deadline; only kernel RAW data or Stop
// eventfd needs to wake it. A 30s ceiling is a backup, not a packet timer.
pub(crate) const RAW_RX_IDLE_MAX_MS:i32=30_000;
const MAX_INLINE_TUN_BURST:u8=8;

#[derive(Default)]
pub(crate) struct GameTunBurst {consecutive:u8}
impl GameTunBurst {
    // Skip a redundant epoll between queued TUN packets. Give physical
    // DNS and Stop the existing eventfd turn after each eight reads.
    pub(crate) fn inline_next(&mut self,read_nonempty:bool)->bool{
        if !read_nonempty {self.consecutive=0;return false}
        self.consecutive+=1;
        if self.consecutive<MAX_INLINE_TUN_BURST{return true}
        self.consecutive=0;
        false
    }
}
pub(crate) fn wait_ms(
    now_ns:u64,health_due_ns:Option<u64>,game_due_ns:Option<u64>
)->i32{
    health_due_ns.into_iter().chain(game_due_ns).min()
        .map(|due|(due.saturating_sub(now_ns).saturating_add(999_999)/
            1_000_000).clamp(1,IDLE_WAKE_MAX_MS as u64) as i32)
        .unwrap_or(IDLE_WAKE_MAX_MS)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn b55_android_game_idle_event_wait_not_fixed_250ms_spin(){
        assert_eq!(wait_ms(1_000_000_000,None,None),1_000);
        assert_eq!(wait_ms(1_000_000_000,Some(16_000_000_000),None),1_000);
        assert_eq!(wait_ms(1_000_000_000,Some(1_000_000_000),None),1);
    }
    #[test]
    fn b55_android_game_game4_fec_and_health_due_not_delayed(){
        let now=1_000_000_000;
        assert_eq!(wait_ms(now,Some(now+15_000_000_000),Some(now+4_000_000)),4);
        assert_eq!(wait_ms(now,Some(now+15_000_000_000),Some(now+50_000_000)),50);
        assert_eq!(wait_ms(now,Some(now+15_000_000_000),Some(now+140_000_000)),140);
        assert_eq!(wait_ms(now,Some(now+30_000_000),Some(now+140_000_000)),30);
    }
    #[test]
    fn b56_android_game_rx_event_driven_idle_not_periodic_1s(){
        assert_eq!(RAW_RX_IDLE_MAX_MS,30_000);
        assert!(RAW_RX_IDLE_MAX_MS>IDLE_WAKE_MAX_MS);
    }
    #[test]
    fn b56_android_game_raw_rx_short_burst_and_stop_event_turn(){
        let mut rx=GameTunBurst::default();
        for _ in 0..7 {assert!(rx.inline_next(true))}
        assert!(!rx.inline_next(true),"eighth original RAW recv must give Stop fd a turn");
        assert!(rx.inline_next(true));
        assert!(!rx.inline_next(false),"WouldBlock resumes kernel readiness");
        assert!(rx.inline_next(true),"next M3 record immediately processed");
    }
    #[test]
    fn b55_android_game_business_burst_bounded_and_idle_reset(){
        let mut burst=GameTunBurst::default();
        for _ in 0..7{assert!(burst.inline_next(true))}
        assert!(!burst.inline_next(true),"event turn after eight packets");
        assert!(burst.inline_next(true),"next burst starts");
        assert!(!burst.inline_next(false),"empty TUN returns to kernel wait");
        assert!(burst.inline_next(true),"new packet not delayed for polling");
    }
}
