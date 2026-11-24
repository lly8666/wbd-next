//! M0 H2229: bounded *TCP appearance only* contiguous ACK ledger and timing.
//! No authenticated receipt, peer liveness, M2 feedback, FEC, or TUN order.
//! Game Linux and Game Windows share exactly the same per-lane semantics.
//! Business delivery is independent: missing outer TCP bytes never block it.
pub(crate) const ACK_ONLY_MIN_INTERVAL_NS:u64=10_000_000;
pub(crate) const STEADY_TCP_WINDOW:u16=65_535;

pub(crate) struct NativePresentationAck{
    next:u64,
    future:Vec<(u64,u64)>,
    stalled:Option<(u64,u64)>, // presentation-only missing-head onset
}
impl NativePresentationAck{
    pub(crate) fn new(initial:u32)->Self{
        Self{next:u64::from(initial),future:Vec::with_capacity(256),stalled:None}
    }
    pub(crate) fn ack(&self)->u32{self.next as u32}
    // Only a future original M3 record whose physical lane AEAD/PN opened;
    // logical first-delivery TUN copying is independently accounted.
    pub(crate) fn authenticated_future(&self,seq:u32)->bool{
        (seq.wrapping_sub(self.next as u32) as i32)>0
    }
    // Exactly one original cold-authenticated seq32 anchor per lane.
    // Called after a real Game AEAD+unique-PN opener; not gated on TUN
    // commit or logical cross-lane dedup. Future spans never gate delivery.
    pub(crate) fn verified(&mut self,seq:u32,len:usize)->u32{
        let distance=i64::from(i32::from_ne_bytes(
            seq.wrapping_sub(self.next as u32).to_ne_bytes()));
        if distance<0{return self.ack()}
        let Some(begin)=self.next.checked_add(distance as u64)else{
            return self.ack()
        };
        let Some(end)=begin.checked_add(len as u64)else{
            return self.ack()
        };
        if end<=self.next{return self.ack()}
        if begin<=self.next{self.next=self.next.max(end)}
        else{
            // Merge adjacent authenticated ranges before enforcing 256
            // disjoint-hole bound: a 1Gbps train must not saturate on
            // the 257th packet behind one missing span.
            let at=self.future.partition_point(|(_,last)|*last<begin);
            let (mut first,mut tail)=(begin,end);
            let mut until=at;
            while until<self.future.len()&&self.future[until].0<=tail{
                first=first.min(self.future[until].0);
                tail=tail.max(self.future[until].1);
                until+=1;
            }
            if at==until&&self.future.len()>=256{return self.ack()}
            self.future.splice(at..until,std::iter::once((first,tail)));
        }
        while self.future.first().is_some_and(|(head,_)|*head<=self.next){
            let (_,tail)=self.future.remove(0);
            self.next=self.next.max(tail);
        }
        self.ack()
    }
    /// Normal's bounded presentation-only 250ms old-hole skip. Actual Game
    /// ciphertext cannot be reconstituted from an outer TCP stream, so an
    /// indefinitely stalled appearance ACK must not starve newer SACK gaps.
    /// This does not acknowledge business, restore FEC or grant Health.
    pub(crate) fn abandon_stalled(&mut self,now_ns:u64)->bool{
        let Some((_,end))=self.future.last().copied()else{
            self.stalled=None;return false
        };
        if self.stalled.is_none_or(|(seq,_)|seq!=self.next){
            self.stalled=Some((self.next,now_ns));return false
        }
        if now_ns.saturating_sub(self.stalled.unwrap().1)<250_000_000{
            return false
        }
        self.next=self.next.max(end);
        self.future.clear();
        self.stalled=None;
        true
    }
    /// Same four newest authentic positive intervals as Normal. Fixed stack
    /// output (unlike Normal's convenient Vec), no allocation on Game RX.
    pub(crate) fn sacks4(&self)
        ->[Option<wbd_platform::ipv4_tcp::SackRange32>;4]{
        let mut spans=self.future.iter().rev().take(4);
        std::array::from_fn(|_|spans.next().map(|&(start,end)|
            wbd_platform::ipv4_tcp::SackRange32{
                start:start as u32,end:end as u32,
            }))
    }
    /// Latest actually AEAD-opened physical future span for Normal-style
    /// SACK feedback. One positive interval bounds many missing candidates;
    /// fixed-size, no allocation or separate controller in the hot path.
    pub(crate) fn latest_sack(&self)
        ->Option<wbd_platform::ipv4_tcp::SackRange32>{
        self.future.last().map(|&(start,end)|
            wbd_platform::ipv4_tcp::SackRange32{
                start:start as u32,end:end as u32,
            })
    }
}
/// No speculative ACK: only a changed authenticated cumulative head is
/// eligible. Coalesce to <=100 pure ACKs/s/lane even on a continuous RX
/// stream. DATA remains free to piggyback without this timer; in particular
/// it never waits for missing outer seq bytes or an ACK deadline.
pub(crate) fn presentation_ack_only_due(now_ns:u64,last_ns:u64,
    current:u32,last_sent:u32)->bool{
    current!=last_sent&&(last_ns==0||
        now_ns.saturating_sub(last_ns)>=ACK_ONLY_MIN_INTERVAL_NS)
}
/// Game2/4 may issue a duplicate ACK only on a NEW authenticated
/// later DATA interval. Never periodic on idle or before 10ms coalescing.
pub(crate) fn presentation_game_ack_due(now_ns:u64,last_ns:u64,
    current:u32,last_sent:u32,auth_future:bool)->bool{
    (current!=last_sent||auth_future)&&
        (last_ns==0||now_ns.saturating_sub(last_ns)>=ACK_ONLY_MIN_INTERVAL_NS)
}
#[cfg(test)]
mod tests{
    use super::*;
    #[test]
    fn r1_game_duplicate_ack_only_on_authenticated_future_and_10ms(){
        let mut ledger=NativePresentationAck::new(100);
        assert!(!ledger.authenticated_future(100));
        assert!(ledger.authenticated_future(150));
        assert!(!presentation_game_ack_due(1,0,100,100,false));
        assert!(presentation_game_ack_due(1,0,100,100,true));
        assert!(!presentation_game_ack_due(9_000_000,1,100,100,true));
        assert!(presentation_game_ack_due(10_000_001,1,100,100,true));
        assert!(!presentation_game_ack_due(10_000_001,1,100,100,false));
        assert_eq!(ledger.verified(150,10),100);
        assert_eq!(ledger.latest_sack(),Some(
            wbd_platform::ipv4_tcp::SackRange32{start:150,end:160}));
        assert_eq!(ledger.verified(100,50),160);
        assert!(ledger.latest_sack().is_none());
        assert!(!ledger.authenticated_future(160));
    }
    #[test]
    fn game_four_sack_positive_intervals_match_normal_newest_four(){
        let mut x=NativePresentationAck::new(100);
        for i in 1..=6u32{
            assert_eq!(x.verified(100+100*i,20),100);
        }
        let got=x.sacks4();
        for i in 0..4usize{
            assert_eq!(got[i],Some(wbd_platform::ipv4_tcp::SackRange32{
                start:700-(i as u32)*100,end:720-(i as u32)*100
            }));
        }
    }
    #[test]
    fn normal_stalled_outer_head_progresses_after_250ms_without_tun_receipt(){
        let mut ledger=NativePresentationAck::new(1000);
        assert_eq!(ledger.verified(1200,100),1000);
        assert_eq!(ledger.latest_sack(),Some(
            wbd_platform::ipv4_tcp::SackRange32{start:1200,end:1300}));
        assert!(!ledger.abandon_stalled(0));
        assert!(!ledger.abandon_stalled(249_000_000));
        assert_eq!(ledger.ack(),1000);
        assert!(ledger.abandon_stalled(250_000_000));
        assert_eq!(ledger.ack(),1300);
        assert!(ledger.latest_sack().is_none());
        assert!(!ledger.abandon_stalled(251_000_000));
        assert_eq!(ledger.verified(1400,100),1300);
        assert!(!ledger.abandon_stalled(300_000_000));
        assert_eq!(ledger.ack(),1300);
        assert!(!ledger.abandon_stalled(549_000_000));
        assert!(ledger.abandon_stalled(550_000_000));
        assert_eq!(ledger.ack(),1500);
    }
    #[test]
    fn h2229_10ms_ack_only_and_duplicate_suppression(){
        assert!(!presentation_ack_only_due(10,0,10,10));
        assert!(presentation_ack_only_due(10,0,11,10));
        assert!(!presentation_ack_only_due(9_999_999,1,11,10));
        assert!(presentation_ack_only_due(10_000_001,1,11,10));
        assert_eq!(STEADY_TCP_WINDOW,65535);
    }
    #[test]
    fn h2229_real_out_of_order_does_not_advance_cumulative_or_block_delivery(){
        let mut a=NativePresentationAck::new(1000);
        assert_eq!(a.verified(1200,100),1000);
        for i in 0..650{assert_eq!(a.verified(1300+i*100,100),1000)}
        assert_eq!(a.future.len(),1);
        assert_eq!(a.verified(1000,300),66300);
        assert!(a.future.is_empty());
        assert_eq!(a.verified(1400,100),66300);
    }
    #[test]
    fn a52_android_normal_off_ack_never_skips_authenticated_gap(){
        // The Android RAW M3 opener may authenticate 0x10 before the
        // earlier 0xfffffff0 span. Neither an out-of-order DATA nor a
        // replayed span may manufacture a cumulative presentation ACK.
        let mut ack=NativePresentationAck::new(0xffff_fff0);
        assert_eq!(ack.verified(0x10,40),0xffff_fff0);
        assert_eq!(ack.verified(0x30,8),0xffff_fff0);
        assert_eq!(ack.verified(0xffff_fff0,32),0x38);
        assert_eq!(ack.verified(0x10,40),0x38);
        // A 10ms coalescing deadline belongs to the same original TX
        // worker; no ACK-only loop without changed authenticated bytes.
        assert!(!presentation_ack_only_due(5_000_000,1,ack.ack(),0xffff_fff0));
        assert!(presentation_ack_only_due(10_000_001,1,ack.ack(),0xffff_fff0));
        assert!(!presentation_ack_only_due(30_000_000,10_000_001,
            ack.ack(),ack.ack()));
    }
    #[test]
    fn h2229_wrap_and_rekey_fenced(){
        let mut a=NativePresentationAck::new(0xffff_fff0);
        assert_eq!(a.verified(0xffff_fff0,32),0x10);
        assert_eq!(a.verified(0x10,10),0x1a);
        let b=NativePresentationAck::new(17);
        assert_eq!(b.ack(),17);
    }
}
