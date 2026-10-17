//! M1-012: independently owned TX/RX single-producer endpoints.
//! A safe bounded std-channel compatibility implementation until M0 pins
//! rtrb in the shared Cargo/lock; this is NOT an rtrb/SPSC performance PASS.
//! No per-item Arc, ciphertext copy, shared direction mutex, or crypto.
#![forbid(unsafe_code)]
use std::{ops::Range,sync::{Arc,atomic::{AtomicBool,Ordering::SeqCst}}};
use wbd_types::{LaneKey,MonoNs};
use wbd_types::buffer_contract::FrozenRecordHandle;
use crate::memory::{FrozenRecord,UniqueBuffer};
use super::{TxKind,wake::{self,OwnerProducer,OwnerConsumer,PushError,WakeEvent}};

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum Direction {Tx,Rx}
struct Epoch {owner_id:u64,serial:u32,lane:LaneKey,stopping:AtomicBool}
/// Arc is cloned on the CONTROL path only. No per-packet Arc scope tag.
#[derive(Clone)]
pub struct DirectionToken(Arc<Epoch>);
impl DirectionToken {
    pub fn owner_id(&self)->u64{self.0.owner_id}
    pub fn serial(&self)->u32{self.0.serial}
    pub fn lane(&self)->LaneKey{self.0.lane}
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum DirectionError { Stale, Stopped, WrongLane, Full, Disconnected }
#[derive(Debug)]
pub struct TxIngress {
    pub kind:TxKind,pub record:FrozenRecord,
    pub offered_at:MonoNs,pub eligible_at:MonoNs,
}
#[derive(Debug)]
pub struct RxIngress {
    pub buffer:UniqueBuffer,pub wire:Range<usize>,
    pub lane_hint:Option<LaneKey>,pub offered_at:MonoNs,
}
pub struct DirectionProducer<T> {
    writer:OwnerProducer<T>,epoch:Arc<Epoch>,direction:Direction,
}
pub struct DirectionConsumer<T> {
    reader:OwnerConsumer<T>,epoch:Arc<Epoch>,direction:Direction,
    canceled:usize,
}
impl<T> DirectionProducer<T> {
    pub fn token(&self)->DirectionToken{DirectionToken(Arc::clone(&self.epoch))}
    pub fn direction(&self)->Direction{self.direction}
    /// Source identity is not credential authority: only protected M0
    /// admission can decide which control-plane lane may hold this token.
    fn check(&self,token:&DirectionToken)->Result<(),DirectionError>{
        if !Arc::ptr_eq(&self.epoch,&token.0){return Err(DirectionError::Stale);}
        if self.epoch.stopping.load(SeqCst){return Err(DirectionError::Stopped);}
        Ok(())
    }
    pub fn try_publish(&self,token:&DirectionToken,item:T)
        ->Result<(),(DirectionError,T)>{
        if let Err(e)=self.check(token){return Err((e,item));}
        self.writer.try_push(item).map_err(|e|match e{
            PushError::Full(item)=>(DirectionError::Full,item),
            PushError::Stopping(item)=>(DirectionError::Stopped,item),
            PushError::Disconnected(item)=>(DirectionError::Disconnected,item),
        })
    }
    pub fn stop(&self){
        self.epoch.stopping.store(true,SeqCst);
        self.writer.stop();
    }
}
impl<T> DirectionConsumer<T> {
    pub fn token(&self)->DirectionToken{DirectionToken(Arc::clone(&self.epoch))}
    pub fn direction(&self)->Direction{self.direction}
    pub fn check_current(&self,token:&DirectionToken)->Result<(),DirectionError>{
        if !Arc::ptr_eq(&self.epoch,&token.0){return Err(DirectionError::Stale);}
        if self.epoch.stopping.load(SeqCst){return Err(DirectionError::Stopped);}
        Ok(())
    }
    /// Already-enqueued items ONLY. At most 32 / caller available Vec slots;
    /// no data waits for batch fill, nor allocations inside this drain.
    /// The caller owns every yielded handle until true driver completion.
    pub fn drain_ready(&mut self,storage:&mut Vec<T>)->usize{
        if self.epoch.stopping.load(SeqCst){return 0;}
        let mut delivered=0;
        let capacity=32usize.min(storage.capacity().saturating_sub(storage.len()));
        while delivered<capacity {
            match self.reader.try_take() {
                Some(WakeEvent::Ready(_,item)) => {
                    // Stop can race this check, but the caller MUST call
                    // check_current before its irreversible driver syscall.
                    if self.epoch.stopping.load(SeqCst){
                        drop(item);break;
                    }
                    storage.push(item);delivered+=1;
                }
                _=>break,
            }
        }
        delivered
    }
    /// Underlying armed+double-inspect+OS thread park, one consumer thread.
    /// Wakeup is a hint. This does NOT dispatch ciphertext to a driver.
    pub fn wait_input<C,R>(&mut self,now:C,deadline:Option<MonoNs>,returns:R)
        ->WakeEvent<T>
    where C:Fn()->MonoNs,R:FnMut()->bool{
        self.reader.wait(now,deadline,returns)
    }
    /// Stop cancels queued but not externally dispatched handles; never
    /// reports driver quiescence. Repeat to drain a pre-stop inflight writer.
    pub fn stop(&mut self)->(usize,usize) {
        self.epoch.stopping.store(true,SeqCst);
        let (new,inflight)=self.reader.stop_cancel_queued();
        self.canceled=self.canceled.saturating_add(new);
        (self.canceled,inflight)
    }
}
fn pair<T>(direction:Direction,owner_id:u64,serial:u32,lane:LaneKey,
    capacity:usize)->Option<(DirectionProducer<T>,DirectionConsumer<T>)>{
    if owner_id==0||serial==0||lane.generation==0||
        lane.tunnel.generation==0{return None;}
    let (writer,reader)=wake::single(capacity)?;
    let epoch=Arc::new(Epoch{owner_id,serial,lane,stopping:AtomicBool::new(false)});
    Some((
        DirectionProducer{writer,epoch:Arc::clone(&epoch),direction},
        DirectionConsumer{reader,epoch,direction,canceled:0},
    ))
}
pub fn split_tx(owner_id:u64,serial:u32,lane:LaneKey,capacity:usize)
    ->Option<(DirectionProducer<TxIngress>,DirectionConsumer<TxIngress>)>{
    pair(Direction::Tx,owner_id,serial,lane,capacity)
}
pub fn split_rx(owner_id:u64,serial:u32,lane:LaneKey,capacity:usize)
    ->Option<(DirectionProducer<RxIngress>,DirectionConsumer<RxIngress>)>{
    pair(Direction::Rx,owner_id,serial,lane,capacity)
}
impl DirectionProducer<TxIngress>{
    /// Reject a mismatched frozen metadata lane without moving its payload.
    pub fn publish_tx(&self,token:&DirectionToken,item:TxIngress)
        ->Result<(),(DirectionError,TxIngress)>{
        if item.record.metadata().lane!=self.epoch.lane{
            return Err((DirectionError::WrongLane,item));
        }
        self.try_publish(token,item)
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    use crate::memory::Arena;
    use wbd_types::{TunnelKey,RecordPn,SeqOffset};
    use wbd_types::buffer_contract::{UniqueSealable,FrozenMetadata};
    fn lane(gen:u32)->LaneKey{
        LaneKey{tunnel:TunnelKey{slot:900,generation:gen},slot:1,generation:gen}
    }
    fn arena()->Arena{Arena::new(223,128,256,1,100000).unwrap()}
    fn frozen(a:&mut Arena,b:u8,gen:u32)->FrozenRecord{
        let mut unique=a.allocate().unwrap();unique.writable()[0]=b;
        unique.freeze(0..1,FrozenMetadata{
            lane:lane(gen),pn:RecordPn(b as u64),seq:SeqOffset(b as u64),
            carrier_snapshot:1
        }).unwrap()
    }
    fn tx_item(a:&mut Arena,b:u8,gen:u32)->TxIngress{
        TxIngress{kind:TxKind::Fresh,record:frozen(a,b,gen),
            offered_at:MonoNs(0),eligible_at:MonoNs(0)}
    }
    fn rx_item(a:&mut Arena,b:u8)->RxIngress{
        let mut unique=a.allocate().unwrap();unique.writable()[0]=b;
        RxIngress{buffer:unique,wire:0..1,lane_hint:None,offered_at:MonoNs(0)}
    }
    #[test]
    fn r1_direction_tx_r01_zero_one_32_33_ready_only_owned_prealloc(){
        let mut a=arena();let (producer,mut consumer)=split_tx(2,1,lane(1),64).unwrap();
        let token=producer.token();let mut out=Vec::with_capacity(64);
        let ptr=out.as_ptr();
        assert_eq!(consumer.drain_ready(&mut out),0);
        producer.publish_tx(&token,tx_item(&mut a,7,1)).unwrap();
        assert_eq!(consumer.drain_ready(&mut out),1);
        assert_eq!(out[0].record.bytes(),&[7]);
        out.clear();
        for i in 0..33u8{
            producer.publish_tx(&token,tx_item(&mut a,i,1)).unwrap();
        }
        assert_eq!(consumer.drain_ready(&mut out),32);
        assert_eq!(consumer.drain_ready(&mut out),1);
        assert_eq!(out.len(),33);
        assert_eq!(out[32].record.bytes(),&[32]);
        assert_eq!(out.as_ptr(),ptr);
        drop(out);assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_direction_rx_r01_spsc_full_returns_unique_original(){
        let mut a=arena();let (producer,mut consumer)=split_rx(2,1,lane(1),1).unwrap();
        let token=producer.token();
        let b=rx_item(&mut a,1);producer.try_publish(&token,b).unwrap();
        let b=rx_item(&mut a,2);
        let original=b.buffer.origin();
        let fail=producer.try_publish(&token,b);
        assert!(matches!(fail,Err((DirectionError::Full,_))));
        let b=fail.err().unwrap().1;
        assert_eq!(b.buffer.origin(),original);
        assert_eq!(a.report().loaned,2);
        drop(b);
        let mut out=Vec::with_capacity(1);
        assert_eq!(consumer.drain_ready(&mut out),1);
        assert_eq!(out[0].buffer.writable()[0],1);
        drop(out);assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_direction_split_tx_rx_two_threads_without_shared_mutable_owner(){
        let mut a=arena();
        let(txp,mut txc)=split_tx(5,1,lane(1),2).unwrap();
        let(rxp,mut rxc)=split_rx(5,1,lane(1),2).unwrap();
        assert_eq!((txc.direction(),rxc.direction()),(Direction::Tx,Direction::Rx));
        let tx_token=txp.token();let rx_token=rxp.token();
        let item=tx_item(&mut a,10,1);let item2=rx_item(&mut a,11);
        let publish=std::thread::spawn(move||{
            txp.publish_tx(&tx_token,item).unwrap();
            rxp.try_publish(&rx_token,item2).unwrap();
        });
        let tx_thread=std::thread::spawn(move||{
            let event=txc.wait_input(||MonoNs(0),None,||false);
            match event{
                WakeEvent::Ready(_,item)=>{assert_eq!(item.record.bytes(),&[10]);}
                _=>panic!("expected TX after sparse wait")
            }
        });
        let rx_thread=std::thread::spawn(move||{
            let event=rxc.wait_input(||MonoNs(0),None,||false);
            match event{
                WakeEvent::Ready(_,mut item)=>{assert_eq!(item.buffer.writable()[0],11);}
                _=>panic!("expected RX after sparse wait")
            }
        });
        publish.join().unwrap();tx_thread.join().unwrap();rx_thread.join().unwrap();
        assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_direction_b04_stop_old_loan_not_released_new_first_no_aba(){
        let mut a=arena();
        let(old_p,mut old_c)=split_tx(7,1,lane(1),2).unwrap();
        let t=old_p.token();
        old_p.publish_tx(&t,tx_item(&mut a,1,1)).unwrap();
        old_p.publish_tx(&t,tx_item(&mut a,2,1)).unwrap();
        let mut handed=Vec::with_capacity(1);
        assert_eq!(old_c.drain_ready(&mut handed),1);
        let ptr=handed[0].record.bytes().as_ptr();
        let (canceled,inflight)=old_c.stop();
        assert_eq!((canceled,inflight),(1,0));
        assert_eq!(old_c.stop(),(1,0));
        assert_eq!(a.report().loaned,1);
        let rejected=old_p.publish_tx(&t,tx_item(&mut a,3,1));
        assert!(matches!(rejected,Err((DirectionError::Stopped,_))));
        drop(rejected);
        let(new_p,mut new_c)=split_tx(7,1,lane(1),2).unwrap();
        let fresh_t=new_p.token();
        assert_eq!(new_p.publish_tx(&t,tx_item(&mut a,4,1))
            .err().unwrap().0,DirectionError::Stale);
        new_p.publish_tx(&fresh_t,tx_item(&mut a,5,1)).unwrap();
        let mut out=Vec::with_capacity(2);
        assert_eq!(new_c.drain_ready(&mut out),1);
        assert_eq!(out[0].record.bytes(),&[5]);
        assert_eq!(handed[0].record.bytes().as_ptr(),ptr);
        assert_eq!(a.report().loaned,2);
        let j=std::thread::spawn(move||drop(handed));
        j.join().unwrap();
        assert_eq!(a.report().loaned,1);
        drop(out);assert_eq!(a.report().loaned,0);
    }
    #[test]
    fn r1_direction_g01_old_rx_lane_not_block_new_direction_ingress(){
        let mut a=arena();
        let(old_p,mut old_c)=split_rx(7,1,lane(1),32).unwrap();
        let old=old_p.token();
        for i in 0..32u8{old_p.try_publish(&old,rx_item(&mut a,i)).unwrap();}
        let mut old_out=Vec::with_capacity(32);
        assert_eq!(old_c.drain_ready(&mut old_out),32);
        assert_eq!(old_c.stop(),(0,0));
        let(new_p,mut new_c)=split_rx(7,2,lane(2),32).unwrap();
        let nt=new_p.token();
        let stale=new_p.try_publish(&old,rx_item(&mut a,80));
        assert_eq!(stale.err().unwrap().0,DirectionError::Stale);
        new_p.try_publish(&nt,rx_item(&mut a,81)).unwrap();
        let mut new_out=Vec::with_capacity(1);
        assert_eq!(new_c.drain_ready(&mut new_out),1);
        assert_eq!(a.report().loaned,33);
        drop(old_out);drop(new_out);
        assert_eq!(a.report().loaned,0);
    }
}
