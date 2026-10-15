//! Generation-tagged, bounded *UDP fixture* outcome/lease boundary on Linux.
//!
//! Integrates the existing real-kernel sendmmsg and recvmmsg only: no new
//! syscall, hot-path clone/allocation, async copied-UDP buffer ownership,
//! AF_PACKET interface attachment, Go V4 admission or shared ABI.
//!
//! A nonblocking copied UDP syscall consumes no driver-owned buffer after its
//! return. A *separate* explicit KernelLoan is available ONLY for backends
//! that report delayed completion; timeouts/STOP do not complete that loan.
//! A late completion can only be acknowledged by its ORIGINAL generation.
//! This scoped adapter never claims authenticated receipt or peer ACK.
use crate::linux_batch::submit_connected_udp;
use crate::linux_rx_batch::{receive_ready_udp, RxBatchOutcome, RxEntry};
use crate::r1::{BatchResult, BorrowError, BorrowFence, KernelLoan, StopResult};
use crate::TxError;
use std::io;
use std::net::UdpSocket;
use std::sync::Arc;
use std::time::Instant;
use wbd_types::buffer_contract::FrozenRecordHandle;

#[derive(Debug, Clone, Copy, Eq, PartialEq)]
pub enum LeaseGateError {
    StaleGeneration,
    Stopping,
    TooManyLoans,
    InvalidOutcome(TxError),
}
/// A token is moved, not cloned. Its frozen memory and old BorrowFence stay
/// alive across old->new generation rotation, STOP and delayed completion.
/// A token returned as Err must remain held by the original driver/owner.
pub struct GenerationLoan<H: FrozenRecordHandle> {
    generation: u32,
    token: KernelLoan<H>,
}
impl<H: FrozenRecordHandle> GenerationLoan<H> {
    pub fn generation(&self) -> u32 {self.generation}
    pub fn bytes(&self)->&[u8]{self.token.read().wire}
}
/// Connected UDP is solely a real-kernel unprivileged fixture: a copy-complete
/// send never indicates delivery, authenticated origin or a peer receipt.
pub struct ScopedUdpOwner {
    generation:u32,
    sender:UdpSocket,
    receiver:UdpSocket,
    fence:Arc<BorrowFence>,
}
impl ScopedUdpOwner {
    pub fn new(generation:u32,sender:UdpSocket,receiver:UdpSocket)->io::Result<Self>{
        if generation==0 {
            return Err(io::Error::new(io::ErrorKind::InvalidInput,"zero generation"));
        }
        sender.peer_addr()?;
        receiver.local_addr()?;
        Ok(Self{generation,sender,receiver,fence:Arc::new(BorrowFence::default())})
    }
    pub fn generation(&self)->u32{self.generation}
    pub fn outstanding(&self)->usize{self.fence.outstanding()}
    pub fn is_stopping(&self)->bool{self.fence.is_stopping()}
    pub fn begin_stop(&self){self.fence.begin_stop()}
    pub fn wait_drained_until(&self,deadline:Instant)->StopResult{
        self.fence.wait_drained_until(deadline)
    }
    fn check(&self,caller:u32)->Result<(),LeaseGateError>{
        if caller!=self.generation{return Err(LeaseGateError::StaleGeneration)}
        if self.fence.is_stopping(){return Err(LeaseGateError::Stopping)}
        Ok(())
    }
    /// Exactly one existing bounded sendmmsg call; retained frozen handles
    /// are borrowed, never resealed/copied/cloned. Accepted is only kernel
    /// copied, an uncertain index must NOT be automatically replayed.
    pub fn submit<H:FrozenRecordHandle>(
        &self,caller:u32,frames:&[H]
    )->Result<BatchResult,LeaseGateError>{
        self.check(caller)?;
        let outcome=submit_connected_udp(&self.sender,frames,&self.fence);
        BatchResult::new(outcome,frames.len())
            .map_err(LeaseGateError::InvalidOutcome)
    }
    /// Exactly one existing bounded recvmmsg, writes solely into caller-owned
    /// independent mutable slots; truncation does not authorize parsing.
    pub fn receive(&self,caller:u32,buffers:&mut [&mut [u8]])
        ->Result<RxBatchOutcome,LeaseGateError>
    {
        self.check(caller)?;
        Ok(receive_ready_udp(&self.receiver,buffers,&self.fence))
    }

    /// The receipt is tied to the exact live owner, not merely a reusable
    /// numeric generation. It is a scope check for caller-owned UDP bytes,
    /// NEVER an authentication/PN/admission token. It borrows the old owner
    /// across rotation so an address-reuse ABA cannot pass pointer identity.
    pub fn receive_tagged<'a>(&'a self,caller:u32,buffers:&mut [&mut [u8]])
        ->Result<ScopedRxReceipt<'a>,LeaseGateError>
    {
        let outcome=self.receive(caller,buffers)?;
        Ok(ScopedRxReceipt{origin:self,outcome})
    }
    /// Explicit deferred backend token (not used for synchronous UDP copy).
    /// On acquisition failure return the **original** record, not a clone.
    pub fn register_delayed<H:FrozenRecordHandle>(
        &self,caller:u32,record:H
    )->Result<GenerationLoan<H>,(LeaseGateError,H)>{
        if let Err(e)=self.check(caller){return Err((e,record))}
        self.fence.try_loan(record).map(|token|
            GenerationLoan{generation:self.generation,token}
        ).map_err(|(e,record)|(match e{
            BorrowError::Stopping=>LeaseGateError::Stopping,
            BorrowError::TooManyLoans=>LeaseGateError::TooManyLoans,
        },record))
    }
    /// Mismatched new generation MUST hand back the exact old token, never
    /// consume/free it. The original owner's real completion/cancel path
    /// eventually releases it after the driver is no longer using bytes.
    pub fn complete_delayed<H:FrozenRecordHandle>(
        &self,loan:GenerationLoan<H>
    )->Result<(),GenerationLoan<H>>{
        if loan.generation!=self.generation{return Err(loan)}
        drop(loan);
        Ok(())
    }
}


/// A synchronous, unauthenticated UDP RX result bound to one live owner.
/// The caller still owns and must retain the original RX buffers while
/// inspecting them. This does not authenticate a lane, consume PN, or grant
/// permission to pass ciphertext into a trusted Go V4 admission path.
pub struct ScopedRxReceipt<'a>{
    origin:&'a ScopedUdpOwner,
    outcome:RxBatchOutcome,
}
impl ScopedRxReceipt<'_>{
    pub fn outcome(&self)->RxBatchOutcome{self.outcome}
    /// A retired/stopped receipt is never dispatchable, even if a new owner
    /// uses the same numeric generation. No payload is copied by this gate.
    pub fn entry_for(&self,owner:&ScopedUdpOwner,index:usize)
        ->Result<Option<RxEntry>,LeaseGateError>
    {
        if !std::ptr::eq(self.origin,owner){
            return Err(LeaseGateError::StaleGeneration);
        }
        owner.check(owner.generation)?;
        Ok(self.outcome.entry(index))
    }
}

#[cfg(test)]
mod tests{
    use super::*;
    use crate::linux_rx_batch::{RxEntry,RxStatus,ParseGateError,parse_complete};
    use crate::ipv4_tcp::{Ipv4Tuple,PacketPersona};
    use crate::rx_ipv4_tcp::TrustedRx;
    use crate::{TxDisposition,TxError};
    use std::sync::{Weak,mpsc};
    use std::thread;
    use std::time::{Duration,Instant};
    use wbd_types::buffer_contract::{BufferOrigin,FrozenMetadata};
    use wbd_types::{BufferKey,LaneKey,RecordPn,SeqOffset,TunnelKey};
    #[derive(Clone)]
    struct Frozen { wire:Arc<[u8]>,meta:FrozenMetadata }
    impl FrozenRecordHandle for Frozen {
        fn origin(&self)->BufferOrigin{
            BufferOrigin{owner_arena:9,key:BufferKey{slot:1,generation:9}}
        }
        fn metadata(&self)->FrozenMetadata{self.meta}
        fn bytes(&self)->&[u8]{&self.wire}
    }
    fn frozen(bytes:&[u8],n:u64)->Frozen{
        Frozen{wire:Arc::from(bytes),meta:FrozenMetadata{
            lane:LaneKey{tunnel:TunnelKey{slot:8,generation:1},slot:3,generation:1},
            seq:SeqOffset(n*4),pn:RecordPn(n),carrier_snapshot:7,
        }}
    }
    fn pair(generation:u32)->ScopedUdpOwner{
        let rx=UdpSocket::bind("127.0.0.1:0").unwrap();
        let tx=UdpSocket::bind("127.0.0.1:0").unwrap();
        tx.connect(rx.local_addr().unwrap()).unwrap();
        ScopedUdpOwner::new(generation,tx,rx).unwrap()
    }
    fn trusted()->TrustedRx<'static>{
        TrustedRx{tuple:Ipv4Tuple{src_ip:&[192,0,2,40],dst_ip:&[198,51,100,40],
                src_port:43000,dst_port:443},
            persona:PacketPersona::Legacy,mtu:1500,
            authenticated_options:None}
    }
    fn golden()->[u8;46]{
        let s="4500002e0015400040064e31c0000228c6336428a7f801bb00000064000000c850180400cc2900007265636f7264";
        std::array::from_fn(|i|u8::from_str_radix(&s[i*2..i*2+2],16).unwrap())
    }

    #[test]
    fn r1_driver_lease_actual_udp_0_1_32_33_prefix_suffix_and_rx(){
        for n in [0,1,32,33usize] {
            let o=pair(7);
            let fs:Vec<_>=(0..n).map(|i|frozen(&[i as u8,0xbe],i as u64)).collect();
            let before:Vec<_>=fs.iter().map(|f|Arc::as_ptr(&f.wire)).collect();
            let out=o.submit(7,&fs).unwrap();
            let accepted=n.min(32);
            assert_eq!(out.accepted_prefix(),accepted);
            assert_eq!(out.len(),n);
            assert_eq!(out.uncertain_index(),None);
            for i in 0..n{
                assert_eq!(out.disposition_at(i),Some(if i<32{
                    TxDisposition::Accepted
                }else{TxDisposition::NotAttempted}));
                assert_eq!(Arc::as_ptr(&fs[i].wire),before[i]);
            }
            if n==33{assert_eq!(out.error(),Some(TxError::WouldBlock));}
            else{assert_eq!(out.error(),None);}
            let mut bytes=[[0xa5u8;16];33];
            let mut slots:[&mut [u8];33]=bytes.each_mut().map(|x|x.as_mut_slice());
            let got=o.receive(7,&mut slots[..n]).unwrap();
            assert_eq!(got.attempted,accepted);
            assert_eq!(got.received,accepted);
            for i in 0..accepted{
                assert_eq!(got.entry(i),Some(RxEntry::Complete{len:2}));
                assert_eq!(&slots[i][..2],&[i as u8,0xbe]);
            }
            if n==0{assert_eq!(got.status,RxStatus::Empty)}
            else if n==33{assert_eq!(got.status,RxStatus::AtCap)}
            else{assert_eq!(got.status,RxStatus::Ready)}
            assert_eq!(got.entry(32),None);
            assert!(bytes[32].iter().all(|&b|b==0xa5));
            if n==33{
                let f=out.disposition_at(32).unwrap();
                assert_eq!(f,TxDisposition::NotAttempted);
                let next=o.submit(7,&fs[32..]).unwrap();
                assert_eq!(next.accepted_prefix(),1);
                let mut b=[0u8;16];let mut one=[b.as_mut_slice()];
                let last=o.receive(7,&mut one).unwrap();
                assert_eq!(last.entry(0),Some(RxEntry::Complete{len:2}));
                assert_eq!(&b[..2],&[32,0xbe]);
            }
            assert_eq!(o.outstanding(),0);
        }
    }
    #[test]
    fn r1_driver_lease_actual_udp_partial_prefix_oversized_and_unsent_suffix(){
        let o=pair(9);
        // IPv4 UDP payload max is 65507; the second is definitely EMSGSIZE.
        let huge=[0xccu8;65508];
        let fs=[frozen(b"first",1),frozen(&huge,2),frozen(b"never-sent",3)];
        let result=o.submit(9,&fs).unwrap();
        assert_eq!(result.accepted_prefix(),1);
        assert_eq!(result.uncertain_index(),None);
        assert_eq!(result.error(),Some(TxError::IoFailed));
        assert_eq!(result.iter().collect::<Vec<_>>(),
            vec![TxDisposition::Accepted,TxDisposition::NotAttempted,TxDisposition::NotAttempted]);
        let mut slots=[[0xa5u8;64];3];
        let mut bufs:[&mut [u8];3]=slots.each_mut().map(|b|b.as_mut_slice());
        let recv=o.receive(9,&mut bufs).unwrap();
        assert_eq!(recv.received,1);
        assert_eq!(recv.entry(0),Some(RxEntry::Complete{len:5}));
        assert_eq!(&bufs[0][..5],b"first");
        assert_eq!(recv.entry(1),Some(RxEntry::Unused));
        assert!(slots[2].iter().all(|&b|b==0xa5));
    }
    #[test]
    fn r1_driver_lease_actual_udp_rx_truncation_no_parse_and_nonhol(){
        let o=pair(9);
        let bad=[0x45u8;200];
        let valid=golden();
        let frames=[frozen(&bad,1),frozen(&valid,2)];
        assert_eq!(o.submit(9,&frames).unwrap().accepted_prefix(),2);
        let mut little=[0xaau8;8];let mut full=[0xaau8;128];
        let mut bufs=[little.as_mut_slice(),full.as_mut_slice()];
        let out=o.receive(9,&mut bufs).unwrap();
        assert_eq!(out.received,2);
        assert_eq!(out.entry(0),Some(RxEntry::Truncated{wire_len:200,capacity:8}));
        assert_eq!(parse_complete(out.entries[0],&little,trusted()),Err(ParseGateError::Truncated));
        assert_eq!(out.entry(1),Some(RxEntry::Complete{len:46}));
        let p=parse_complete(out.entries[1],&full,trusted()).unwrap();
        assert_eq!(p.ciphertext,b"record"); // UNAUTHENTICATED, not PN receipt
    }
    #[test]
    fn r1_driver_lease_actual_udp_wouldblock_invalid_slot_no_consume_stop(){
        let o=pair(6);
        let mut out=[0xaau8;64];let mut slots=[out.as_mut_slice()];
        assert_eq!(o.receive(6,&mut slots).unwrap().status,RxStatus::WouldBlock);
        assert_eq!(out,[0xaa;64]);
        let f=[frozen(b"still-pending",1)];
        assert_eq!(o.submit(6,&f).unwrap().accepted_prefix(),1);
        let mut empty:[u8;0]=[];let mut full=[0x55u8;64];
        let mut invalid=[empty.as_mut_slice(),full.as_mut_slice()];
        assert_eq!(o.receive(6,&mut invalid).unwrap().status,RxStatus::InvalidBuffers);
        let mut valid=[full.as_mut_slice()];
        let ready=o.receive(6,&mut valid).unwrap();
        assert_eq!(ready.entry(0),Some(RxEntry::Complete{len:13}));
        assert_eq!(&full[..13],b"still-pending");
        assert_eq!(o.outstanding(),0);
        o.begin_stop();o.begin_stop();
        assert_eq!(o.wait_drained_until(Instant::now()),StopResult::Drained);
        assert_eq!(o.submit(6,&f).err(),Some(LeaseGateError::Stopping));
        let mut one=[0x99u8;64];let mut bufs=[one.as_mut_slice()];
        assert_eq!(o.receive(6,&mut bufs).err(),Some(LeaseGateError::Stopping));
        assert_eq!(one,[0x99;64]);
    }
    #[test]
    fn r1_driver_lease_delayed_generation_rejected_late_no_free_after_stop(){
        let old=pair(41);let new=pair(42);
        let f=frozen(b"frozen-ciphertext",7);
        let weak:Weak<[u8]>=Arc::downgrade(&f.wire);
        let token=old.register_delayed(41,f).ok().unwrap();
        assert_eq!(token.bytes(),b"frozen-ciphertext");
        assert_eq!(old.outstanding(),1);
        old.begin_stop();old.begin_stop();
        assert_eq!(old.wait_drained_until(Instant::now()),
            StopResult::Pending{outstanding:1});
        assert!(weak.upgrade().is_some());
        let returned=new.complete_delayed(token).err().expect("wrong owner MUST return token");
        assert_eq!(returned.generation(),41);
        assert!(weak.upgrade().is_some());
        assert_eq!(old.outstanding(),1);
        let reject=frozen(b"fresh old denied",8);
        assert!(matches!(old.register_delayed(41,reject),Err((LeaseGateError::Stopping,_))));
        assert_eq!(old.submit(41,&[frozen(b"old denied",9)]).err(),
            Some(LeaseGateError::Stopping));
        assert_eq!(new.submit(42,&[frozen(b"new fresh",10)]).unwrap().accepted_prefix(),1);
        let mut buf=[0u8;64];let mut slots=[buf.as_mut_slice()];
        assert_eq!(new.receive(42,&mut slots).unwrap().entry(0),
            Some(RxEntry::Complete{len:9}));
        assert_eq!(&buf[..9],b"new fresh");
        assert_eq!(old.register_delayed(42,frozen(b"wrong generation",11)).err().map(|z|z.0),
            Some(LeaseGateError::StaleGeneration));
        old.complete_delayed(returned).ok().unwrap();
        assert!(weak.upgrade().is_none());
        assert_eq!(old.wait_drained_until(Instant::now()),StopResult::Drained);
        assert_eq!(new.outstanding(),0);
    }
    #[test]
    fn r1_driver_lease_waiter_delayed_completion_two_generation_isolation(){
        let old=Arc::new(pair(77));
        let new=pair(78);
        let token=old.register_delayed(77,frozen(b"held",1)).ok().unwrap();
        let (tx,rx)=mpsc::channel();
        let waiter=Arc::clone(&old);
        let t=thread::spawn(move||{
            tx.send(waiter.wait_drained_until(Instant::now()+Duration::from_secs(2))).unwrap();
        });
        assert_eq!(old.wait_drained_until(Instant::now()),StopResult::Pending{outstanding:1});
        assert_eq!(new.submit(78,&[frozen(b"ready",2)]).unwrap().accepted_prefix(),1);
        assert_eq!(old.outstanding(),1);
        let token=new.complete_delayed(token).err().expect("wrong owner returns old token");
        assert_eq!(old.outstanding(),1);
        old.complete_delayed(token).ok().unwrap(); // only after simulated completion
        assert_eq!(rx.recv_timeout(Duration::from_secs(2)).unwrap(),StopResult::Drained);
        t.join().unwrap();
        assert_eq!(new.outstanding(),0);
    }
    #[test]
    fn r1_driver_lease_eintr_uncertain_wouldblock_replay_policy_pure(){
        // Native EINTR injection is not claimed; existing native sendmmsg
        // and recvmmsg classifier tests cover exact deterministic branches.
        // Here only the public outcome mapping is asserted, never a kernel EINTR.
        let interrupted=BatchResult::new(crate::TxBatchOutcome{
            accepted_prefix:0,uncertain_index:Some(0),error:Some(TxError::IoUncertain)},3).unwrap();
        assert_eq!(interrupted.iter().collect::<Vec<_>>(),
            vec![TxDisposition::Uncertain,TxDisposition::NotAttempted,TxDisposition::NotAttempted]);
        let retry=BatchResult::new(crate::TxBatchOutcome{
            accepted_prefix:0,uncertain_index:None,error:Some(TxError::WouldBlock)},3).unwrap();
        assert_eq!(retry.iter().collect::<Vec<_>>(),
            vec![TxDisposition::NotAttempted;3]);
        let o=pair(1);
        assert_eq!(o.register_delayed(0,frozen(b"denied",2)).err().map(|e|e.0),
            Some(LeaseGateError::StaleGeneration));
    }

    #[test]
    fn r1_udp_rx_real_33rd_overflow_repeated_bursts_preallocated_no_starvation(){
        let o=pair(101);
        // Each 33rd packet is actually queued by the kernel, unlike a
        // 33rd sendmmsg suffix. One recvmmsg may touch only the first 32
        // preallocated slots; a second syscall must service the overflow.
        for round in 0..24usize {
            let frames:Vec<_>=(0..33usize).map(|i|
                frozen(&[round as u8,i as u8,0x5a],(round*33+i) as u64)
            ).collect();
            let first=o.submit(101,&frames[..32]).unwrap();
            assert_eq!(first.accepted_prefix(),32);
            assert_eq!(first.uncertain_index(),None);
            assert_eq!(o.submit(101,&frames[32..]).unwrap().accepted_prefix(),1);
            let mut storage=[[0xa5u8;8];33];
            let ptrs:[*mut u8;33]=std::array::from_fn(|i|storage[i].as_mut_ptr());
            let mut views:[&mut [u8];33]=storage.each_mut().map(|b|b.as_mut_slice());
            let receipt=o.receive_tagged(101,&mut views).unwrap();
            let result=receipt.outcome();
            assert_eq!(result.requested,33);
            assert_eq!(result.attempted,32);
            assert_eq!(result.received,32);
            assert_eq!(result.status,RxStatus::AtCap);
            for i in 0..32{
                assert_eq!(receipt.entry_for(&o,i).unwrap(),Some(RxEntry::Complete{len:3}));
                assert_eq!(&views[i][..3],&[round as u8,i as u8,0x5a]);
                assert_eq!(views[i].as_mut_ptr(),ptrs[i]);
            }
            assert_eq!(receipt.entry_for(&o,32).unwrap(),None);
            assert_eq!(views[32],[0xa5;8]);
            assert_eq!(views[32].as_mut_ptr(),ptrs[32]);
            drop(receipt);
            let overflow=o.receive_tagged(101,&mut views[32..]).unwrap();
            assert_eq!(overflow.outcome().received,1);
            assert_eq!(overflow.entry_for(&o,0).unwrap(),Some(RxEntry::Complete{len:3}));
            assert_eq!(&views[32][..3],&[round as u8,32,0x5a]);
            drop(overflow);
            let no_more=o.receive(101,&mut views[..1]).unwrap();
            assert_eq!(no_more.status,RxStatus::WouldBlock);
            assert_eq!(o.outstanding(),0);
        }
    }

    #[test]
    fn r1_udp_rx_real_truncation_then_late_arrival_and_empty_not_promoted(){
        let o=pair(202);
        let oversized=[0x45u8;96];
        assert_eq!(o.sender.send(&oversized).unwrap(),96);
        assert_eq!(o.sender.send(b"complete").unwrap(),8);
        let mut tiny=[0xa5u8;7];
        let mut whole=[0xa5u8;32];
        let mut slots=[tiny.as_mut_slice(),whole.as_mut_slice()];
        let receipt=o.receive_tagged(202,&mut slots).unwrap();
        assert_eq!(receipt.outcome().received,2);
        assert_eq!(receipt.entry_for(&o,0).unwrap(),
            Some(RxEntry::Truncated{wire_len:96,capacity:7}));
        assert_eq!(receipt.entry_for(&o,1).unwrap(),Some(RxEntry::Complete{len:8}));
        assert_eq!(parse_complete(receipt.outcome().entries[0],slots[0],trusted()),
            Err(ParseGateError::Truncated));
        assert_eq!(&slots[1][..8],b"complete");
        drop(receipt);
        let empty=o.receive(202,&mut slots).unwrap();
        assert_eq!(empty.status,RxStatus::WouldBlock);
        assert_eq!(empty.received,0);
        assert_eq!(o.sender.send(b"late").unwrap(),4);
        let late=o.receive_tagged(202,&mut slots[..1]).unwrap();
        assert_eq!(late.entry_for(&o,0).unwrap(),Some(RxEntry::Complete{len:4}));
        assert_eq!(&tiny[..4],b"late");
    }

    #[test]
    fn r1_udp_rx_stopped_old_borrowed_receipt_cannot_dispatch_to_rotated_owner(){
        let old=pair(303);
        let fresh=pair(304);
        let record=frozen(b"frozen-while-old-rx-retained",51);
        let original_pn=record.meta.pn;
        let weak:Weak<[u8]>=Arc::downgrade(&record.wire);
        let old_loan=old.register_delayed(303,record).ok().unwrap();
        assert_eq!(old.outstanding(),1);
        assert_eq!(old.sender.send(b"old-rx").unwrap(),6);
        let mut old_storage=[0xa5u8;32];
        let mut old_slots=[old_storage.as_mut_slice()];
        let old_receipt=old.receive_tagged(303,&mut old_slots).unwrap();
        assert_eq!(old_receipt.entry_for(&old,0).unwrap(),Some(RxEntry::Complete{len:6}));
        assert_eq!(&old_storage[..6],b"old-rx");
        old.begin_stop();
        old.begin_stop();
        assert_eq!(old.wait_drained_until(Instant::now()),StopResult::Pending{outstanding:1});
        assert_eq!(old_receipt.entry_for(&old,0),Err(LeaseGateError::Stopping));
        assert_eq!(old_receipt.entry_for(&fresh,0),Err(LeaseGateError::StaleGeneration));
        assert_eq!(old_loan.token.read().metadata.pn,original_pn);
        assert!(weak.upgrade().is_some());
        // A late UDP arrival on the retired socket is NOT an authorized RX.
        assert_eq!(old.sender.send(b"late-old").unwrap(),8);
        let mut denied=[0x77u8;32];
        let mut denied_slots=[denied.as_mut_slice()];
        assert_eq!(old.receive(303,&mut denied_slots).err(),Some(LeaseGateError::Stopping));
        assert_eq!(denied,[0x77;32]);
        let mut fresh_storage=[0xa5u8;32];
        let mut fresh_slots=[fresh_storage.as_mut_slice()];
        assert_eq!(fresh.receive(304,&mut fresh_slots).unwrap().status,RxStatus::WouldBlock);
        assert_eq!(fresh.sender.send(b"fresh-rx").unwrap(),8);
        let new_receipt=fresh.receive_tagged(304,&mut fresh_slots).unwrap();
        assert_eq!(new_receipt.entry_for(&fresh,0).unwrap(),Some(RxEntry::Complete{len:8}));
        assert_eq!(&fresh_storage[..8],b"fresh-rx");
        assert_eq!(new_receipt.entry_for(&old,0),Err(LeaseGateError::StaleGeneration));
        let returned=fresh.complete_delayed(old_loan).err().expect("old token must survive");
        assert_eq!(old.outstanding(),1);
        assert!(weak.upgrade().is_some());
        old.complete_delayed(returned).ok().unwrap();
        assert!(weak.upgrade().is_none());
        assert_eq!(old.wait_drained_until(Instant::now()),StopResult::Drained);
        assert_eq!(fresh.outstanding(),0);
    }

    #[test]
    fn r1_udp_rx_scope_identity_rejects_equal_numeric_generation_across_contexts(){
        let a=pair(505);
        let b=pair(505);
        assert_eq!(a.sender.send(b"from-a").unwrap(),6);
        assert_eq!(b.sender.send(b"from-b").unwrap(),6);
        let mut ab=[0u8;16];let mut bb=[0u8;16];
        let mut av=[ab.as_mut_slice()];let mut bv=[bb.as_mut_slice()];
        let ar=a.receive_tagged(505,&mut av).unwrap();
        let br=b.receive_tagged(505,&mut bv).unwrap();
        assert_eq!(ar.entry_for(&b,0),Err(LeaseGateError::StaleGeneration));
        assert_eq!(br.entry_for(&a,0),Err(LeaseGateError::StaleGeneration));
        assert_eq!(ar.entry_for(&a,0).unwrap(),Some(RxEntry::Complete{len:6}));
        assert_eq!(br.entry_for(&b,0).unwrap(),Some(RxEntry::Complete{len:6}));
        assert_eq!(&ab[..6],b"from-a");
        assert_eq!(&bb[..6],b"from-b");
        // RX is metadata for unauthenticated bytes only; there is no Go
        // admission, PN allocator, or authenticated lane in this API.
    }

}
