//! Shared Windows original-FakeTCP cold candidate carrier. Normal and Game
//! both use the existing native RX/TX workers. No new ring, native thread,
//! or hot Go callback. Only an unmatched cold port enters this mailbox.
use super::*;
use std::sync::atomic::{AtomicBool,AtomicU32,Ordering};
use std::sync::mpsc::{sync_channel,SyncSender};
use std::time::Duration;
use wbd_platform::windows_native_io::WakeEvent;
use wbd_platform::windows_xdp_tx::XdpTx;
const FRAME_CAP:usize=2304;
const EARLY_CAP:usize=256;
pub(super) struct NativeColdPort{
    pub(super) port:AtomicU32,
    pub(super) rx:Mutex<VecDeque<Vec<u8>>>,
    changed:std::sync::Condvar,
    pub(super) tx:Mutex<Option<(u16,Vec<u8>,SyncSender<i32>)>>,
    pub(super) tx_pending:AtomicBool,
    pub(super) raw_rx:usize,
    initial_ports:[u16;4],
}
impl NativeColdPort{
    pub(super) fn new(raw_rx:usize,initial_ports:[u16;4])->Self{
        Self{port:AtomicU32::new(0),rx:Mutex::new(VecDeque::new()),
            changed:std::sync::Condvar::new(),tx:Mutex::new(None),
            tx_pending:AtomicBool::new(false),raw_rx,initial_ports}
    }
    pub(super) fn offer_rx(&self,port:u16,frame:&[u8]){
        if self.port.load(Ordering::Acquire)!=u32::from(port)||frame.len()>FRAME_CAP{return}
        if let Ok(mut q)=self.rx.lock(){
            // Recheck after lock: an aborted cold attempt can no longer
            // receive anything from the old port, including queued frames.
            if self.port.load(Ordering::Acquire)==u32::from(port)&&q.len()<EARLY_CAP{
                q.push_back(frame.to_vec());self.changed.notify_one();
            }
        }
    }
    pub(super) fn read(&self,port:u16,dst:&mut [u8])->i32{
        let Ok(q)=self.rx.lock()else{return -1};
        let Ok((mut q,_))=self.changed.wait_timeout_while(q,Duration::from_millis(50),|q|
            q.is_empty()&&self.port.load(Ordering::Acquire)==u32::from(port))
            else{return -1};
        if self.port.load(Ordering::Acquire)!=u32::from(port){return -1}
        let Some(frame)=q.pop_front()else{return 0};
        if frame.len()>dst.len(){return -1}
        dst[..frame.len()].copy_from_slice(&frame);frame.len() as i32
    }
    pub(super) fn close(&self,port:u16)->Result<(),i32>{
        if self.port.load(Ordering::Acquire)!=u32::from(port){return Err(INVALID)}
        // No queued TX may run after this point. The original TX worker
        // holds this lock only during one genuine candidate frame send.
        self.detach(port)?;
        unsafe{wbd_platform::windows_xdp_rx::cold_change_port(self.raw_rx,port,false)}
            .map_err(|_|BAD_STAGE)
    }
    // Transfer ownership of the reserved port to a live native path;
    // do not remove its driver bit or reservation.
    pub(super) fn detach(&self,port:u16)->Result<(),i32>{
        if self.port.load(Ordering::Acquire)!=u32::from(port){return Err(INVALID)}
        let mut tx=self.tx.lock().map_err(|_|BAD_STAGE)?;
        self.port.store(0,Ordering::Release);
        if let Some((_,_,reply))=tx.take(){let _=reply.send(-1);}
        self.tx_pending.store(false,Ordering::Release);
        let mut rx=self.rx.lock().map_err(|_|BAD_STAGE)?;
        rx.clear();self.changed.notify_all();
        Ok(())
    }
    pub(super) fn begin(&self,port:u16)->Result<(),i32>{
        if port==0||self.initial_ports.contains(&port)||self.port.load(Ordering::Acquire)!=0{
            return Err(INVALID)
        }
        // Publish the exact new port after the socket is exclusively held
        // and the existing XDP program can receive it. SYN starts later.
        unsafe{wbd_platform::windows_xdp_rx::cold_change_port(self.raw_rx,port,true)}
            .map_err(|_|BAD_STAGE)?;
        self.port.store(u32::from(port),Ordering::Release);Ok(())
    }
    pub(super) fn send_one(&self,npf:&mut XdpTx)->Result<(),i32>{
        if !self.tx_pending.load(Ordering::Acquire){return Ok(())}
        let mut tx=self.tx.lock().map_err(|_|BAD_STAGE)?;
        let Some((port,frame,reply))=tx.take()else{
            self.tx_pending.store(false,Ordering::Release);return Ok(())
        };
        self.tx_pending.store(false,Ordering::Release);
        if self.port.load(Ordering::Acquire)!=u32::from(port){let _=reply.send(-1);return Ok(())}
        let result=npf.send_batch(&[&frame]);
        let _=reply.send(if result.accepted_prefix==1&&result.uncertain_index.is_none(){1}else{-1});
        // No TX credit is a cold candidate miss, not a sibling failure.
        if npf.failed()||result.error.is_some_and(|e|e!=wbd_platform::TxError::WouldBlock){return Err(BAD_STAGE)}
        Ok(())
    }
    // Same original FakeTCP frame and exact accepted driver prefix.
    // Only this cold call waits; the live TX owner never waits on Go.
    pub(super) fn write(&self,port:u16,bytes:&[u8],wake:&WakeEvent)->i32{
        if bytes.len()<54||bytes.len()>FRAME_CAP{return -1}
        let off=14+usize::from(bytes[14]&15)*4;
        if bytes[12..14]!=[8,0]||bytes[14]>>4!=4||bytes[23]!=6||
            off<34||off+20>bytes.len()||
            u16::from_be_bytes([bytes[off],bytes[off+1]])!=port{return -1}
        let (reply,rx)=sync_channel(1);
        {
            let Ok(mut tx)=self.tx.lock()else{return -1};
            if self.port.load(Ordering::Acquire)!=u32::from(port)||tx.is_some(){return -1}
            *tx=Some((port,bytes.to_vec(),reply));
            self.tx_pending.store(true,Ordering::Release);
        }
        if wake.wake().is_ok(){
            if let Ok(result)=rx.recv_timeout(Duration::from_secs(2)){return result}
        }
        if let Ok(mut q)=self.tx.lock(){
            if q.as_ref().is_some_and(|(p,_,_)|*p==port){
                q.take();self.tx_pending.store(false,Ordering::Release);
            }
        }
        rx.try_recv().unwrap_or(-1)
    }
}
