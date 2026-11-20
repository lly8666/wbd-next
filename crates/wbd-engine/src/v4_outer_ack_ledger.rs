//! H2229: one cosmetic, authenticated TCP appearance ACK ledger for Game2/4.
//! NOT a delivery queue, true kernel TCP endpoint, M2 receipt, FEC reorder
//! barrier, retransmission oracle, or peer liveness/Health authority.
//! The same bounded coalescing rule as Windows Normal and Linux Normal M4.
//! Each TLS lane/generation owns a separate instance, reinitialized on rekey.
#![allow(dead_code)]
use wbd_platform::rx_ipv4_tcp::extend_seq32;
use wbd_platform::ipv4_tcp::SackRange32;

pub(crate) const STEADY_TCP_WINDOW:u16=65535;
// A Linux/Windows normal delayed ACK is commonly bounded in the tens of ms;
// this project's presentation-only immediate-first / max-10ms batching only
// occurs after authenticated peer traffic and cannot gate inner delivery.
pub(crate) const OUTER_ACK_COALESCE_NS:u64=10_000_000;
pub(crate) const OUTER_ACK_STALLED_NS:u64=250_000_000;

pub(crate) struct CosmeticAckLedger{
    pub(crate) next:u64,
    pub(crate) future:Vec<(u64,u64)>,
    stalled:Option<(u64,u64)>,
}
impl CosmeticAckLedger{
    pub(crate) fn new(next:u32)->Self{
        Self{next:u64::from(next),future:Vec::with_capacity(256),stalled:None}
    }
    pub(crate) fn verified(&mut self,seq:u32,len:usize)->u32{
        let Ok(start)=extend_seq32(self.next,seq)else{return self.next as u32};
        self.verified_absolute(start,len)
    }
    pub(crate) fn verified_absolute(&mut self,start:u64,len:usize)->u32{
        let Some(end)=start.checked_add(len as u64)else{return self.next as u32};
        if len==0 || end<=self.next{return self.next as u32}
        if start<=self.next{self.next=self.next.max(end)}
        else{
            let at=self.future.partition_point(|(_,end)|*end<start);
            let(mut first,mut last)=(start,end);
            let mut until=at;
            while until<self.future.len()&&self.future[until].0<=last{
                first=first.min(self.future[until].0);
                last=last.max(self.future[until].1);
                until+=1;
            }
            if until==at&&self.future.len()>=256{
                // Authentication cannot authorize unbounded ACK memory or
                // a speculative jump. Inner delivery already happened.
                return self.next as u32
            }
            self.future.splice(at..until,std::iter::once((first,last)));
        }
        while let Some(&(first,end))=self.future.first(){
            if first>self.next{break}
            self.next=self.next.max(end);
            self.future.remove(0);
        }
        self.next as u32
    }
    /// Only another AUTHENTICATED peer packet may abandon an old cosmetic
    /// head. Never changes the unique M3/Game delivery result.
    pub(crate) fn abandon_stalled(&mut self,now:u64)->bool{
        let Some((_,end))=self.future.last().copied()else{
            self.stalled=None;return false
        };
        if self.stalled.is_none_or(|(seq,_)|seq!=self.next){
            self.stalled=Some((self.next,now));return false
        }
        if now.saturating_sub(self.stalled.unwrap().1)<OUTER_ACK_STALLED_NS{return false}
        self.next=self.next.max(end);
        self.future.clear();
        self.stalled=None;
        true
    }
    pub(crate) fn sacks(&self)->([SackRange32;4],usize){
        let mut out=[SackRange32{start:0,end:0};4];
        let mut n=0;
        for &(start,end) in self.future.iter().rev().take(4){
            out[n]=SackRange32{start:start as u32,end:end as u32};
            n+=1;
        }
        (out,n)
    }
}
/// First positive authenticated progress can be acknowledged immediately.
/// Follow-up ACK-only datagrams are bounded to 100/s/lane, including SACK
/// revisions; independent local DATA may piggyback at any pace.
pub(crate) fn ack_only_due(last:Option<u64>,now:u64,positive_change:bool)->bool{
    positive_change&&last.is_none_or(|n|now.saturating_sub(n)>=OUTER_ACK_COALESCE_NS)
}
#[cfg(test)]
mod tests{
    use super::*;
    #[test]
    fn out_of_order_authentication_never_blocks_inner_delivery_or_fakes_cumulative(){
        let mut x=CosmeticAckLedger::new(1000);
        for i in 0..600u32{assert_eq!(x.verified(2000+i*10,10),1000)}
        assert_eq!(x.future,vec![(2000,8000)]);
        let (s,n)=x.sacks();assert_eq!(n,1);
        assert_eq!((s[0].start,s[0].end),(2000,8000));
        assert_eq!(x.verified(1000,1000),8000);
        assert!(x.future.is_empty());
        assert_eq!(x.verified(7000,10),8000);
    }
    #[test]
    fn wrap_duplicate_and_rekey_never_borrow_previous_generation(){
        let mut a=CosmeticAckLedger::new(0xffff_fff0);
        assert_eq!(a.verified(0xffff_fff0,32),16);
        assert_eq!(a.verified(0xffff_fff0,32),16);
        let b=CosmeticAckLedger::new(0x10101010);
        assert_eq!(b.next,0x10101010);
        assert!(b.future.is_empty());
    }
    #[test]
    fn positive_only_abandon_never_claims_reliable_business_delivery(){
        let mut a=CosmeticAckLedger::new(100);
        a.verified(200,10);
        assert!(!a.abandon_stalled(1));
        assert!(!a.abandon_stalled(200_000_000));
        assert!(a.abandon_stalled(250_000_002));
        assert_eq!(a.next,210);
    }
    #[test]
    fn delayed_ack_is_bounded_and_requires_positive_crypto_progress(){
        assert!(!ack_only_due(None,1,false));
        assert!(ack_only_due(None,1,true));
        assert!(!ack_only_due(Some(100),100+OUTER_ACK_COALESCE_NS-1,true));
        assert!(ack_only_due(Some(100),100+OUTER_ACK_COALESCE_NS,true));
        assert!(!ack_only_due(Some(100),100+OUTER_ACK_COALESCE_NS,false));
        assert_eq!(STEADY_TCP_WINDOW,65535);
    }
}
