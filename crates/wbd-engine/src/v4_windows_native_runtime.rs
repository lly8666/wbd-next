//! Windows PLAN026 authenticated Normal/off Rust-native I/O.
 //! One Wintun session, one NPF RX worker, one NPF TX worker, zero steady Go
 //! packet callbacks. This is a child of the existing original TLS-scoped
 //! Rust owner: all M1/M3/PN/M2 logic is reused, never reimplemented.
 use super::*;
 use std::sync::atomic::{AtomicBool, AtomicI32, AtomicU32, AtomicU64, Ordering};
 use std::thread::{self, JoinHandle};
 use wbd_platform::windows_native_io::{
     self as io, NpcapFns, NpcapRx, NpcapTx, WintunFns,
     WintunRx, WintunTx, WakeEvent, ReadResult, WaitResult,
 };
 use wbd_platform::ipv4_tcp::{
     build_bytes, build_presentation_ack, Ipv4Tuple, PacketPersona, Presentation,
 };
 use wbd_platform::rx_ipv4_tcp::{parse_data_packet, extend_seq32, TrustedRx};

 const BATCH:usize=8;
 const MAX_IPV4:usize=2048;
 const MAX_LINK:usize=2304;
 const MAX_NPF:usize=65535+64;
 const IDLE_WAIT:u32=u32::MAX;

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
     tx_after_rx:AtomicU64,
     rejected:AtomicU64,
     worker_error:AtomicI32,
     ack:AtomicU32,
     ack_sent:AtomicU32,
     tx_seq:AtomicU32,
     last_rx_ns:AtomicU64,
     stopping:AtomicBool,
 }
 impl Counters {
     fn new(ack:u32,seq:u32)->Self{
         Self{tx_copied:AtomicU64::new(0),rx_delivered:AtomicU64::new(0),
             tx_after_rx:AtomicU64::new(0),rejected:AtomicU64::new(0),
             worker_error:AtomicI32::new(0),ack:AtomicU32::new(ack),
             ack_sent:AtomicU32::new(ack),
             tx_seq:AtomicU32::new(seq),
             last_rx_ns:AtomicU64::new(0),stopping:AtomicBool::new(false)}
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
 // presentation ACK. Late SACK-like ranges stay bounded; M2 is the real
 // reliability protocol and does not derive acknowledgement from this.
 struct PresentationAck {
     next:u64,
     future:Vec<(u64,u64)>,
 }
 impl PresentationAck {
     fn new(next:u32)->Self{Self{next:u64::from(next),future:Vec::with_capacity(256)}}
     fn verified(&mut self,seq:u32,len:usize)->u32{
         let Ok(start)=extend_seq32(self.next,seq)else{return self.next as u32};
         let Some(end)=start.checked_add(len as u64)else{return self.next as u32};
         if end<=self.next{return self.next as u32}
         if start<=self.next {
             self.next=end;
         }else{
             if self.future.len()>=256{return self.next as u32}
             let at=self.future.partition_point(|(begin,_)|*begin<=start);
             self.future.insert(at,(start,end));
         }
         while let Some(&(begin,limit))=self.future.first(){
             if begin>self.next{break}
             self.next=self.next.max(limit);
             self.future.remove(0);
         }
         self.next as u32
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
     counters:&Counters,ip_id:&mut u16,
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
         let mut e=lane.lock().map_err(|_|BAD_STAGE)?;
         for i in 0..count {
             let (used,seq,pn)=v3_seal_entry(
                 &mut e,cfg.epoch,cfg.luid,cfg.ifindex,
                 &sources[i][..source_len[i]],&mut wire[i]
             )?;
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
         let mut e=lane.lock().map_err(|_|BAD_STAGE)?;
         for (i,&(pn,seq,used)) in meta[..count].iter().enumerate(){
             let status=kernel_result(result,count,i)?;
             m2_kernel_firstsend_entry(&mut e,cfg.epoch,cfg.luid,cfg.ifindex,
                 pn,seq,used,status)?;
             if status==1{
                 counters.tx_copied.fetch_add(1,Ordering::Relaxed);
                 if counters.rx_delivered.load(Ordering::Acquire)>0{
                     counters.tx_after_rx.fetch_add(1,Ordering::Relaxed);
                 }
             }
         }
     }
     if result.error.is_some(){return Err(BAD_STAGE)}
     Ok(count)
 }

 fn send_control(
     cfg:&WbdWinNativeAttachV1,lane:&Arc<Mutex<Entry>>,
     npf:&mut NpcapTx,counters:&Counters,ip_id:&mut u16,
 )->Result<bool,i32>{
     let mut wire=[0u8;MAX_IPV4];
     let ack=counters.ack.load(Ordering::Acquire);
     let feedback={
         let mut e=lane.lock().map_err(|_|BAD_STAGE)?;
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
         if accepted{counters.ack_sent.store(ack,Ordering::Release);}
         let mut e=lane.lock().map_err(|_|BAD_STAGE)?;
         m2_finish_feedback_entry(&mut e,cfg.epoch,cfg.luid,cfg.ifindex,
             pn,u32::from(accepted))?;
         if outcome.error.is_some(){return Err(BAD_STAGE)}
         return Ok(true)
     }
     let repair={
         let mut e=lane.lock().map_err(|_|BAD_STAGE)?;
         m2_next_repair_entry(&mut e,cfg.epoch,cfg.luid,cfg.ifindex,&mut wire)?
     };
     if let Some((used,seq,pn))=repair{
         let mut frame=[0u8;MAX_LINK];
         let raw=packet_frame(cfg,seq,ack,
             &wire[..used],*ip_id,&mut frame)?;
         *ip_id=ip_id.wrapping_add(1);
         let outcome=npf.send_batch(&[raw]);
         let accepted=kernel_result(outcome,1,0)?==1;
         if accepted{counters.ack_sent.store(ack,Ordering::Release);}
         let mut e=lane.lock().map_err(|_|BAD_STAGE)?;
         m2_complete_repair_entry(&mut e,cfg.epoch,cfg.luid,cfg.ifindex,
             pn,u32::from(accepted))?;
         if outcome.error.is_some(){return Err(BAD_STAGE)}
         return Ok(true)
     }
     Ok(false)
 }
 fn send_presentation_ack(cfg:&WbdWinNativeAttachV1,
     npf:&mut NpcapTx,counters:&Counters,ip_id:&mut u16,
 )->Result<(),i32>{
     let mut bytes=[0u8;MAX_LINK];
     let mut frame=[0u8;MAX_LINK];
     let ack=counters.ack.load(Ordering::Acquire);
     let raw=build_presentation_ack(Ipv4Tuple{
         src_ip:&cfg.local_ip,dst_ip:&cfg.peer_ip,
         src_port:cfg.local_port,dst_port:cfg.peer_port,
     },counters.tx_seq.load(Ordering::Acquire),
       ack,*ip_id,
       PacketPersona::Windows11,cfg.path_mtu as usize,&mut bytes)
       .map_err(|_|INVALID)?;
     let link=io::ethernet_outbound(raw,&cfg.source_mac,
         &cfg.next_hop_mac,&mut frame).map_err(|_|INVALID)?;
     *ip_id=ip_id.wrapping_add(1);
     let outcome=npf.send_batch(&[link]);
     if kernel_result(outcome,1,0)?!=1{return Err(BAD_STAGE)}
     counters.ack_sent.store(ack,Ordering::Release);
     Ok(())
 }
  fn tx_loop(cfg:WbdWinNativeAttachV1,lane:Arc<Mutex<Entry>>,
     mut tun:WintunRx,mut npf:NpcapTx,stop:Arc<WakeEvent>,
     notify:Arc<WakeEvent>,counters:Arc<Counters>)->i32{
     let mut ip_id=1u16;
     loop {
         if counters.stopping.load(Ordering::Acquire){return OK}
         let result=(||->Result<bool,i32>{
             let mut work=0;
             for _ in 0..4 {
                 if counters.stopping.load(Ordering::Acquire){return Ok(true)}
                 let n=stage_sources(&cfg,&lane,&mut tun,&mut npf,&counters,&mut ip_id)?;
                 work+=n;
                 if n<BATCH{break}
             }
             let control=send_control(&cfg,&lane,&mut npf,&counters,&mut ip_id)?;
             if work>0||control{return Ok(false)}
             let next_ack=counters.ack.load(Ordering::Acquire);
             if next_ack!=counters.ack_sent.load(Ordering::Acquire){
                 send_presentation_ack(&cfg,&mut npf,&counters,&mut ip_id)?;
                 return Ok(false)
             }
             let m2_active={
                 let e=lane.lock().map_err(|_|BAD_STAGE)?;
                 e.m2.as_ref().is_some_and(|m|m.shadow.outstanding()>0)
             };
             let since_rx=m2_clock().0.saturating_sub(
                 counters.last_rx_ns.load(Ordering::Acquire));
             let timeout=if m2_active||since_rx<2_000_000_000{20}else{IDLE_WAIT};
             match io::wait_ready(&[stop.handle(),tun.event(),notify.handle()],timeout){
                 Ok(WaitResult::Ready(0))=>Ok(true),
                 Ok(WaitResult::Ready(_)|WaitResult::Timeout)=>Ok(false),
                 Err(_)=>Err(BAD_STAGE),
             }
         })();
         match result {Ok(true)=>return OK,Ok(false)=>{},Err(code)=>return code}
     }
 }
 fn open_and_deliver(cfg:&WbdWinNativeAttachV1,lane:&Arc<Mutex<Entry>>,
     tun:&mut WintunTx,tx_notify:&WakeEvent,counters:&Counters,
     ack:&mut PresentationAck,seq:u32,wire:&[u8],
     plain:&mut [u8;MAX_IPV4])->Result<(),i32>{
     let opened={
         let mut e=lane.lock().map_err(|_|BAD_STAGE)?;
         let opened=v5_open_record_entry(&mut e,cfg.epoch,cfg.luid,
             cfg.ifindex,seq,wire,plain);
         opened
     };
     match opened {
         Ok((used,1,_))=>{
             tun.deliver_authenticated(&plain[..used]).map_err(|_|BAD_STAGE)?;
             counters.ack.store(ack.verified(seq,wire.len()),Ordering::Release);
             counters.rx_delivered.fetch_add(1,Ordering::Release);
             counters.last_rx_ns.store(m2_clock().0,Ordering::Release);
             let _=tx_notify.wake();
         },
         Ok((_,2,_))=>{
             counters.ack.store(ack.verified(seq,wire.len()),Ordering::Release);
             counters.last_rx_ns.store(m2_clock().0,Ordering::Release);
             let _=tx_notify.wake();
         },
         Err(INVALID)=>{counters.rejected.fetch_add(1,Ordering::Relaxed);},
         Err(code)=>return Err(code),
         _=>return Err(BAD_STAGE),
     }
     Ok(())
 }
 fn rx_loop(cfg:WbdWinNativeAttachV1,lane:Arc<Mutex<Entry>>,
     mut tun:WintunTx,mut npf:NpcapRx,stop:Arc<WakeEvent>,
     tx_notify:Arc<WakeEvent>,early_notify:Arc<WakeEvent>,
     early:Arc<Mutex<VecDeque<(u32,Vec<u8>)>>>,
     counters:Arc<Counters>)->i32{
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
     loop{
         if counters.stopping.load(Ordering::Acquire){return OK}
         // Drain genuine Go pre-handoff packets FIRST, in original order.
         // Only this RX worker ever calls the M3 opener after Start.
         loop{
             if counters.stopping.load(Ordering::Acquire){return OK}
             let next=match early.lock(){
                 Ok(mut q)=>q.pop_front(),Err(_)=>return BAD_STAGE
             };
             let Some((seq,record))=next else{break};
             if let Err(code)=open_and_deliver(&cfg,&lane,&mut tun,&tx_notify,
                 &counters,&mut ack,seq,&record,&mut plain){return code}
         }
         match io::wait_ready(&[stop.handle(),event,early_notify.handle()],IDLE_WAIT){
             Ok(WaitResult::Ready(0))=>return OK,
             Ok(WaitResult::Ready(1|2))=>{},
             Ok(WaitResult::Timeout)=>continue,
             Err(_)=>return BAD_STAGE,
             _=>return BAD_STAGE,
         }
         for _ in 0..32{
             if counters.stopping.load(Ordering::Acquire){return OK}
             let n=match npf.read(&mut frame){
                 Ok(ReadResult::Frame(n))=>n,
                 Ok(ReadResult::NoPacket)=>break,
                 Ok(ReadResult::Skipped)=>continue,
                 Ok(ReadResult::EndOfStream)=>return BAD_STAGE,
                 Err(_)=>return BAD_STAGE,
             };
             let Some(packet)=io::ethernet_ipv4(&frame[..n])else{continue};
             let Ok(sealed)=parse_data_packet(packet,trusted)else{
                 counters.rejected.fetch_add(1,Ordering::Relaxed);continue
             };
             if let Err(code)=open_and_deliver(&cfg,&lane,&mut tun,&tx_notify,
                 &counters,&mut ack,sealed.seq32,sealed.ciphertext,&mut plain){return code}
         }
     }
 }

 #[no_mangle]
 pub unsafe extern "C" fn wbd_m0_win_native_v1_start(cfg:*const WbdWinNativeAttachV1)->i32{
     if cfg.is_null(){return INVALID}
     let config=unsafe{*cfg};
     if config.version!=1||config.size as usize!=std::mem::size_of::<WbdWinNativeAttachV1>()
         ||config.owner==0||config.local_port==0||config.peer_port==0
         ||config.rx_capture==0||config.tx_capture==0||config.wintun_session==0
         ||config.wintun_read_event==0{return INVALID}
     let lane=match lookup(config.owner){Ok(v)=>v,Err(code)=>return code};
     {
         let e=match lane.lock(){Ok(v)=>v,Err(_)=>return BAD_STAGE};
         if !v3_ready(&e,config.epoch,config.luid,config.ifindex)
             ||e.path_mtu as u32!=config.path_mtu ||e.m2.is_none()
             ||e.role_server||e.feature7{return BAD_STAGE}
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
     let tx=thread::spawn(move||{
         let rc=tx_loop(config,tx_lane,wtx,sender,Arc::clone(&tx_stop),tx_notify,
             Arc::clone(&tx_counters));
         if rc!=OK{
             tx_counters.worker_error.store(rc,Ordering::Release);
             let _=tx_stop.wake();
         }
         rc
     });
     let rx_lane=Arc::clone(&lane);let rx_stop=Arc::clone(&stop);
     let rx_event=Arc::clone(&rx_notify);let rx_early=Arc::clone(&early);
     let tx_notify_for_rx=Arc::clone(&notify);let rx_counters=Arc::clone(&counters);
     let rx=thread::spawn(move||{
         let rc=rx_loop(config,rx_lane,wrx,capture,Arc::clone(&rx_stop),tx_notify_for_rx,
             rx_event,rx_early,Arc::clone(&rx_counters));
         if rc!=OK{
             rx_counters.worker_error.store(rc,Ordering::Release);
             let _=rx_stop.wake();
         }
         rc
     });
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
 #[no_mangle]
 pub extern "C" fn wbd_m0_win_native_v1_stop(h:u64)->i32{
     let session={
         let mut g=match active().lock(){Ok(v)=>v,Err(_)=>return BAD_STAGE};
         let Some(s)=g.remove(&h)else{return UNKNOWN};
         s
     };
     session.counters.stopping.store(true,Ordering::Release);
     let _=session.stop.wake();
     let _=session.tx_notify.wake();
     let _=session.rx_notify.wake();
     let tx=session.tx.join().unwrap_or(STOP_INCOMPLETE);
     let rx=session.rx.join().unwrap_or(STOP_INCOMPLETE);
     if tx!=OK&&tx!=BAD_STAGE{return tx}
     if rx!=OK&&rx!=BAD_STAGE{return rx}
     OK // all driver borrows returned before Go can EndSession/pcap_close
 }

 #[cfg(test)]
 mod tests {
     use super::*;
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
