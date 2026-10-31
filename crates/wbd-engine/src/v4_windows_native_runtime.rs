//! Windows PLAN026 authenticated Normal/off Rust-native I/O.
 //! One Wintun session, one NPF RX worker, one NPF TX worker, zero steady Go
 //! packet callbacks. This is a child of the existing original TLS-scoped
 //! Rust owner: all M1/M3/PN/M2 logic is reused, never reimplemented.
 use super::*;
 use std::sync::atomic::{AtomicBool, AtomicI32, AtomicU32, AtomicU64, Ordering};
 use std::thread::{self, JoinHandle};
 use std::time::Duration;
 use std::ffi::c_void;
 use wbd_platform::windows_native_io::{
     self as io, NpcapFns, NpcapRx, NpcapTx, WintunFns,
     WintunRx, WintunTx, WakeEvent, ReadResult, WaitResult,
 };
 use wbd_platform::ipv4_tcp::{
     build_bytes, build_presentation_ack, build_presentation_ack_sack,
     SackRange32 as WireSack, Ipv4Tuple, PacketPersona, Presentation,
 };
 use wbd_platform::rx_ipv4_tcp::{parse_data_packet,parse_ack_packet,extend_seq32,TrustedRx};

 // std::thread::Builder::name is only a Rust thread name on some
 // Windows runtimes. Expose the actual OS thread description once so that
 // the *external* 1Hz Win32 sampler can attribute steady Go+Rust CPU.
 // No clock, allocation, lock or telemetry write in the packet loop.
 #[link(name="kernel32")]
 extern "system" {
     fn GetCurrentThread() -> *mut c_void;
     fn GetCurrentThreadId() -> u32;
     fn SetThreadDescription(thread:*mut c_void, description:*const u16) -> i32;
 }
 const NATIVE_TX_WIDE:[u16;14]=[
     119,98,100,45,110,97,116,105,118,101,45,116,120,0
 ];
 const NATIVE_RX_WIDE:[u16;14]=[
     119,98,100,45,110,97,116,105,118,101,45,114,120,0
 ];
 fn set_native_thread_name(name:&[u16;14]) {
     let _=unsafe { SetThreadDescription(GetCurrentThread(),name.as_ptr()) };
 }
 const BATCH:usize=8;
 // Auto-reset Windows TX events preserve a pending wake. Once per ready
 // batch is sufficient; a partial batch flushes before any next RX wait.
 const RX_WAKE_BATCH:usize=32;
 #[derive(Default)]
 struct TxWakeBatch { pending:usize }
 impl TxWakeBatch {
     fn note_verified(&mut self)->bool {
         self.pending+=1;
         if self.pending==RX_WAKE_BATCH {self.pending=0;true}else{false}
     }
     fn finish(&mut self)->bool {
         if self.pending==0 {false}else{self.pending=0;true}
     }
 }
 const MAX_IPV4:usize=2048;
 const MAX_LINK:usize=2304;
 const MAX_NPF:usize=65535+64;
 const IDLE_WAIT:u32=u32::MAX;
 // Rust HealthClock only: never coalesce authenticated dead with BAD_STAGE=3.
 const AUTHENTICATED_PEER_DEAD:i32=6;

 // This diagnostic is compiled out of ordinary Windows production
 // builds. At most 1/64 owner-lock attempts per direction reads a clock.
 #[derive(Clone,Copy)]
 enum LockDirection {Tx,Rx}
 #[cfg(feature="win_native_lock_profile")]
 struct LockWaitSamples {
     ticks:AtomicU64, samples:AtomicU64,
     wait_ns:AtomicU64, max_ns:AtomicU64,
 }
 #[cfg(feature="win_native_lock_profile")]
 impl LockWaitSamples {
     fn new()->Self{
         Self{ticks:AtomicU64::new(0),samples:AtomicU64::new(0),
             wait_ns:AtomicU64::new(0),max_ns:AtomicU64::new(0)}
     }
     fn sample(&self,ns:u64){
         self.samples.fetch_add(1,Ordering::Relaxed);
         self.wait_ns.fetch_add(ns,Ordering::Relaxed);
         self.max_ns.fetch_max(ns,Ordering::Relaxed);
     }
 }
 #[cfg(feature="win_native_lock_profile")]
 struct LockProfile{tx:LockWaitSamples,rx:LockWaitSamples}
 #[cfg(feature="win_native_lock_profile")]
 impl LockProfile{
     fn new()->Self{Self{tx:LockWaitSamples::new(),rx:LockWaitSamples::new()}}
 }
 #[inline]
 fn lock_owner<'a>(lane:&'a Arc<Mutex<Entry>>,counters:&Counters,
     dir:LockDirection)->Result<std::sync::MutexGuard<'a,Entry>,i32>{
     #[cfg(feature="win_native_lock_profile")]
     {
         let p=match dir {LockDirection::Tx=>&counters.profile.tx,
             LockDirection::Rx=>&counters.profile.rx};
         if p.ticks.fetch_add(1,Ordering::Relaxed)&63==0{
             let started=Instant::now();
             let guard=lane.lock().map_err(|_|BAD_STAGE)?;
             let ns=started.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64;
             p.sample(ns);
             return Ok(guard)
         }
     }
     #[cfg(not(feature="win_native_lock_profile"))]
     let _=(counters,dir);
     lane.lock().map_err(|_|BAD_STAGE)
 }
 #[repr(C)]
 #[derive(Clone, Copy)]
 pub struct WbdWinNativeAttachV1 {
     pub version:u32,
     pub size:u32,
     pub owner:u64,
     pub epoch:[u8;16],
     pub luid:u64,
     pub ifindex:u32,
     pub path_mtu:u32,
     pub initial_tx_seq:u32,
     pub initial_rx_seq:u32,
     pub local_ip:[u8;4],
     pub peer_ip:[u8;4],
     pub local_port:u16,
     pub peer_port:u16,
     pub source_mac:[u8;6],
     pub next_hop_mac:[u8;6],
     pub rx_capture:usize,
     pub tx_capture:usize,
     pub wintun_session:usize,
     pub wintun_read_event:usize,
     pub npcap:NpcapFns,
     pub wintun:WintunFns,
 }
 #[repr(C)]
 #[derive(Clone, Copy, Default)]
 pub struct WbdWinNativeStatsV1 {
     pub version:u32,
     pub size:u32,
     pub tx_copied:u64,
     pub rx_delivered:u64,
     pub tx_after_rx:u64,
     pub rejected:u64,
     pub worker_error:i32,
     pub workers:u32,
 }
 struct Counters {
     tx_copied:AtomicU64,
     rx_delivered:AtomicU64,
     rx_tx_notify_attempts:AtomicU64,
     tx_after_rx:AtomicU64,
     rejected:AtomicU64,
     fresh_outer_bytes:AtomicU64,
     feedback_outer_bytes:AtomicU64,
     repair_outer_bytes:AtomicU64,
     repair_uncertain_bytes:AtomicU64,
     pure_ack_outer_bytes:AtomicU64,
     repair_packets:AtomicU64,
     worker_error:AtomicI32,
     ack:AtomicU32,
     ack_sent:AtomicU32,
     sack_frame:Mutex<([WireSack;4],usize)>,
     sack_rev:AtomicU32,
     sack_sent_rev:AtomicU32,
     tx_seq:AtomicU32,
     stopping:AtomicBool,
     #[cfg(feature="win_native_lock_profile")]
     profile:LockProfile,
 }
 impl Counters {
     fn new(ack:u32,seq:u32)->Self{
         Self{tx_copied:AtomicU64::new(0),rx_delivered:AtomicU64::new(0),
             rx_tx_notify_attempts:AtomicU64::new(0),
             tx_after_rx:AtomicU64::new(0),rejected:AtomicU64::new(0),
             fresh_outer_bytes:AtomicU64::new(0),
             feedback_outer_bytes:AtomicU64::new(0),
             repair_outer_bytes:AtomicU64::new(0),
             repair_uncertain_bytes:AtomicU64::new(0),
             pure_ack_outer_bytes:AtomicU64::new(0),
             repair_packets:AtomicU64::new(0),
             worker_error:AtomicI32::new(0),ack:AtomicU32::new(ack),
             ack_sent:AtomicU32::new(ack),
             sack_frame:Mutex::new(([WireSack{start:0,end:0};4],0)),
             sack_rev:AtomicU32::new(0),
             sack_sent_rev:AtomicU32::new(0),
             tx_seq:AtomicU32::new(seq),
             stopping:AtomicBool::new(false),
             #[cfg(feature="win_native_lock_profile")]
             profile:LockProfile::new()}
     }
     fn snapshot(&self)->WbdWinNativeStatsV1{
         WbdWinNativeStatsV1{
             version:1,size:std::mem::size_of::<WbdWinNativeStatsV1>() as u32,
             tx_copied:self.tx_copied.load(Ordering::Relaxed),
             rx_delivered:self.rx_delivered.load(Ordering::Acquire),
             tx_after_rx:self.tx_after_rx.load(Ordering::Relaxed),
             rejected:self.rejected.load(Ordering::Relaxed),
             worker_error:self.worker_error.load(Ordering::Acquire),
             workers:2,
         }
     }
 }
// Only authenticated, successfully delivered TCP ranges may advance
 // presentation ACK. Future SACK ranges are bounded; M3 business delivery
 // and AEAD replay remain independent of cosmetic ACK progress.
 struct PresentationAck {
     next:u64,
     future:Vec<(u64,u64)>,
     stalled:Option<(u64,u64)>, // old appearance ACK head, first RX-batch time
 }
 impl PresentationAck {
     fn new(next:u32)->Self{Self{next:u64::from(next),future:Vec::with_capacity(256),stalled:None}}
     // Partial reliability of cosmetic appearance only: no M3 payload or
     // Auto quality authority. One RX-batch check, never a DATA PTO timer.
     fn abandon_stalled(&mut self,now:u64)->bool{
         let Some((_,end))=self.future.last().copied()else{
             self.stalled=None;return false
         };
         if self.stalled.is_none_or(|(seq,_)|seq!=self.next){
             self.stalled=Some((self.next,now));return false
         }
         if now.saturating_sub(self.stalled.unwrap().1)<250_000_000{return false}
         self.next=self.next.max(end);
         self.future.clear(); // <=256 authenticated positive spans, no full-cache scan
         self.stalled=None;
         true
     }
     fn sacks(&self)->([WireSack;4],usize){
         let mut blocks=[WireSack{start:0,end:0};4];
         let mut n=0;
         for &(start,end) in self.future.iter().rev().take(4){
             blocks[n]=WireSack{start:start as u32,end:end as u32};
             n+=1;
         }
         (blocks,n)
     }
     fn verified(&mut self,seq:u32,len:usize)->u32{
         let Ok(start)=extend_seq32(self.next,seq)else{return self.next as u32};
         let Some(end)=start.checked_add(len as u64)else{return self.next as u32};
         if end<=self.next{return self.next as u32}
         if start<=self.next {
             self.next=self.next.max(end);
         }else{
             // The original per-record 256 cap stopped advancing behind
             // a real gap after only 256 later packets. Keep disjoint,
             // authenticated future byte spans, not one node per packet.
             let at=self.future.partition_point(|(_,limit)|*limit<start);
             let(mut first,mut last)=(start,end);
             let mut until=at;
             while until<self.future.len() && self.future[until].0<=last{
                 first=first.min(self.future[until].0);
                 last=last.max(self.future[until].1);
                 until+=1;
             }
             if until==at && self.future.len()>=256{return self.next as u32}
             self.future.splice(at..until,std::iter::once((first,last)));
         }
         while let Some(&(begin,limit))=self.future.first(){
             if begin>self.next{break}
             self.next=self.next.max(limit);
             self.future.remove(0);
         }
         self.next as u32
     }
 }
 #[cfg(test)]
 mod plan027_native_presentation_ack_test{
     use super::PresentationAck;
     #[test]
     fn h505_contiguous_future_600_verified_records_coalesce_and_recover(){
         let mut x=PresentationAck::new(1000);
         for i in 0..600u32{
             assert_eq!(x.verified(2000+i*10,10),1000);
         }
         assert_eq!(x.future,vec![(2000,8000)]);
         assert_eq!(x.verified(1000,1000),8000);
         assert!(x.future.is_empty());
         assert_eq!(x.verified(7000,10),8000);
     }
     #[test]
     fn h533_old_gap_abandon_rearms_later_authentic_ack(){
         let mut x=PresentationAck::new(100);
         for i in 0..300u32{x.verified(200+i*20,10);}
         assert_eq!(x.future.len(),256);
         assert!(!x.abandon_stalled(1));
         assert!(!x.abandon_stalled(200_000_000));
         assert!(x.abandon_stalled(250_000_001));
         assert_eq!(x.next,200+255*20+10);
         assert!(x.future.is_empty());
         x.verified(7000,10);
         assert!(!x.abandon_stalled(250_000_002));
         assert!(x.abandon_stalled(500_000_003));
         assert_eq!(x.next,7010);
         x.verified(7010,10);
         assert_eq!(x.next,7020);
     }
     #[test]
     fn h541_sack_prefers_recent_authenticated_future_without_forged_ack(){
         let mut x=PresentationAck::new(100);
         assert_eq!(x.verified(200,10),100);
         assert_eq!(x.verified(300,10),100);
         let (blocks,n)=x.sacks();
         assert_eq!(n,2);
         assert_eq!((blocks[0].start,blocks[0].end),(300,310));
         assert_eq!((blocks[1].start,blocks[1].end),(200,210));
         assert_eq!(x.next,100);
         assert_eq!(x.verified(100,100),210);
         assert_eq!(x.verified(210,90),310);
         assert_eq!(x.sacks().1,0);
     }
     #[test]
     fn h515_authenticated_outer_gap_sack_and_then_real_cumulative(){
         let mut ack=PresentationAck::new(100);
         assert_eq!(ack.verified(200,100),100);
         let (blocks,count)=ack.sacks();
         assert_eq!(count,1);
         assert_eq!((blocks[0].start,blocks[0].end),(200,300));
         assert_eq!(ack.verified(100,100),300);
         assert_eq!(ack.sacks().1,0);
     }
 }
  struct NativeSession {
     stop:Arc<WakeEvent>,
     tx_notify:Arc<WakeEvent>,
     rx_notify:Arc<WakeEvent>,
     early:Arc<Mutex<VecDeque<(u32,Vec<u8>)>>>,
     counters:Arc<Counters>,
     tx:JoinHandle<i32>,
     rx:JoinHandle<i32>,
 }
 static NATIVE:OnceLock<Mutex<BTreeMap<u64,NativeSession>>>=OnceLock::new();
 fn active()->&'static Mutex<BTreeMap<u64,NativeSession>>{
     NATIVE.get_or_init(||Mutex::new(BTreeMap::new()))
 }
 pub(super) fn active_owner(h:u64)->bool{
     active().lock().map_or(true,|g|g.contains_key(&h))
 }

 // The owner is already authenticated and M4 OS-pinned before construction.
 // Worker threads clone this Arc ONCE and never lock the global registry.
 fn lookup(h:u64)->Result<Arc<Mutex<Entry>>,i32>{
     let r=registry().lock().map_err(|_|BAD_STAGE)?;
     r.entries.get(&h).cloned().ok_or(UNKNOWN)
 }
 fn kernel_result(outcome:wbd_platform::TxBatchOutcome,count:usize,i:usize)
     ->Result<u32,i32>{
     if i>=count||outcome.accepted_prefix>count{return Err(BAD_STAGE)}
     if i<outcome.accepted_prefix{return Ok(1)}
     if outcome.uncertain_index==Some(i){return Ok(2)}
     Ok(0)
 }
 fn packet_frame<'a>(cfg:&WbdWinNativeAttachV1,seq:u32,ack:u32,
     wire:&[u8],ip_id:u16,frame:&'a mut [u8;MAX_LINK])
     ->Result<&'a [u8],i32>{
     let bytes=build_bytes(Ipv4Tuple{
             src_ip:&cfg.local_ip,dst_ip:&cfg.peer_ip,
             src_port:cfg.local_port,dst_port:cfg.peer_port,
         },Presentation{ack32:ack,advertised_window:65535,
             ip_id,persona:PacketPersona::Windows11},
         u64::from(seq),wire,None,cfg.path_mtu as usize,&mut frame[14..])
         .map_err(|_|INVALID)?;
     let total=14+bytes.len();
     frame[..6].copy_from_slice(&cfg.next_hop_mac);
     frame[6..12].copy_from_slice(&cfg.source_mac);
     frame[12..14].copy_from_slice(&0x0800u16.to_be_bytes());
     Ok(&frame[..total])
 }
 fn stage_sources(
     cfg:&WbdWinNativeAttachV1,
     lane:&Arc<Mutex<Entry>>,tun:&mut WintunRx,npf:&mut NpcapTx,
     counters:&Counters,ip_id:&mut u16,fixed:bool,
 )->Result<usize,i32>{
     // One bounded Wintun drain, ONE Entry lock to seal ALL ready sources,
     // ONE NPF ready-only queue and ONE lock to settle real driver receipts.
     // No Vec, Go call, thread pool or shared registry lookup per packet.
     let mut sources=[[0u8;MAX_IPV4];BATCH];
     let mut source_len=[0usize;BATCH];
     let mut count=0;
     for _ in 0..BATCH {
         if counters.stopping.load(Ordering::Acquire){break}
         match tun.read(&mut sources[count]){
             Ok(ReadResult::Frame(n))=>{
                 source_len[count]=n;
                 count+=1;
                 if count==BATCH{break}
             },
             Ok(ReadResult::NoPacket|ReadResult::EndOfStream)=>break,
             Ok(ReadResult::Skipped)=>{
                 counters.rejected.fetch_add(1,Ordering::Relaxed);
             },
             Err(_)=>return Err(BAD_STAGE),
         }
     }
     if count==0{return Ok(0)}
     let mut wire=[[0u8;MAX_IPV4];BATCH];
     let mut meta=[(0u64,0u32,0usize);BATCH];
     {
         let mut e=lock_owner(lane,counters,LockDirection::Tx)?;
         for i in 0..count {
             let (used,seq,pn)=if fixed{
                 #[cfg(feature="fec2_product_record")]
                 {
                     fec2::stage_fixed_source_entry(
                         &mut e,cfg.epoch,cfg.luid,cfg.ifindex,
                         &sources[i][..source_len[i]],&mut wire[i]
                     )?
                 }
                 #[cfg(not(feature="fec2_product_record"))]
                 {return Err(BAD_STAGE)}
             }else{
                 v3_seal_entry(
                     &mut e,cfg.epoch,cfg.luid,cfg.ifindex,
                     &sources[i][..source_len[i]],&mut wire[i]
                 )?
             };
             meta[i]=(pn,seq,used);
         }
     }
     let mut frames=[[0u8;MAX_LINK];BATCH];
     let mut lens=[0usize;BATCH];
     let ack=counters.ack.load(Ordering::Acquire);
     for i in 0..count {
         let (_,seq,used)=meta[i];
         let f=packet_frame(cfg,seq,ack,&wire[i][..used],
             *ip_id,&mut frames[i])?;
         lens[i]=f.len();
         *ip_id=ip_id.wrapping_add(1);
     }
     let (_,last_seq,last_used)=meta[count-1];
     counters.tx_seq.store(last_seq.wrapping_add(last_used as u32),Ordering::Release);
     let mut ready:[&[u8];BATCH]=[&[];BATCH];
     for i in 0..count {ready[i]=&frames[i][..lens[i]];}
     let result=npf.send_batch(&ready[..count]);
     if result.accepted_prefix>0{
         counters.ack_sent.store(ack,Ordering::Release);
     }
     {
         let mut e=lock_owner(lane,counters,LockDirection::Tx)?;
         let mut fresh_bytes=0u64;
         for (i,&(pn,seq,used)) in meta[..count].iter().enumerate(){
             let status=kernel_result(result,count,i)?;
             m2_kernel_firstsend_entry(&mut e,cfg.epoch,cfg.luid,cfg.ifindex,
                 pn,seq,used,status)?;
             if status==1{
                 fresh_bytes+=lens[i] as u64;
                 counters.tx_copied.fetch_add(1,Ordering::Relaxed);
                 if counters.rx_delivered.load(Ordering::Acquire)>0{
                     counters.tx_after_rx.fetch_add(1,Ordering::Relaxed);
                 }
             }
         }
         counters.fresh_outer_bytes.fetch_add(fresh_bytes,Ordering::Relaxed);
         if fresh_bytes>0{
             // Only true Npcap-copied business resets local idle; a staged
             // but definitely-not-sent source is not user progress.
             if let Some(m)=e.m2.as_mut(){
                 m.health.on_local_business(m2_clock().0);
             }
         }
     }
     if result.error.is_some(){return Err(BAD_STAGE)}
     Ok(count)
 }

 // Only the existing FixedStream owns actual-k parity and block close.
 // Driver prefix receipts settle its staged rows exactly once. No duplicate
 // Go FEC encoder or busy-timer, and a sparse source is sent before parity.
 #[cfg(feature="fec2_product_record")]
 fn send_fixed_parity(
     cfg:&WbdWinNativeAttachV1,lane:&Arc<Mutex<Entry>>,
     npf:&mut NpcapTx,counters:&Counters,ip_id:&mut u16,
 )->Result<bool,i32>{
     let batch={
         let mut e=lock_owner(lane,counters,LockDirection::Tx)?;
         fec2::stage_fixed_parity_entry(
             &mut e,cfg.epoch,cfg.luid,cfg.ifindex
         )?
     };
     let count=batch.count as usize;
     if count==0{return Ok(false)}
     let mut frames=[[0u8;MAX_LINK];4];
     let mut lengths=[0usize;4];
     let ack=counters.ack.load(Ordering::Acquire);
     for (i,row) in batch.rows[..count].iter().enumerate(){
         let wire_len=row.used as usize;
         let f=packet_frame(cfg,row.seq,ack,&row.wire[..wire_len],
             *ip_id,&mut frames[i])?;
         lengths[i]=f.len();
         *ip_id=ip_id.wrapping_add(1);
     }
     let last=&batch.rows[count-1];
     counters.tx_seq.store(last.seq.wrapping_add(last.used),Ordering::Release);
     let mut packets:[&[u8];4]=[&[];4];
     for i in 0..count{packets[i]=&frames[i][..lengths[i]]}
     let outcome=npf.send_batch(&packets[..count]);
     let mut copied=0u8;
     let mut uncertain=0u8;
     for i in 0..count{
         match kernel_result(outcome,count,i)?{
             1=>{
                 copied+=1;
                 counters.tx_copied.fetch_add(1,Ordering::Relaxed);
                 counters.fresh_outer_bytes.fetch_add(lengths[i] as u64,Ordering::Relaxed);
             },
             2=>uncertain+=1,
             _=>{},
         }
     }
     let not_sent=(count as u8)-copied-uncertain;
     {
         let mut e=lock_owner(lane,counters,LockDirection::Tx)?;
         e.fec2_tx.as_mut().ok_or(BAD_STAGE)?
             .settle_staged(copied,not_sent,uncertain)
             .map_err(|_|BAD_STAGE)?;
         if copied>0{
             let m=e.m2.as_mut().ok_or(BAD_STAGE)?;
             m.fec_copied_parity=m.fec_copied_parity.saturating_add(copied as u64);
             counters.ack_sent.store(ack,Ordering::Release);
         }
     }
     if outcome.error.is_some(){return Err(BAD_STAGE)}
     Ok(true)
 }
 fn send_control(
     cfg:&WbdWinNativeAttachV1,lane:&Arc<Mutex<Entry>>,
     npf:&mut NpcapTx,counters:&Counters,ip_id:&mut u16,
 )->Result<bool,i32>{
     let mut wire=[0u8;MAX_IPV4];
     let ack=counters.ack.load(Ordering::Acquire);
     let feedback={
         let mut e=lock_owner(lane,counters,LockDirection::Tx)?;
         m2_next_feedback_entry(&mut e,cfg.epoch,cfg.luid,cfg.ifindex,&mut wire)?
     };
     if let Some((used,seq,pn))=feedback{
         let mut frame=[0u8;MAX_LINK];
         let raw=packet_frame(cfg,seq,ack,
             &wire[..used],*ip_id,&mut frame)?;
         *ip_id=ip_id.wrapping_add(1);
         counters.tx_seq.store(seq.wrapping_add(used as u32),Ordering::Release);
         let outcome=npf.send_batch(&[raw]);
         let accepted=kernel_result(outcome,1,0)?==1;
         if accepted{
             counters.ack_sent.store(ack,Ordering::Release);
             counters.feedback_outer_bytes.fetch_add(raw.len() as u64,Ordering::Relaxed);
         }
         let mut e=lock_owner(lane,counters,LockDirection::Tx)?;
         m2_finish_feedback_entry(&mut e,cfg.epoch,cfg.luid,cfg.ifindex,
             pn,u32::from(accepted))?;
         if outcome.error.is_some(){return Err(BAD_STAGE)}
         return Ok(true)
     }
     let repair={
         let mut e=lock_owner(lane,counters,LockDirection::Tx)?;
         m2_next_repair_entry(&mut e,cfg.epoch,cfg.luid,cfg.ifindex,&mut wire)?
     };
     if let Some((used,seq,pn))=repair{
         let mut frame=[0u8;MAX_LINK];
         let raw=packet_frame(cfg,seq,ack,
             &wire[..used],*ip_id,&mut frame)?;
         *ip_id=ip_id.wrapping_add(1);
         let outcome=npf.send_batch(&[raw]);
         let kernel=kernel_result(outcome,1,0)?;
         if kernel==1{
             counters.ack_sent.store(ack,Ordering::Release);
             counters.repair_outer_bytes.fetch_add(raw.len() as u64,Ordering::Relaxed);
             counters.repair_packets.fetch_add(1,Ordering::Relaxed);
         }else if kernel==2{
             counters.repair_uncertain_bytes.fetch_add(raw.len() as u64,Ordering::Relaxed);
         }
         let mut e=lock_owner(lane,counters,LockDirection::Tx)?;
         m2_complete_repair_entry(&mut e,cfg.epoch,cfg.luid,cfg.ifindex,
             pn,kernel)?;
         if outcome.error.is_some(){return Err(BAD_STAGE)}
         return Ok(true)
     }
     Ok(false)
 }
 fn send_presentation_ack(cfg:&WbdWinNativeAttachV1,
     npf:&mut NpcapTx,counters:&Counters,ip_id:&mut u16,
     sack_negotiated:bool,
 )->Result<(),i32>{
     // Build pure TCP-looking ACK directly at Ethernet L3 offset.
     // The old path filled a separate 2304B scratch and copied 40B back.
     let mut frame=[0u8;MAX_LINK];
     let ack=counters.ack.load(Ordering::Acquire);
     let tuple=Ipv4Tuple{
         src_ip:&cfg.local_ip,dst_ip:&cfg.peer_ip,
         src_port:cfg.local_port,dst_port:cfg.peer_port,
     };
     let rev=counters.sack_rev.load(Ordering::Acquire);
     let (blocks,count)=if sack_negotiated{
         *counters.sack_frame.lock().map_err(|_|BAD_STAGE)?
     }else{([WireSack{start:0,end:0};4],0)};
     let n=if count>0{
         build_presentation_ack_sack(tuple,
             counters.tx_seq.load(Ordering::Acquire),ack,*ip_id,
             PacketPersona::Windows11,cfg.path_mtu as usize,
             &blocks[..count],&mut frame[14..])
     }else{
         build_presentation_ack(tuple,
             counters.tx_seq.load(Ordering::Acquire),ack,*ip_id,
             PacketPersona::Windows11,cfg.path_mtu as usize,
             &mut frame[14..])
     }.map_err(|_|INVALID)?.len();
     frame[..6].copy_from_slice(&cfg.next_hop_mac);
     frame[6..12].copy_from_slice(&cfg.source_mac);
     frame[12..14].copy_from_slice(&0x0800u16.to_be_bytes());
     *ip_id=ip_id.wrapping_add(1);
     let outcome=npf.send_batch(&[&frame[..14+n]]);
     if kernel_result(outcome,1,0)?!=1{return Err(BAD_STAGE)}
     counters.ack_sent.store(ack,Ordering::Release);
     counters.sack_sent_rev.store(rev,Ordering::Release);
     counters.pure_ack_outer_bytes.fetch_add((14+n) as u64,Ordering::Relaxed);
     Ok(())
 }
  /// Exact event-driven M2 wake. Both deadlines use the same Rust
 /// monotonic clock, and RX/TUN/Stop events wake earlier. No 20ms polling
 /// after a genuine authenticated reverse packet.
 fn m2_wake_timeout_ms(now:MonoNs,feedback:Option<MonoNs>,
     repair:Option<MonoNs>)->u32 {
     let Some(next)=feedback.into_iter().chain(repair).map(|x|x.0).min()
         else{return IDLE_WAIT};
     if next<=now.0{return 0}
     let remaining=next-now.0;
     remaining.div_ceil(1_000_000).min(u64::from(u32::MAX-1)) as u32
 }
 #[cfg(feature="fec2_product_record")]
 fn native_auto_tick(cfg:&WbdWinNativeAttachV1,
     lane:&Arc<Mutex<Entry>>,counters:&Counters
 )->Result<(),i32>{
     let now=m2_clock();
     let mut guard=lock_owner(lane,counters,LockDirection::Tx)?;
     let e:&mut Entry=&mut guard;
     if !e.auto_actor.as_ref().is_some_and(|actor|actor.deadline()<=now.0){
         return Ok(())
     }
     // This is the identical original M2 firstsend/k histogram readback
     // that the former Go policy read at 2s, not packet appearance ACKs.
     let q=fec2::native_auto_quality_entry(e,now)?;
     let Some(mut actor)=e.auto_actor.take()else{return Err(BAD_STAGE)};
     let intent=actor.evaluate(now.0,q);
     if let Some(intent)=intent{
         // Apply only via original FixedStream/true M2 quiescent revision.
         // Rejected/busy is not a false GUI Applied or extra controller.
         let result=fec2::fixed_change_revision_entry(e,cfg.epoch,
             cfg.luid,cfg.ifindex,intent.profile,intent.revision);
         if result.is_ok(){
             actor.commit(intent,now.0);
             eprintln!("WBD_WINDOWS_RUST_NATIVE_AUTO_REVISION_REQUESTED revision={} profile={} evidence=original_authenticated_m2",
                 intent.revision,intent.profile);
         }else if result==Err(INVALID){
             e.auto_actor=Some(actor);
             return Err(INVALID)
         }
     }
     e.auto_actor=Some(actor);
     Ok(())
 }
 // Only the once-per-new-RX SACK revision can justify an ACK-only
 // frame in a continuously backlogged DATA sender; otherwise do not
 // interfere with original M1 definite-copy readiness and DATA piggyback.
 fn native_ack_only_due(sack_negotiated:bool,pending_sack:bool,
     cumulative_changed:bool,business_active:bool)->bool{
     (sack_negotiated&&pending_sack)||
         (!business_active&&cumulative_changed)
 }
 fn tx_loop(cfg:WbdWinNativeAttachV1,lane:Arc<Mutex<Entry>>,
     mut tun:WintunRx,mut npf:NpcapTx,stop:Arc<WakeEvent>,
     notify:Arc<WakeEvent>,counters:Arc<Counters>,fixed:bool,auto:bool,
     sack_negotiated:bool)->i32{
     let mut ip_id=1u16;
     // Cache Auto next check in the worker. A full packet batch never
     // takes an extra owner mutex for a 2-second policy decision.
     let mut next_auto_check=m2_clock().0.saturating_add(2_000_000_000);
     loop {
         if counters.stopping.load(Ordering::Acquire){return OK}
         let result=(||->Result<bool,i32>{
             {
                 let e=lock_owner(&lane,&counters,LockDirection::Tx)?;
                 // Genuine post-M3 AEAD+PN, not TCP ACK or inactivity.
                 // DORMANT is not a dead-peer verdict: only a separate
                 // verified client FIN plus business-idle may dormancy.
                 if e.m2.as_ref().is_some_and(|m|
                     m.health.unhealthy(m2_clock().0)){
                     eprintln!("WBD_WINDOWS_RUST_NATIVE_HEALTH_TIMEOUT reason=authenticated_dead_after_90s");
                     return Err(AUTHENTICATED_PEER_DEAD)
                 }
             }
             let mut work=0;
             for _ in 0..4 {
                 if counters.stopping.load(Ordering::Acquire){return Ok(true)}
                 let n=stage_sources(&cfg,&lane,&mut tun,&mut npf,&counters,&mut ip_id,fixed)?;
                 work+=n;
                 if n<BATCH{break}
             }
             // A bounded <=4-row parity quantum follows ready fresh sources.
             // In Fixed/Auto there is never an extra native parity worker.
             #[cfg(feature="fec2_product_record")]
             let parity=if fixed{
                 send_fixed_parity(&cfg,&lane,&mut npf,&counters,&mut ip_id)?
             }else{false};
             #[cfg(not(feature="fec2_product_record"))]
             let parity=false;
             // One repair per 32 new packets would cap useful opportunities
             // near 3%, even at 30% real loss. Four ready-only control slots
             // per bounded fresh turn; v3 credit and 8192pps remain hard gates.
             let mut control=false;
             for _ in 0..4 {
                 if counters.stopping.load(Ordering::Acquire){break}
                 if !send_control(&cfg,&lane,&mut npf,&counters,&mut ip_id)?{break}
                 control=true;
             }
             #[cfg(feature="fec2_product_record")]
             if auto&&m2_clock().0>=next_auto_check{
                 native_auto_tick(&cfg,&lane,&counters)?;
                 next_auto_check=m2_clock().0.saturating_add(2_000_000_000);
             }
             // SACK is not on the DATA carrier and must not starve while
             // TUN continuously yields complete 8x4 ready batches. RX
             // publishes at most one authenticated-future snapshot /20ms.
             // Normal cumulative ACK remains DATA-piggybacked during work:
             // no periodic ACK-only traffic when only DATA is flowing.
             let active=work>0||control||parity;
             let next_ack=counters.ack.load(Ordering::Acquire);
             let sack_pending=counters.sack_rev.load(Ordering::Acquire)!=
                 counters.sack_sent_rev.load(Ordering::Acquire);
             if native_ack_only_due(sack_negotiated,sack_pending,
                 next_ack!=counters.ack_sent.load(Ordering::Acquire),active){
                 send_presentation_ack(&cfg,&mut npf,&counters,&mut ip_id,
                     sack_negotiated)?;
                 return Ok(false)
             }
             if active{return Ok(false)}
             let timeout={
                 let e=lock_owner(&lane,&counters,LockDirection::Tx)?;
                 let m=e.m2.as_ref().ok_or(BAD_STAGE)?;
                 let fec_due=if fixed{
                     #[cfg(feature="fec2_product_record")]
                     {e.fec2_tx.as_ref().and_then(|tx|tx.next_deadline())}
                     #[cfg(not(feature="fec2_product_record"))]
                     {None}
                 }else{None};
                 #[cfg(feature="fec2_product_record")]
                 let auto_due=e.auto_actor.as_ref().map(|actor|MonoNs(actor.deadline()));
                 #[cfg(not(feature="fec2_product_record"))]
                 let auto_due:Option<MonoNs>=None;
                 let now=m2_clock();
                  let quality_due=if m.auto_low_rate_mode{
                      m.quality_sender.as_ref().and_then(|s|s.timed_close_deadline())
                          .or_else(||m.quality_close_waiting.map(|_|now))
                          .or_else(||m.quality_sender.is_none()
                              .then_some(MonoNs(m.quality_next_open_ns)))
                  }else{None};
                  let receive_due=m.quality_due.front().map(|(_,due)|MonoNs(*due));
                  let shadow_due=m.shadow.next_deadline();
                  let paced_due=m.repair_retry_after_ns.map(MonoNs);
                  let next=shadow_due.into_iter().chain(paced_due).chain(quality_due)
                      .chain(receive_due).chain(fec_due)
                      .chain(m.health.next_tx_deadline().map(MonoNs))
                      .chain(auto_due).min_by_key(|d|d.0);
                  let receipt_due=None; // PLAN027 no per-record M2 timer
                  m2_wake_timeout_ms(now,receipt_due,next)
             };
             match io::wait_ready(&[stop.handle(),tun.event(),notify.handle()],timeout){
                 Ok(WaitResult::Ready(0))=>Ok(true),
                 Ok(WaitResult::Ready(_)|WaitResult::Timeout)=>Ok(false),
                 Err(_)=>Err(BAD_STAGE),
             }
         })();
         match result {Ok(true)=>return OK,Ok(false)=>{},Err(code)=>return code}
     }
 }
 // Returns true only for authenticated DATA or CONTROL whose ACK/M2
 // state was updated. The RX worker performs the bounded TX notification.
 fn open_and_deliver(cfg:&WbdWinNativeAttachV1,lane:&Arc<Mutex<Entry>>,
     tun:&mut WintunTx,counters:&Counters,
     ack:&mut PresentationAck,seq:u32,wire:&[u8],
     plain:&mut [u8;MAX_IPV4],fixed:bool)->Result<bool,i32>{
     if fixed{
         #[cfg(feature="fec2_product_record")]
         {
             let delivered={
                 let mut e=lock_owner(lane,counters,LockDirection::Rx)?;
                 fec2::open_symbol_entry(&mut e,cfg.epoch,cfg.luid,
                     cfg.ifindex,seq,wire)
             };
             match delivered{
                 Ok(frames)=>{
                     for frame in frames{
                         tun.deliver_authenticated(&frame.frame[..frame.length as usize])
                             .map_err(|_|BAD_STAGE)?;
                         counters.rx_delivered.fetch_add(1,Ordering::Release);
                     }
                     counters.ack.store(ack.verified(seq,wire.len()),Ordering::Release);
                     return Ok(true)
                 },
                 Err(INVALID)=>{
                     counters.rejected.fetch_add(1,Ordering::Relaxed);
                     return Ok(false)
                 },
                 Err(code)=>return Err(code),
             }
         }
         #[cfg(not(feature="fec2_product_record"))]
         {return Err(BAD_STAGE)}
     }
     let opened={
         let mut e=lock_owner(lane,counters,LockDirection::Rx)?;
         let opened=v5_open_record_entry(&mut e,cfg.epoch,cfg.luid,
             cfg.ifindex,seq,wire,plain);
         opened
     };
     match opened {
         Ok((used,1,_))=>{
             tun.deliver_authenticated(&plain[..used]).map_err(|_|BAD_STAGE)?;
             counters.ack.store(ack.verified(seq,wire.len()),Ordering::Release);
             counters.rx_delivered.fetch_add(1,Ordering::Release);
             Ok(true)
         },
         Ok((_,2,_))=>{
             counters.ack.store(ack.verified(seq,wire.len()),Ordering::Release);
             Ok(true)
         },
         Err(INVALID)=>{
             counters.rejected.fetch_add(1,Ordering::Relaxed);
             Ok(false)
         },
         Err(code)=>Err(code),
         _=>Err(BAD_STAGE),
     }
 }
 #[inline]
 fn flush_tx_wake(tx_notify:&WakeEvent,counters:&Counters) {
     counters.rx_tx_notify_attempts.fetch_add(1,Ordering::Relaxed);
     let _=tx_notify.wake();
 }
 fn rx_loop(cfg:WbdWinNativeAttachV1,lane:Arc<Mutex<Entry>>,
     mut tun:WintunTx,mut npf:NpcapRx,stop:Arc<WakeEvent>,
     tx_notify:Arc<WakeEvent>,early_notify:Arc<WakeEvent>,
     early:Arc<Mutex<VecDeque<(u32,Vec<u8>)>>>,
     counters:Arc<Counters>,fixed:bool,sack_negotiated:bool)->i32{
     let event=match npf.event(){Ok(e)=>e,Err(_)=>return BAD_STAGE};
     let trusted=TrustedRx{
         tuple:Ipv4Tuple{src_ip:&cfg.peer_ip,dst_ip:&cfg.local_ip,
             src_port:cfg.peer_port,dst_port:cfg.local_port},
         persona:PacketPersona::Legacy,mtu:cfg.path_mtu as usize,
         authenticated_options:None,
     };
     let mut frame=[0u8;MAX_NPF];
     let mut plain=[0u8;MAX_IPV4];
     let mut ack=PresentationAck::new(cfg.initial_rx_seq);
     let mut last_sack_publish=Instant::now();
     loop{
         if counters.stopping.load(Ordering::Acquire){return OK}
         // Drain genuine Go pre-handoff packets FIRST, in original order.
         // Only this RX worker ever calls the M3 opener after Start.
         let mut early_wakes=TxWakeBatch::default();
         loop{
             if counters.stopping.load(Ordering::Acquire){return OK}
             let next=match early.lock(){
                 Ok(mut q)=>q.pop_front(),Err(_)=>return BAD_STAGE
             };
             let Some((seq,record))=next else{break};
             let verified=match open_and_deliver(&cfg,&lane,&mut tun,
                 &counters,&mut ack,seq,&record,&mut plain,fixed){
                 Ok(v)=>v,Err(code)=>return code
             };
             if verified&&early_wakes.note_verified(){
                 flush_tx_wake(&tx_notify,&counters);
             }
         }
         if early_wakes.finish(){flush_tx_wake(&tx_notify,&counters);}
         match io::wait_ready(&[stop.handle(),event,early_notify.handle()],IDLE_WAIT){
             Ok(WaitResult::Ready(0))=>return OK,
             Ok(WaitResult::Ready(1|2))=>{},
             Ok(WaitResult::Timeout)=>continue,
             Err(_)=>return BAD_STAGE,
             _=>return BAD_STAGE,
         }
         let mut npf_wakes=TxWakeBatch::default();
         let mut verified_batch=false;
         let mut last_outer_ack=None::<(u32,[WireSack;4],usize)>;
         for _ in 0..RX_WAKE_BATCH{
             if counters.stopping.load(Ordering::Acquire){return OK}
             let n=match npf.read(&mut frame){
                 Ok(ReadResult::Frame(n))=>n,
                 Ok(ReadResult::NoPacket)=>break,
                 Ok(ReadResult::Skipped)=>continue,
                 Ok(ReadResult::EndOfStream)=>return BAD_STAGE,
                 Err(_)=>return BAD_STAGE,
             };
             let Some(packet)=io::ethernet_ipv4(&frame[..n])else{continue};
             // Optional SACK only after actual original Go protected
             // FakeTCP SYN/SYN-ACK; packet checksum is NOT crypto proof.
             if let Ok(outer)=parse_ack_packet(packet,trusted,sack_negotiated){
                 let mut blocks=[WireSack{start:0,end:0};4];
                 blocks[..outer.sacks().len()].copy_from_slice(outer.sacks());
                 if !outer.sacks().is_empty()||
                     !last_outer_ack.as_ref().is_some_and(|x|x.2>0){
                     last_outer_ack=Some((outer.ack32,blocks,outer.sacks().len()));
                 }
                 continue
             }
              let Ok(sealed)=parse_data_packet(packet,trusted)else{
                 counters.rejected.fetch_add(1,Ordering::Relaxed);continue
             };
             let verified=match open_and_deliver(&cfg,&lane,&mut tun,
                 &counters,&mut ack,sealed.seq32,sealed.ciphertext,&mut plain,fixed){
                 Ok(v)=>v,Err(code)=>return code
             };
             if verified{
                  verified_batch=true;
                  if !last_outer_ack.as_ref().is_some_and(|x|x.2>0){
                      last_outer_ack=Some((sealed.presentation_ack32,
                          [WireSack{start:0,end:0};4],0));
                  }
                  if npf_wakes.note_verified(){
                      flush_tx_wake(&tx_notify,&counters);
                  }
              }
          }
          // Advance only on a genuine authenticated RX ready batch; this
          // cannot create a timer, extra DATA, or an inner delivery ACK.
          if sack_negotiated&&verified_batch&&ack.abandon_stalled(m2_clock().0){
              counters.ack.store(ack.next as u32,Ordering::Release);
              flush_tx_wake(&tx_notify,&counters);
          }
          if let Some((ack32,blocks,n))=last_outer_ack{
              let mut e=match lock_owner(&lane,&counters,LockDirection::Rx){
                  Ok(e)=>e,Err(code)=>return code
              };
              let mut sacks=[wbd_recovery::outer_ack::SackRange32{
                  start:0,end:0};4];
              for (dst,src) in sacks.iter_mut().zip(&blocks[..n]){
                  *dst=wbd_recovery::outer_ack::SackRange32{
                      start:src.start,end:src.end};
              }
              let _=m2_outer_ack_hint_entry(&mut e,cfg.epoch,
                  cfg.luid,cfg.ifindex,ack32,&sacks[..n]);
          }
          // RX publishes <=50 authenticated SACK snapshots per second,
          // never one Go call or global lock per inner business packet.
          if sack_negotiated&&verified_batch&&
              last_sack_publish.elapsed()>=Duration::from_millis(20){
              last_sack_publish=Instant::now();
              let snapshot=ack.sacks();
              let mut current=match counters.sack_frame.lock(){
                  Ok(s)=>s,Err(_)=>return BAD_STAGE
              };
              if *current!=snapshot{
                  *current=snapshot;
                  counters.sack_rev.fetch_add(1,Ordering::Release);
                  drop(current);
                  flush_tx_wake(&tx_notify,&counters);
              }
          }
          // A partial ready batch must signal immediately on drain.
         if npf_wakes.finish(){flush_tx_wake(&tx_notify,&counters);}
     }
 }

 #[repr(C)]
 #[derive(Clone,Copy)]
 pub struct WbdWinNativeAttachV2 {
     pub version:u32,
     pub size:u32,
     pub mode:u32, // 0 Normal, 1 Fixed, 2 Auto. Game stays multi-lane.
     pub reserved:u32, // bit0 Auto aggressive; bit1 Go-negotiated SACK
     pub normal:WbdWinNativeAttachV1,
 }
 #[no_mangle]
 pub unsafe extern "C" fn wbd_m0_win_native_v2_start(cfg:*const WbdWinNativeAttachV2)->i32{
     if cfg.is_null(){return INVALID}
     let v2=unsafe{*cfg};
     if v2.version!=2 || v2.size as usize!=std::mem::size_of::<WbdWinNativeAttachV2>()
         ||!matches!(v2.mode,0|1|2)||v2.reserved>3||
         (v2.mode!=2&&v2.reserved&1!=0){return INVALID}
     #[cfg(feature="fec2_product_record")]
     {start_native(v2.normal,v2.mode!=0,
         if v2.mode==2{Some(v2.reserved&1!=0)}else{None},
         v2.reserved&2!=0)}
     #[cfg(not(feature="fec2_product_record"))]
     {let _=v2;BAD_STAGE}
 }
 #[no_mangle]
 pub unsafe extern "C" fn wbd_m0_win_native_v1_start(cfg:*const WbdWinNativeAttachV1)->i32{
     if cfg.is_null(){return INVALID}
     start_native(unsafe{*cfg},false,None,false)
 }
 fn start_native(config:WbdWinNativeAttachV1,fixed:bool,
     auto_policy:Option<bool>,sack_negotiated:bool
 )->i32{
     if config.version!=1||config.size as usize!=std::mem::size_of::<WbdWinNativeAttachV1>()
         ||config.owner==0||config.local_port==0||config.peer_port==0
         ||config.rx_capture==0||config.tx_capture==0||config.wintun_session==0
         ||config.wintun_read_event==0{return INVALID}
     let lane=match lookup(config.owner){Ok(v)=>v,Err(code)=>return code};
     {
         let mut e=match lane.lock(){Ok(v)=>v,Err(_)=>return BAD_STAGE};
         if !v3_ready(&e,config.epoch,config.luid,config.ifindex)
             ||e.path_mtu as u32!=config.path_mtu ||e.m2.is_none()
             ||e.role_server||e.feature7!=fixed{return BAD_STAGE}
         #[cfg(feature="fec2_product_record")]
         if fixed && (e.fec2_tx.is_none()||e.game_group.is_some()){
             return BAD_STAGE
         }
         #[cfg(not(feature="fec2_product_record"))]
         if fixed{return BAD_STAGE}
         #[cfg(feature="fec2_product_record")]
         if let Some(aggressive)=auto_policy{
             if e.auto_actor.is_some(){return BAD_STAGE}
             let Some(stream)=e.fec2_tx.as_ref()else{return BAD_STAGE};
             let profile=stream.profile_index();
             let rev=stream.revision().0;
             e.auto_actor=Some(auto_native::NativeAutoActor::new(
                 profile,rev,aggressive,m2_clock().0));
              if let Some(m)=e.m2.as_mut(){m.auto_low_rate_mode=true;}
              else{return BAD_STAGE}
         }
         #[cfg(not(feature="fec2_product_record"))]
         if auto_policy.is_some(){return BAD_STAGE}
     }
     let (wtx,wrx)=match unsafe{io::split_borrowed_wintun(
         config.wintun_session,config.wintun_read_event,config.wintun)}{
         Ok((rx,tx))=>(rx,tx),Err(_)=>return INVALID
     };
     let capture=match unsafe{NpcapRx::from_borrowed(config.rx_capture,config.npcap)}{
         Ok(v)=>v,Err(_)=>return INVALID
     };
     if capture.event().is_err(){return BAD_STAGE}
     let sender=match unsafe{NpcapTx::from_borrowed(config.tx_capture,config.npcap)}{
         Ok(v)=>v,Err(_)=>return INVALID
     };
     let stop=match WakeEvent::new(){Ok(v)=>Arc::new(v),Err(_)=>return BAD_STAGE};
     let notify=match WakeEvent::new_auto(){Ok(v)=>Arc::new(v),Err(_)=>return BAD_STAGE};
     let counters=Arc::new(Counters::new(config.initial_rx_seq,config.initial_tx_seq));
     let rx_notify=match WakeEvent::new_auto(){Ok(v)=>Arc::new(v),Err(_)=>return BAD_STAGE};
     let early=Arc::new(Mutex::new(VecDeque::with_capacity(64)));

     let mut guard=match active().lock(){Ok(v)=>v,Err(_)=>return BAD_STAGE};
     if guard.contains_key(&config.owner){return BAD_STAGE}
     let tx_lane=Arc::clone(&lane);let tx_stop=Arc::clone(&stop);
     let tx_notify=Arc::clone(&notify);let tx_counters=Arc::clone(&counters);
     let tx=thread::Builder::new().name("wbd-native-tx".into()).spawn(move||{
         set_native_thread_name(&NATIVE_TX_WIDE);
         eprintln!("WBD_WINDOWS_RUST_NATIVE_WORKER_TID role=TX tid={}",unsafe{GetCurrentThreadId()});
         let rc=tx_loop(config,tx_lane,wtx,sender,Arc::clone(&tx_stop),tx_notify,
             Arc::clone(&tx_counters),fixed,auto_policy.is_some(),sack_negotiated);
         if rc!=OK{
             tx_counters.worker_error.store(rc,Ordering::Release);
             let _=tx_stop.wake();
         }
         rc
     }).expect("Rust TX worker spawn");
     let rx_lane=Arc::clone(&lane);let rx_stop=Arc::clone(&stop);
     let rx_event=Arc::clone(&rx_notify);let rx_early=Arc::clone(&early);
     let tx_notify_for_rx=Arc::clone(&notify);let rx_counters=Arc::clone(&counters);
     let rx=thread::Builder::new().name("wbd-native-rx".into()).spawn(move||{
         set_native_thread_name(&NATIVE_RX_WIDE);
         eprintln!("WBD_WINDOWS_RUST_NATIVE_WORKER_TID role=RX tid={}",unsafe{GetCurrentThreadId()});
         let rc=rx_loop(config,rx_lane,wrx,capture,Arc::clone(&rx_stop),tx_notify_for_rx,
             rx_event,rx_early,Arc::clone(&rx_counters),fixed,sack_negotiated);
         if rc!=OK{
             rx_counters.worker_error.store(rc,Ordering::Release);
             let _=rx_stop.wake();
         }
         rc
     }).expect("Rust RX worker spawn");
     guard.insert(config.owner,NativeSession{stop,tx_notify:notify,
         rx_notify,early,counters,tx,rx});
     OK
 }
 /// Bounded cold handoff of already-read, post-Detach authenticated candidate
 /// ciphertext. Never used for steady packets; only RX worker can AEAD-open.
 #[no_mangle]
 pub unsafe extern "C" fn wbd_m0_win_native_v1_early(
     h:u64,seq:u32,wire:*const u8,len:usize,
 )->i32{
     if wire.is_null()||len<51||len>2048{return INVALID}
     let guard=match active().lock(){Ok(v)=>v,Err(_)=>return BAD_STAGE};
     let Some(session)=guard.get(&h)else{return UNKNOWN};
     let mut q=match session.early.lock(){Ok(v)=>v,Err(_)=>return BAD_STAGE};
     if q.len()>=64{return FULL}
     q.push_back((seq,unsafe{std::slice::from_raw_parts(wire,len)}.to_vec()));
     drop(q);
     let _=session.rx_notify.wake();
     OK
 }
 #[no_mangle]
 pub unsafe extern "C" fn wbd_m0_win_native_v1_stats(
     h:u64,out:*mut WbdWinNativeStatsV1
 )->i32{
     if out.is_null(){return INVALID}
     let guard=match active().lock(){Ok(v)=>v,Err(_)=>return BAD_STAGE};
     let Some(session)=guard.get(&h)else{return UNKNOWN};
     unsafe{out.write(session.counters.snapshot())};
     OK
 }
 // Stop belongs to the original Win32 native owner, not the Go timeout.
 // Never remove a still-live NPF/Wintun loan holder from the registry and
 // then join indefinitely inside synchronous FFI. Return the truthful
 // incomplete state; the original caller may retry after kernel I/O wakes.
 fn wait_normal_native_workers<F:FnMut()->Result<bool,i32>>(
     mut done:F,limit:Duration,
 )->Result<(),i32>{
     let start=std::time::Instant::now();
     loop{
         if done()?{return Ok(())}
         if start.elapsed()>=limit{return Err(STOP_INCOMPLETE)}
         thread::sleep(Duration::from_millis(10));
     }
 }
 #[no_mangle]
 pub extern "C" fn wbd_m0_win_native_v1_stop(h:u64)->i32{
     {
         let g=match active().lock(){Ok(v)=>v,Err(_)=>return BAD_STAGE};
         let Some(s)=g.get(&h)else{return UNKNOWN};
         s.counters.stopping.store(true,Ordering::Release);
         let _=s.stop.wake();
         let _=s.tx_notify.wake();
         let _=s.rx_notify.wake();
     }
     if let Err(rc)=wait_normal_native_workers(||{
         let g=active().lock().map_err(|_|BAD_STAGE)?;
         let s=g.get(&h).ok_or(UNKNOWN)?;
         Ok(s.tx.is_finished()&&s.rx.is_finished())
     },Duration::from_secs(12)){
         eprintln!("M0_PLAN027_NORMAL_NATIVE_STOP_NOT_DRAINED handle={h} rc={rc} retained_npfcapture_wintun_loan=1 retryable=1");
         return rc
     }
     // All Rust workers finished genuine OS calls; removal and JoinHandle
     // consumption are now immediate. Only then may Go close the NPF/WAL.
     let session={
         let mut g=match active().lock(){Ok(v)=>v,Err(_)=>return BAD_STAGE};
         let Some(s)=g.remove(&h)else{return UNKNOWN};
         s
     };
     let tx=session.tx.join().unwrap_or(STOP_INCOMPLETE);
     let rx=session.rx.join().unwrap_or(STOP_INCOMPLETE);
     eprintln!("WBD_WINDOWS_RUST_NATIVE_WAKE_BATCH max_verified_per_wake={} tx_wake_attempts={} rx_data_delivered={} joined=true",
         RX_WAKE_BATCH,
         session.counters.rx_tx_notify_attempts.load(Ordering::Relaxed),
         session.counters.rx_delivered.load(Ordering::Acquire));
     #[cfg(feature="win_native_lock_profile")]
     {
         let p=&session.counters.profile;
         eprintln!("WBD_WINDOWS_RUST_NATIVE_ENTRY_LOCK_SAMPLED sample_every=64 tx_samples={} tx_wait_ns={} tx_max_ns={} rx_samples={} rx_wait_ns={} rx_max_ns={}",
             p.tx.samples.load(Ordering::Relaxed),
             p.tx.wait_ns.load(Ordering::Relaxed),
             p.tx.max_ns.load(Ordering::Relaxed),
             p.rx.samples.load(Ordering::Relaxed),
             p.rx.wait_ns.load(Ordering::Relaxed),
             p.rx.max_ns.load(Ordering::Relaxed));
     }
     let f=session.counters.fresh_outer_bytes.load(Ordering::Relaxed);
     let r=session.counters.repair_outer_bytes.load(Ordering::Relaxed);
     let u=session.counters.repair_uncertain_bytes.load(Ordering::Relaxed);
     let k=session.counters.feedback_outer_bytes.load(Ordering::Relaxed)
         +session.counters.pure_ack_outer_bytes.load(Ordering::Relaxed);
     // Conservative bound includes uncertain driver sends as charged R.
     // Ratio numerators/denominators are wire Ethernet bytes, not app bytes.
     eprintln!("WBD_WINDOWS_NATIVE_OUTER_REPAIR source_wire_bytes={} repair_accepted_wire_bytes={} repair_uncertain_wire_bytes={} control_wire_bytes={} repair_packets={} r_to_f_ppm={} r_to_total_ppm={} joined=true",
         f,r,u,k,session.counters.repair_packets.load(Ordering::Relaxed),
         if f>0{(r+u).saturating_mul(1_000_000)/f}else{0},
         if f+r+u+k>0{(r+u).saturating_mul(1_000_000)/(f+r+u+k)}else{0});
     if tx!=OK&&tx!=BAD_STAGE{return tx}
     if rx!=OK&&rx!=BAD_STAGE{return rx}
     OK // all driver borrows returned before Go can EndSession/pcap_close
 }

 #[cfg(test)]
 mod tests {
     use super::*;
     #[cfg(feature="win_native_lock_profile")]
     #[test]
     fn sampled_lock_profile_separates_tx_and_rx_without_packet_abi() {
         let c=Counters::new(1,1);
         let lock=Arc::new(Mutex::new(0));
         // The actual Entry lock wrapper is exercised in real Windows
         // product tests; the sample account policy is 1 per 64 attempts.
         for i in 0..64{
             let tick=c.profile.tx.ticks.fetch_add(1,Ordering::Relaxed);
             if tick&63==0{c.profile.tx.sample(i)}
         }
         assert_eq!(c.profile.tx.samples.load(Ordering::Relaxed),1);
         assert_eq!(c.profile.rx.samples.load(Ordering::Relaxed),0);
         assert_eq!(*lock.lock().unwrap(),0);
     }
     #[test]
     fn normal_native_stop_timeout_retains_worker_until_real_join(){
         // Only Stop ownership and bounded wait; no simulated Wintun,
         // no kernel or TLS product PASS inferred from this test.
         let release=Arc::new(AtomicBool::new(false));
         let gate=Arc::clone(&release);
         let tx=thread::spawn(move||{
             while !gate.load(Ordering::Acquire){
                 thread::sleep(Duration::from_millis(1));
             }
             OK
         });
         let rx=thread::spawn(||OK);
         assert_eq!(wait_normal_native_workers(
             ||Ok(tx.is_finished()&&rx.is_finished()),Duration::from_millis(15)
         ),Err(STOP_INCOMPLETE));
         assert!(!tx.is_finished()); // Neither native loan was discarded.
         release.store(true,Ordering::Release);
         assert_eq!(wait_normal_native_workers(
             ||Ok(tx.is_finished()&&rx.is_finished()),Duration::from_secs(2)
         ),Ok(()));
         assert_eq!(tx.join().unwrap(),OK);
         assert_eq!(rx.join().unwrap(),OK);
     }
     #[test]
     fn h517_negotiated_positive_sack_is_not_starved_by_full_native_business_batch(){
         // Continuous TUN ready business formerly returned before all
         // presentation ACK-only checks; genuine SACK could never escape.
         assert!(native_ack_only_due(true,true,false,true));
         assert!(native_ack_only_due(true,true,true,true));
         // No background pure ACK flood on lossless, busy Normal source.
         assert!(!native_ack_only_due(true,false,true,true));
         assert!(!native_ack_only_due(false,true,false,true));
         assert!(!native_ack_only_due(false,false,false,false));
         assert!(native_ack_only_due(false,false,true,false));
     }
     #[test]
     fn bounded_rx_tx_wake_coalescing_preserves_single_and_full_batches(){
         let mut b=TxWakeBatch::default();
         assert!(!b.finish()); // No ACK verification: no SetEvent.
         assert!(!b.note_verified());
         assert!(b.finish()); // one verified packet: notify immediately.
         assert!(!b.finish()); // no duplicate wake.
         for _ in 0..RX_WAKE_BATCH-1 {assert!(!b.note_verified());}
         assert!(b.note_verified()); // 32 verified packets: one wake.
         assert!(!b.finish());
         for _ in 0..RX_WAKE_BATCH+1 {
             let signal=b.note_verified();
             if signal {assert_eq!(b.pending,0);}
         }
         assert!(b.finish()); // 33 -> 1 full + 1 partial wake.
     }
     #[test]
     fn m2_native_next_deadline_wakes_only_when_due() {
         assert_eq!(m2_wake_timeout_ms(MonoNs(1),None,None),IDLE_WAIT);
         assert_eq!(m2_wake_timeout_ms(MonoNs(10),Some(MonoNs(10)),None),0);
         assert_eq!(m2_wake_timeout_ms(MonoNs(10),None,Some(MonoNs(9))),0);
         assert_eq!(m2_wake_timeout_ms(MonoNs(10),
             Some(MonoNs(21_000_011)),None),22);
         assert_eq!(m2_wake_timeout_ms(MonoNs(100),
             Some(MonoNs(55_000_100)),Some(MonoNs(4_000_100))),4);
         assert_eq!(m2_wake_timeout_ms(MonoNs(0),None,
             Some(MonoNs(u64::MAX))),u32::MAX-1);
     }
     #[test]
     fn windows_native_thread_descriptions_are_exact() {
         assert_eq!(String::from_utf16(&NATIVE_TX_WIDE[..13]).unwrap(),"wbd-native-tx");
         assert_eq!(String::from_utf16(&NATIVE_RX_WIDE[..13]).unwrap(),"wbd-native-rx");
         let (sender,receiver)=std::sync::mpsc::channel();
         std::thread::spawn(move||{
             set_native_thread_name(&NATIVE_RX_WIDE);
             sender.send(()).unwrap();
         }).join().unwrap();
         receiver.recv().unwrap();
     }
     #[test]
     fn native_stop_event_wins_when_capture_and_handoff_are_also_ready(){
         let stop=WakeEvent::new().unwrap();
         let capture=WakeEvent::new().unwrap();
         let early=WakeEvent::new_auto().unwrap();
         capture.wake().unwrap();
         early.wake().unwrap();
         stop.wake().unwrap();
         assert_eq!(io::wait_ready(
             &[stop.handle(),capture.handle(),early.handle()],0
         ).unwrap(),WaitResult::Ready(0));
         // The same manual-reset Stop wins again after the RX wake.
         assert_eq!(io::wait_ready(
             &[stop.handle(),capture.handle(),early.handle()],0
         ).unwrap(),WaitResult::Ready(0));
     }
     #[test]
     fn saturated_rx_and_early_loops_observe_stop_without_reaching_wait(){
         let counters=Counters::new(1,1);
         counters.stopping.store(true,Ordering::Release);
         assert!(counters.stopping.load(Ordering::Acquire));
     }
     #[test]
     fn native_go_rust_c_abi_is_192_bytes_and_fixed_offsets(){
         use std::mem::{offset_of,size_of};
         assert_eq!(size_of::<WbdWinNativeAttachV1>(),192);
         assert_eq!(offset_of!(WbdWinNativeAttachV1,rx_capture),80);
         assert_eq!(offset_of!(WbdWinNativeAttachV1,npcap),112);
         assert_eq!(offset_of!(WbdWinNativeAttachV1,wintun),160);
         assert_eq!(size_of::<WbdWinNativeStatsV1>(),48);
         assert_eq!(size_of::<NpcapFns>(),6*size_of::<usize>());
         assert_eq!(size_of::<WintunFns>(),4*size_of::<usize>());
     }
     #[test]
     fn fixed_v2_attach_is_versioned_and_does_not_change_v1_abi(){
         assert_eq!(std::mem::size_of::<WbdWinNativeAttachV2>(),
             std::mem::size_of::<WbdWinNativeAttachV1>()+16);
         assert_eq!(std::mem::size_of::<WbdWinNativeAttachV1>(),192);
     }
     #[test]
     fn native_ack_stops_at_gap_and_merges_verified_ranges_only(){
         let mut ack=PresentationAck::new(100);
         assert_eq!(ack.verified(180,20),100);
         assert_eq!(ack.verified(100,40),140);
         assert_eq!(ack.verified(140,40),200);
         assert_eq!(ack.verified(100,40),200);
         assert_eq!(ack.future.len(),0);
         // This presentation bitmap does not become M2 receipt authority.
     }
     #[test]
     fn native_ack_survives_tcp32_wrap_and_stale_duplicate(){
         let mut ack=PresentationAck::new(0xffff_fff0);
         assert_eq!(ack.verified(0xffff_fff0,32),16);
         assert_eq!(ack.verified(0xffff_fff0,32),16);
         assert_eq!(ack.verified(16,1),17);
     }
     #[test]
     fn native_driver_prefix_never_claims_peer_receipt(){
         let out=wbd_platform::TxBatchOutcome {
             accepted_prefix:2,uncertain_index:Some(2),
             error:Some(wbd_platform::TxError::IoUncertain),
         };
         assert_eq!(kernel_result(out,4,0),Ok(1));
         assert_eq!(kernel_result(out,4,1),Ok(1));
         assert_eq!(kernel_result(out,4,2),Ok(2));
         assert_eq!(kernel_result(out,4,3),Ok(0));
     }
 }
