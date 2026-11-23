//! M0 H2229: bounded *TCP appearance only* contiguous ACK ledger and timing.
//! No authenticated receipt, peer liveness, M2 feedback, FEC, or TUN order.
//! Game Linux and Game Windows share exactly the same per-lane semantics.
//! Business delivery is independent: missing outer TCP bytes never block it.
pub(crate) const ACK_ONLY_MIN_INTERVAL_NS:u64=10_000_000;
pub(crate) const STEADY_TCP_WINDOW:u16=65_535;

pub(crate) struct NativePresentationAck{
    next:u64,
    future:Vec<(u64,u64)>,
}
impl NativePresentationAck{
    pub(crate) fn new(initial:u32)->Self{
        Self{next:u64::from(initial),future:Vec::with_capacity(256)}
    }
    pub(crate) fn ack(&self)->u32{self.next as u32}
    // Only a successfully authenticated and copied future original M3
    // record; caller tests before verified() updates the cumulative head.
    pub(crate) fn authenticated_future(&self,seq:u32)->bool{
        (seq.wrapping_sub(self.next as u32) as i32)>0
    }
    // Exactly one original cold-authenticated seq32 anchor per lane.
    // Called only after a real Game AEAD+unique-PN opener and successful
    // TUN commit. Future spans are cosmetic; never gate TUN delivery.
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
        assert_eq!(ledger.verified(100,50),160);
        assert!(!ledger.authenticated_future(160));
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
    fn h2229_wrap_and_rekey_fenced(){
        let mut a=NativePresentationAck::new(0xffff_fff0);
        assert_eq!(a.verified(0xffff_fff0,32),0x10);
        assert_eq!(a.verified(0x10,10),0x1a);
        let b=NativePresentationAck::new(17);
        assert_eq!(b.ack(),17);
    }
}
