"""Apply H2476 to a temporary frozen Windows build checkout."""
import hashlib,json,pathlib,sys
CHANGES=[
  [
    "crates/wbd-platform/src/windows_native_io.rs",
    "pub struct NpcapRx {",
    "pub enum BorrowedNpcapRead<'a> {\n    Frame(&'a [u8]), NoPacket, Skipped, EndOfStream,\n}\npub struct NpcapRx {"
  ],
  [
    "crates/wbd-platform/src/windows_native_io.rs",
    "    /// One ready packet maximum. Copies only caplen",
    "    /// Temporary capture loan, tied to the exclusive mutable RX handle.\n    /// No subsequent next_ex call is possible while the slice is borrowed.\n    pub fn read_borrowed(&mut self) -> Result<BorrowedNpcapRead<'_>, NativeIoError> {\n        let mut header: *const PcapHeader = ptr::null();\n        let mut frame: *const u8 = ptr::null();\n        let rc = unsafe { (self.fns.next_ex)(self.handle.as_ptr(), &mut header, &mut frame) };\n        match rc {\n            0 => Ok(BorrowedNpcapRead::NoPacket),\n            -2 => Ok(BorrowedNpcapRead::EndOfStream),\n            1 => {\n                if header.is_null() || frame.is_null() { return Ok(BorrowedNpcapRead::Skipped); }\n                let meta = unsafe { &*header };\n                let len = meta.caplen as usize;\n                if len == 0 || len > MAX_NPF_FRAME || meta.caplen > meta.len {\n                    return Ok(BorrowedNpcapRead::Skipped);\n                }\n                // Same validated driver loan as read(); this reference cannot outlive\n                // the exclusive mutable borrow or be retained by the caller.\n                Ok(BorrowedNpcapRead::Frame(unsafe { std::slice::from_raw_parts(frame, len) }))\n            }\n            _ => Err(NativeIoError::CaptureFailed),\n        }\n    }\n    /// One ready packet maximum. Copies only caplen"
  ],
  [
    "crates/wbd-platform/src/windows_native_io.rs",
    "    static SEND_CALLS: AtomicUsize = AtomicUsize::new(0);",
    "    #[test]\n    fn h2476_borrowed_capture_matches_owned_bytes() {\n        let fns = NpcapFns {next_ex,send_packet,get_event,queue_alloc:None,queue_transmit:None,queue_destroy:None};\n        let mut rx = unsafe { NpcapRx::from_borrowed(1,fns).unwrap() };\n        let mut dst=[0u8;64];\n        assert_eq!(rx.read(&mut dst),Ok(ReadResult::Frame(20)));\n        match rx.read_borrowed().unwrap() {\n            BorrowedNpcapRead::Frame(frame)=>assert_eq!(frame,&dst[..20]),\n            _=>panic!(\"expected frame\"),\n        }\n        assert_eq!(rx.read(&mut dst),Ok(ReadResult::Frame(20)));\n    }\n    static SEND_CALLS: AtomicUsize = AtomicUsize::new(0);"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    " fn open_and_deliver(cfg:",
    " #[derive(Default)]\n struct H2476RxCost {\n     borrowed:bool, reads:u64, frames:u64, turns:u64, full:u64,\n     read_samples:u64, read_ns:u64, read_bytes:u64,\n     open_samples:u64, open_ns:u64, wintun_samples:u64, wintun_ns:u64,\n }\n impl Drop for H2476RxCost {\n     fn drop(&mut self){\n         eprintln!(\"H2476_RX_COST borrowed={} reads={} frames={} turns={} full={} read_samples={} read_ns={} read_bytes={} open_samples={} open_ns={} wintun_samples={} wintun_ns={}\",\n             u8::from(self.borrowed),self.reads,self.frames,self.turns,self.full,self.read_samples,self.read_ns,self.read_bytes,\n             self.open_samples,self.open_ns,self.wintun_samples,self.wintun_ns);\n     }\n }\n fn open_and_deliver(cfg:"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "     tunnel_dns:Option<&Arc<Mutex<TunnelDnsMap>>>)->Result<bool,i32>{",
    "     tunnel_dns:Option<&Arc<Mutex<TunnelDnsMap>>>,sample_delivery:Option<&mut H2476RxCost>)->Result<bool,i32>{"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "                 tun.deliver_authenticated(&plain[..used]).map_err(|_|BAD_STAGE)?;",
    "                 let started=sample_delivery.as_ref().map(|_|Instant::now());\n                 let result=tun.deliver_authenticated(&plain[..used]);\n                 if let (Some(t),Some(p))=(started,sample_delivery){\n                     p.wintun_samples+=1;p.wintun_ns+=t.elapsed().as_nanos() as u64;\n                 }\n                 result.map_err(|_|BAD_STAGE)?;"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "     let mut boundary_rx=BoundaryQpcTrace::new(\"RX_WINTUN_SEND\");",
    "     let mut boundary_rx=BoundaryQpcTrace::new(\"RX_WINTUN_SEND\");\n     let borrowed=std::env::var(\"WBD_H2476_RX_BORROW\").ok().as_deref()==Some(\"1\");\n     eprintln!(\"H2476_RX_MODE borrowed={}\",u8::from(borrowed));\n     let mut costs=H2476RxCost::default();costs.borrowed=borrowed;"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "                 &counters,&mut ack,seq,&record,&mut plain,fixed,\n                 tunnel_dns.as_ref()){",
    "                 &counters,&mut ack,seq,&record,&mut plain,fixed,\n                 tunnel_dns.as_ref(),None){"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "         for _ in 0..RX_WAKE_BATCH{\n             if counters.stopping.load(Ordering::Acquire){return OK}\n             let n=match npf.read(&mut frame){\n                 Ok(ReadResult::Frame(n))=>n,\n                 Ok(ReadResult::NoPacket)=>break,\n                 Ok(ReadResult::Skipped|ReadResult::SkippedIpv6)=>continue,\n                 Ok(ReadResult::EndOfStream)=>return BAD_STAGE,\n                 Err(_)=>return BAD_STAGE,\n             };\n             let Some(packet)=io::ethernet_ipv4(&frame[..n])else{continue};",
    "         costs.turns+=1;\n         let mut full=true;\n         for _ in 0..RX_WAKE_BATCH{\n             if counters.stopping.load(Ordering::Acquire){return OK}\n             costs.reads+=1;\n             let sampled=costs.reads&255==0;\n             let started=sampled.then(Instant::now);\n             use io::BorrowedNpcapRead as Loan;\n             let received=if borrowed{npf.read_borrowed()}else{\n                 match npf.read(&mut frame){\n                     Ok(ReadResult::Frame(n))=>Ok(Loan::Frame(&frame[..n])),\n                     Ok(ReadResult::NoPacket)=>Ok(Loan::NoPacket),\n                     Ok(ReadResult::Skipped|ReadResult::SkippedIpv6)=>Ok(Loan::Skipped),\n                     Ok(ReadResult::EndOfStream)=>Ok(Loan::EndOfStream),\n                     Err(e)=>Err(e),\n                 }\n             };\n             let bytes=match received{\n                 Ok(Loan::Frame(bytes))=>bytes,\n                 Ok(Loan::NoPacket)=>{full=false;break},\n                 Ok(Loan::Skipped)=>continue,\n                 _=>return BAD_STAGE,\n             };\n             costs.frames+=1;\n             if let Some(t)=started{\n                 costs.read_samples+=1;costs.read_ns+=t.elapsed().as_nanos() as u64;\n                 costs.read_bytes+=bytes.len() as u64;\n             }\n             let Some(packet)=io::ethernet_ipv4(bytes)else{continue};"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "             let verified=match open_and_deliver(&cfg,&lane,&mut tun,\n                 &counters,&mut ack,sealed.seq32,sealed.ciphertext,&mut plain,fixed,\n                 tunnel_dns.as_ref()){\n                 Ok(v)=>v,Err(code)=>return code\n             };",
    "             let started=sampled.then(Instant::now);\n             let verified=match open_and_deliver(&cfg,&lane,&mut tun,\n                 &counters,&mut ack,sealed.seq32,sealed.ciphertext,&mut plain,fixed,\n                 tunnel_dns.as_ref(),if sampled{Some(&mut costs)}else{None}){\n                 Ok(v)=>v,Err(code)=>return code\n             };\n             if let Some(t)=started{\n                 costs.open_samples+=1;costs.open_ns+=t.elapsed().as_nanos() as u64;\n             }"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "          // Advance only on a genuine authenticated RX ready batch; this",
    "          if full{costs.full+=1;}\n          // Advance only on a genuine authenticated RX ready batch; this"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "     borrowed:bool, reads:u64, frames:u64, turns:u64, full:u64,",
    "     borrowed:bool, continuation:bool, reads:u64, frames:u64, turns:u64, full:u64,\n     waits:u64, bypass:u64, bypass_empty:u64, owner_offer_ns:u64, owner_drain_ns:u64, owner_finish_ns:u64, owner_samples:u64,"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "H2476_RX_COST borrowed={} reads={} frames={} turns={} full={} read_samples={} read_ns={} read_bytes={} open_samples={} open_ns={} wintun_samples={} wintun_ns={}",
    "H2476_RX_COST borrowed={} reads={} frames={} turns={} full={} read_samples={} read_ns={} read_bytes={} open_samples={} open_ns={} wintun_samples={} wintun_ns={} continuation={} waits={} bypass={} bypass_empty={} owner_offer_ns={} owner_drain_ns={} owner_finish_ns={} owner_samples={}"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "self.open_samples,self.open_ns,self.wintun_samples,self.wintun_ns);",
    "self.open_samples,self.open_ns,self.wintun_samples,self.wintun_ns,u8::from(self.continuation),self.waits,self.bypass,self.bypass_empty,self.owner_offer_ns,self.owner_drain_ns,self.owner_finish_ns,self.owner_samples);"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "     let mut costs=H2476RxCost::default();costs.borrowed=borrowed;",
    "     let mut costs=H2476RxCost::default();costs.borrowed=borrowed;\n     costs.continuation=std::env::var(\"WBD_H2477_RX_CONTINUE\").ok().as_deref()==Some(\"1\");\n     let mut previous_full=false;"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "         match io::wait_ready(&[stop.handle(),event,early_notify.handle()],wait_ms){\n             Ok(WaitResult::Ready(0))=>return OK,\n             Ok(WaitResult::Ready(1|2))=>{},\n             Ok(WaitResult::Timeout)=>continue,\n             Err(_)=>return BAD_STAGE,\n             _=>return BAD_STAGE,\n         }",
    "         let bypass=costs.continuation&&previous_full&&deferred_direct_tcp.is_none();\n         previous_full=false;\n         if bypass{costs.bypass+=1;}else{\n             costs.waits+=1;\n             match io::wait_ready(&[stop.handle(),event,early_notify.handle()],wait_ms){\n                 Ok(WaitResult::Ready(0))=>return OK,\n                 Ok(WaitResult::Ready(1|2))=>{},\n                 Ok(WaitResult::Timeout)=>continue,\n                 Err(_)=>return BAD_STAGE,\n                 _=>return BAD_STAGE,\n             }\n         }"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "          if full{costs.full+=1;}",
    "          if full{costs.full+=1;}else if bypass{costs.bypass_empty+=1;}\n          previous_full=full;"
  ],
  [
    "crates/wbd-engine/src/v4_windows_owner.rs",
    "fn v5_open_record_entry(e:&mut Entry,epoch:[u8;16],luid:u64,\n    ifindex:u32,seq:u32,wire:&[u8],out:&mut [u8]\n)->Result<(usize,u32,u64),i32>{",
    "fn v5_open_record_entry(e:&mut Entry,epoch:[u8;16],luid:u64,\n    ifindex:u32,seq:u32,wire:&[u8],out:&mut [u8]\n)->Result<(usize,u32,u64),i32>{\n    v5_open_record_entry_sampled(e,epoch,luid,ifindex,seq,wire,out,None)\n}\nfn v5_open_record_entry_sampled(e:&mut Entry,epoch:[u8;16],luid:u64,\n    ifindex:u32,seq:u32,wire:&[u8],out:&mut [u8],mut sample:Option<&mut [u64;3]>\n)->Result<(usize,u32,u64),i32>{\n    let started=sample.as_ref().map(|_|Instant::now());"
  ],
  [
    "crates/wbd-engine/src/v4_windows_owner.rs",
    "    let mut opened_kind1=None;\n    let rx_storage=std::mem::take(&mut e.rx_scratch);",
    "    let mut opened_kind1=None;\n    if let (Some(t),Some(s))=(started,sample.as_deref_mut()){s[0]=t.elapsed().as_nanos() as u64;}\n    let draining_start=sample.as_ref().map(|_|Instant::now());\n    let rx_storage=std::mem::take(&mut e.rx_scratch);"
  ],
  [
    "crates/wbd-engine/src/v4_windows_owner.rs",
    "    e.rx_scratch=storage;\n    if valid && report.link_ready==1",
    "    e.rx_scratch=storage;\n    if let (Some(t),Some(s))=(draining_start,sample.as_deref_mut()){s[1]=t.elapsed().as_nanos() as u64;}\n    let finish_start=sample.as_ref().map(|_|Instant::now());\n    if valid && report.link_ready==1"
  ],
  [
    "crates/wbd-engine/src/v4_windows_owner.rs",
    "        e.rx_unwrapped_high=e.rx_unwrapped_high.max(unfolded+wire.len() as u64);\n        Ok((len,1,unique_pn))",
    "        e.rx_unwrapped_high=e.rx_unwrapped_high.max(unfolded+wire.len() as u64);\n        if let (Some(t),Some(s))=(finish_start,sample.as_deref_mut()){s[2]=t.elapsed().as_nanos() as u64;}\n        Ok((len,1,unique_pn))"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "     tunnel_dns:Option<&Arc<Mutex<TunnelDnsMap>>>,sample_delivery:Option<&mut H2476RxCost>)->Result<bool,i32>{",
    "     tunnel_dns:Option<&Arc<Mutex<TunnelDnsMap>>>,mut sample_delivery:Option<&mut H2476RxCost>)->Result<bool,i32>{"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "         let opened=v5_open_record_entry(&mut e,cfg.epoch,cfg.luid,\n             cfg.ifindex,seq,wire,plain);\n         opened",
    "         let mut timing=[0u64;3];\n         let opened=v5_open_record_entry_sampled(&mut e,cfg.epoch,cfg.luid,\n             cfg.ifindex,seq,wire,plain,if sample_delivery.is_some(){Some(&mut timing)}else{None});\n         if matches!(&opened,Ok((_,1,_))){\n             if let Some(p)=sample_delivery.as_deref_mut(){p.owner_samples+=1;p.owner_offer_ns+=timing[0];p.owner_drain_ns+=timing[1];p.owner_finish_ns+=timing[2];}\n         }\n         opened"
  ],
  [
    "crates/wbd-engine/src/v4_owner_crypto.rs",
    "    pub(crate) fn drain_windows_authenticated_kind1<F,G>(\n        &mut self,now:MonoNs,storage:Vec<RxPacket>,\n        mut accept_link:F,mut accept_kind1:G,\n    )->Result<(Vec<RxPacket>,AuthenticatedRxReport),\n               (ProtectedCryptoError,Vec<RxPacket>)>\n    where F:FnMut(u64,&[u8]), G:FnMut(u64,crate::v4_native_health::AuthenticatedControl) {\n        if self.state!=OwnerPhase::Active {\n            return Err((ProtectedCryptoError::Inactive,storage))\n        }\n        let mut borrowed=self.rx_tx.drain_rx(&self.token,now,storage)\n            .map_err(|(err,st)|(ProtectedCryptoError::Early(err),st))?;\n        let mut report=AuthenticatedRxReport::default();\n        for packet in borrowed.as_mut_slice(){\n            let Some(rx)=self.crypto.rx.as_mut() else{\n                report.rejected+=1;continue\n            };\n            match rx.open_unique_in_place(packet.wire_mut()){\n                Ok(record) if record.kind==AUTHENTICATED_LINK_KIND=>{\n                    accept_link(record.pn,record.payload);\n                    report.link_ready+=1;\n                },\n                Ok(record) if record.kind==\n                    wbd_codec::record_frame::AUTHENTICATED_HEALTH_KIND=>{\n                    if record.payload.len()>512 {\n                        report.rejected+=1;continue\n                    }\n                    match crate::v4_native_health::parse_authenticated_control(record.payload){\n                        Ok(control)=>{\n                            accept_kind1(record.pn,control);\n                            report.control_ready+=1;\n                        },\n                        Err(_)=>report.rejected+=1,\n                    }\n                },\n                Ok(_)=>report.rejected+=1,\n                Err(_)=>report.rejected+=1,\n            }\n        }\n        Ok((borrowed.recycle(),report))\n    }\n",
    "    pub(crate) fn drain_windows_authenticated_kind1<F,G>(\n        &mut self,now:MonoNs,storage:Vec<RxPacket>,\n        mut accept_link:F,accept_kind1:G,\n    )->Result<(Vec<RxPacket>,AuthenticatedRxReport),\n               (ProtectedCryptoError,Vec<RxPacket>)>\n    where F:FnMut(u64,&[u8]), G:FnMut(u64,crate::v4_native_health::AuthenticatedControl) {\n        self.drain_windows_authenticated_kind1_loan(now,storage,\n            |pn,_,link|accept_link(pn,link),accept_kind1)\n            .map(|(loan,report)|(loan.recycle(),report))\n    }\n\n    // Native synchronous RX keeps the original generation loan until Wintun\n    // has consumed the authenticated slice. No new opener or plaintext allocation.\n    #[cfg(target_os=\"windows\")]\n    pub(crate) fn drain_windows_authenticated_kind1_loan<F,G>(\n        &mut self,now:MonoNs,storage:Vec<RxPacket>,\n        mut accept_link:F,mut accept_kind1:G,\n    )->Result<(LoanBatch<RxPacket>,AuthenticatedRxReport),\n               (ProtectedCryptoError,Vec<RxPacket>)>\n    where F:FnMut(u64,usize,&[u8]), G:FnMut(u64,crate::v4_native_health::AuthenticatedControl) {\n        if self.state!=OwnerPhase::Active {\n            return Err((ProtectedCryptoError::Inactive,storage))\n        }\n        let mut borrowed=self.rx_tx.drain_rx(&self.token,now,storage)\n            .map_err(|(err,st)|(ProtectedCryptoError::Early(err),st))?;\n        let mut report=AuthenticatedRxReport::default();\n        for packet in borrowed.as_mut_slice(){\n            let Some(rx)=self.crypto.rx.as_mut() else{\n                report.rejected+=1;continue\n            };\n            let base=packet.wire_mut().as_ptr() as usize;\n            match rx.open_unique_in_place(packet.wire_mut()){\n                Ok(record) if record.kind==AUTHENTICATED_LINK_KIND=>{\n                    accept_link(record.pn,record.payload.as_ptr() as usize-base,record.payload);\n                    report.link_ready+=1;\n                },\n                Ok(record) if record.kind==\n                    wbd_codec::record_frame::AUTHENTICATED_HEALTH_KIND=>{\n                    if record.payload.len()>512 {\n                        report.rejected+=1;continue\n                    }\n                    match crate::v4_native_health::parse_authenticated_control(record.payload){\n                        Ok(control)=>{\n                            accept_kind1(record.pn,control);\n                            report.control_ready+=1;\n                        },\n                        Err(_)=>report.rejected+=1,\n                    }\n                },\n                Ok(_)=>report.rejected+=1,\n                Err(_)=>report.rejected+=1,\n            }\n        }\n        Ok((borrowed,report))\n    }\n"
  ],
  [
    "crates/wbd-engine/src/v4_windows_owner.rs",
    "fn v5_open_record_entry_sampled(e:&mut Entry,epoch:[u8;16],luid:u64,\n    ifindex:u32,seq:u32,wire:&[u8],out:&mut [u8],mut sample:Option<&mut [u64;3]>\n)->Result<(usize,u32,u64),i32>{\n    let started=sample.as_ref().map(|_|Instant::now());\n    if !v3_ready(e,epoch,luid,ifindex)||\n        wire.len()<=FIXED_WIRE_OVERHEAD || wire.len()>2048 ||\n        out.len()<wire.len(){return Err(INVALID)}\n    let mut slab=e.arena.allocate().map_err(|_|FULL)?;\n    slab.writable()[..wire.len()].copy_from_slice(wire);\n    let unfolded=m0_tcp_unwrap(e,seq,wire.len())?;\n    let now=m2_clock();\n    e.owner.offer_after_active(slab,0..wire.len(),unfolded,now)\n        .map_err(|_|INVALID)?;\n    let mut len=0usize;\n    let mut valid=false;\n    let mut opened_data_pn=None;\n    let mut opened_kind1=None;\n    if let (Some(t),Some(s))=(started,sample.as_deref_mut()){s[0]=t.elapsed().as_nanos() as u64;}\n    let draining_start=sample.as_ref().map(|_|Instant::now());\n    let rx_storage=std::mem::take(&mut e.rx_scratch);\n    let draining=e.owner.drain_windows_authenticated_kind1(\n        now,rx_storage,|pn,link|{\n            // No unauthenticated DATA, replay, HEALTH or fragmented LINK\n            // can reach a Windows kernel packet sink from this v3 boundary.\n            // Fragmentation will be installed with the complete M3 table.\n            if matches!(inspect_link(link,wire.len(),LinkMode::FixedOff),\n                Ok(LinkView::Ordinary(_))) &&\n                link.len()>=20 && link[0]>>4==4 &&\n                link[0]&15>=5 && link.len()<=out.len(){\n                out[..link.len()].copy_from_slice(link);\n                len=link.len();valid=true;opened_data_pn=Some(pn);\n            }\n        },|pn,receipt|{opened_kind1=Some((pn,receipt))});\n    let (storage,report)=match draining{\n        Ok(v)=>v,\n        Err((_,scratch))=>{e.rx_scratch=scratch;return Err(BAD_STAGE)}\n    };\n    e.rx_scratch=storage;\n    if let (Some(t),Some(s))=(draining_start,sample.as_deref_mut()){s[1]=t.elapsed().as_nanos() as u64;}\n    let finish_start=sample.as_ref().map(|_|Instant::now());\n    if valid && report.link_ready==1 && report.rejected==0\n        && report.control_ready==0 {\n        let unique_pn=opened_data_pn.ok_or(INVALID)?;\n        // Only the same owner-replay-checked M3 successful DATA opens\n        // activate RxFeedbackState. Control kind1 cannot ACK itself.\n        if let Some(m)=e.m2.as_mut(){\n            if m.auto_low_rate_mode {\n                m.quality_receive.on_unique_data(RecordPn(unique_pn),false);\n            }\n            m.health.on_authenticated_business(m2_clock().0);\n        }\n        e.rx_unwrapped_high=e.rx_unwrapped_high.max(unfolded+wire.len() as u64);\n        if let (Some(t),Some(s))=(finish_start,sample.as_deref_mut()){s[2]=t.elapsed().as_nanos() as u64;}\n        Ok((len,1,unique_pn))\n    }\n    // Only after the SAME original protected M3 AEAD and replay admission\n    // can this typed kind1 enter the bounded staging lane. It does not yet\n    // authorize shadow retirement or Go TCP carrier receipt.\n    else if report.link_ready==0&&report.control_ready==1&&report.rejected==0 {\n        let Some((pn,control))=opened_kind1 else{return Err(INVALID)};\n        if e.m2.is_some(){\n            // Health-only is verified liveness, not a frozen DATA receipt.\n            m2_authenticated_kind1_entry(e,pn,&control)?;\n        }else if let Some(receipt)=control.receipt{\n            if e.authenticated_kind1.len()>=MAX_AUTHENTICATED_KIND1{return Err(FULL)}\n            e.authenticated_kind1.push_back((pn,receipt));\n        }\n        e.rx_unwrapped_high=e.rx_unwrapped_high.max(unfolded+wire.len() as u64);\n        Ok((0,2,pn)) // kind1 is not an IPv4 packet or M2 shadow-release grant\n    } else {Err(INVALID)}\n}\n",
    "fn v5_open_record_entry_sampled(e:&mut Entry,epoch:[u8;16],luid:u64,\n    ifindex:u32,seq:u32,wire:&[u8],out:&mut [u8],mut sample:Option<&mut [u64;3]>\n)->Result<(usize,u32,u64),i32>{\n    let started=sample.as_ref().map(|_|Instant::now());\n    if !v3_ready(e,epoch,luid,ifindex)||\n        wire.len()<=FIXED_WIRE_OVERHEAD || wire.len()>2048 ||\n        out.len()<wire.len(){return Err(INVALID)}\n    let mut slab=e.arena.allocate().map_err(|_|FULL)?;\n    slab.writable()[..wire.len()].copy_from_slice(wire);\n    let unfolded=m0_tcp_unwrap(e,seq,wire.len())?;\n    let now=m2_clock();\n    e.owner.offer_after_active(slab,0..wire.len(),unfolded,now)\n        .map_err(|_|INVALID)?;\n    let mut len=0usize;\n    let mut valid=false;\n    let mut opened_data_pn=None;\n    let mut opened_kind1=None;\n    if let (Some(t),Some(s))=(started,sample.as_deref_mut()){s[0]=t.elapsed().as_nanos() as u64;}\n    let draining_start=sample.as_ref().map(|_|Instant::now());\n    let rx_storage=std::mem::take(&mut e.rx_scratch);\n    let draining=e.owner.drain_windows_authenticated_kind1(\n        now,rx_storage,|pn,link|{\n            // No unauthenticated DATA, replay, HEALTH or fragmented LINK\n            // can reach a Windows kernel packet sink from this v3 boundary.\n            // Fragmentation will be installed with the complete M3 table.\n            if matches!(inspect_link(link,wire.len(),LinkMode::FixedOff),\n                Ok(LinkView::Ordinary(_))) &&\n                link.len()>=20 && link[0]>>4==4 &&\n                link[0]&15>=5 && link.len()<=out.len(){\n                out[..link.len()].copy_from_slice(link);\n                len=link.len();valid=true;opened_data_pn=Some(pn);\n            }\n        },|pn,receipt|{opened_kind1=Some((pn,receipt))});\n    let (storage,report)=match draining{\n        Ok(v)=>v,\n        Err((_,scratch))=>{e.rx_scratch=scratch;return Err(BAD_STAGE)}\n    };\n    e.rx_scratch=storage;\n    if let (Some(t),Some(s))=(draining_start,sample.as_deref_mut()){s[1]=t.elapsed().as_nanos() as u64;}\n    let finish_start=sample.as_ref().map(|_|Instant::now());\n    if valid && report.link_ready==1 && report.rejected==0\n        && report.control_ready==0 {\n        let unique_pn=opened_data_pn.ok_or(INVALID)?;\n        // Only the same owner-replay-checked M3 successful DATA opens\n        // activate RxFeedbackState. Control kind1 cannot ACK itself.\n        if let Some(m)=e.m2.as_mut(){\n            if m.auto_low_rate_mode {\n                m.quality_receive.on_unique_data(RecordPn(unique_pn),false);\n            }\n            m.health.on_authenticated_business(m2_clock().0);\n        }\n        e.rx_unwrapped_high=e.rx_unwrapped_high.max(unfolded+wire.len() as u64);\n        if let (Some(t),Some(s))=(finish_start,sample.as_deref_mut()){s[2]=t.elapsed().as_nanos() as u64;}\n        Ok((len,1,unique_pn))\n    }\n    // Only after the SAME original protected M3 AEAD and replay admission\n    // can this typed kind1 enter the bounded staging lane. It does not yet\n    // authorize shadow retirement or Go TCP carrier receipt.\n    else if report.link_ready==0&&report.control_ready==1&&report.rejected==0 {\n        let Some((pn,control))=opened_kind1 else{return Err(INVALID)};\n        if e.m2.is_some(){\n            // Health-only is verified liveness, not a frozen DATA receipt.\n            m2_authenticated_kind1_entry(e,pn,&control)?;\n        }else if let Some(receipt)=control.receipt{\n            if e.authenticated_kind1.len()>=MAX_AUTHENTICATED_KIND1{return Err(FULL)}\n            e.authenticated_kind1.push_back((pn,receipt));\n        }\n        e.rx_unwrapped_high=e.rx_unwrapped_high.max(unfolded+wire.len() as u64);\n        Ok((0,2,pn)) // kind1 is not an IPv4 packet or M2 shadow-release grant\n    } else {Err(INVALID)}\n}\nfn h2478_open_record_loan(e:&mut Entry,epoch:[u8;16],luid:u64,\n    ifindex:u32,seq:u32,wire:&[u8],max_out:usize,storage:&mut Vec<RxPacket>,mut sample:Option<&mut [u64;3]>\n)->Result<(usize,u32,u64,usize,LoanBatch<RxPacket>),i32>{\n    let started=sample.as_ref().map(|_|Instant::now());\n    if !v3_ready(e,epoch,luid,ifindex)||\n        wire.len()<=FIXED_WIRE_OVERHEAD || wire.len()>2048 ||\n        max_out<wire.len(){return Err(INVALID)}\n    let mut slab=e.arena.allocate().map_err(|_|FULL)?;\n    slab.writable()[..wire.len()].copy_from_slice(wire);\n    let unfolded=m0_tcp_unwrap(e,seq,wire.len())?;\n    let now=m2_clock();\n    e.owner.offer_after_active(slab,0..wire.len(),unfolded,now)\n        .map_err(|_|INVALID)?;\n    let mut len=0usize;\n    let mut valid=false;\n    let mut offset=0usize;\n    let mut opened_data_pn=None;\n    let mut opened_kind1=None;\n    if let (Some(t),Some(s))=(started,sample.as_deref_mut()){s[0]=t.elapsed().as_nanos() as u64;}\n    let draining_start=sample.as_ref().map(|_|Instant::now());\n    let rx_storage=std::mem::take(storage);\n    let draining=e.owner.drain_windows_authenticated_kind1_loan(\n        now,rx_storage,|pn,at,link|{\n            // No unauthenticated DATA, replay, HEALTH or fragmented LINK\n            // can reach a Windows kernel packet sink from this v3 boundary.\n            // Fragmentation will be installed with the complete M3 table.\n            if matches!(inspect_link(link,wire.len(),LinkMode::FixedOff),\n                Ok(LinkView::Ordinary(_))) &&\n                link.len()>=20 && link[0]>>4==4 &&\n                link[0]&15>=5 && link.len()<=max_out{\n                offset=at;\n                len=link.len();valid=true;opened_data_pn=Some(pn);\n            }\n        },|pn,receipt|{opened_kind1=Some((pn,receipt))});\n    let (batch,report)=match draining{\n        Ok(v)=>v,\n        Err((_,scratch))=>{*storage=scratch;return Err(BAD_STAGE)}\n    };\n    if let (Some(t),Some(s))=(draining_start,sample.as_deref_mut()){s[1]=t.elapsed().as_nanos() as u64;}\n    let finish_start=sample.as_ref().map(|_|Instant::now());\n    let result=(||{\n    if valid && report.link_ready==1 && report.rejected==0\n        && report.control_ready==0 {\n        let unique_pn=opened_data_pn.ok_or(INVALID)?;\n        // Only the same owner-replay-checked M3 successful DATA opens\n        // activate RxFeedbackState. Control kind1 cannot ACK itself.\n        if let Some(m)=e.m2.as_mut(){\n            if m.auto_low_rate_mode {\n                m.quality_receive.on_unique_data(RecordPn(unique_pn),false);\n            }\n            m.health.on_authenticated_business(m2_clock().0);\n        }\n        e.rx_unwrapped_high=e.rx_unwrapped_high.max(unfolded+wire.len() as u64);\n        if let (Some(t),Some(s))=(finish_start,sample.as_deref_mut()){s[2]=t.elapsed().as_nanos() as u64;}\n        Ok((len,1,unique_pn))\n    }\n    // Only after the SAME original protected M3 AEAD and replay admission\n    // can this typed kind1 enter the bounded staging lane. It does not yet\n    // authorize shadow retirement or Go TCP carrier receipt.\n    else if report.link_ready==0&&report.control_ready==1&&report.rejected==0 {\n        let Some((pn,control))=opened_kind1 else{return Err(INVALID)};\n        if e.m2.is_some(){\n            // Health-only is verified liveness, not a frozen DATA receipt.\n            m2_authenticated_kind1_entry(e,pn,&control)?;\n        }else if let Some(receipt)=control.receipt{\n            if e.authenticated_kind1.len()>=MAX_AUTHENTICATED_KIND1{return Err(FULL)}\n            e.authenticated_kind1.push_back((pn,receipt));\n        }\n        e.rx_unwrapped_high=e.rx_unwrapped_high.max(unfolded+wire.len() as u64);\n        Ok((0,2,pn)) // kind1 is not an IPv4 packet or M2 shadow-release grant\n    } else {Err(INVALID)}\n    })();\n    match result{\n        Ok((used,kind,pn))=>Ok((used,kind,pn,offset,batch)),\n        Err(code)=>{*storage=batch.recycle();Err(code)},\n    }\n}\n"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "     borrowed:bool, continuation:bool, reads:u64, frames:u64, turns:u64, full:u64,",
    "     borrowed:bool, continuation:bool, loan:bool, loan_delivered:u64, reads:u64, frames:u64, turns:u64, full:u64,"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "owner_finish_ns={} owner_samples={}",
    "owner_finish_ns={} owner_samples={} loan={} loan_delivered={}"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "self.owner_finish_ns,self.owner_samples);",
    "self.owner_finish_ns,self.owner_samples,u8::from(self.loan),self.loan_delivered);"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "     let mut previous_full=false;",
    "     let mut previous_full=false;\n     let loan_enabled=std::env::var(\"WBD_H2478_RX_LOAN\").ok().as_deref()==Some(\"1\");\n     costs.loan=loan_enabled;\n     let mut loan_storage=Vec::<RxPacket>::with_capacity(8);\n     let mut loan_delivered=0u64;"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "     tunnel_dns:Option<&Arc<Mutex<TunnelDnsMap>>>,mut sample_delivery:Option<&mut H2476RxCost>)->Result<bool,i32>{",
    "     tunnel_dns:Option<&Arc<Mutex<TunnelDnsMap>>>,mut sample_delivery:Option<&mut H2476RxCost>,\n     loan_enabled:bool,loan_storage:&mut Vec<RxPacket>,loan_delivered:&mut u64)->Result<bool,i32>{"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "     let opened={\n         let mut e=lock_owner(lane,counters,LockDirection::Rx)?;\n         let mut timing=[0u64;3];\n         let opened=v5_open_record_entry_sampled(&mut e,cfg.epoch,cfg.luid,\n             cfg.ifindex,seq,wire,plain,if sample_delivery.is_some(){Some(&mut timing)}else{None});",
    "     let mut loan=None;\n     let opened={\n         let mut e=lock_owner(lane,counters,LockDirection::Rx)?;\n         let mut timing=[0u64;3];\n         let sample=if sample_delivery.is_some(){Some(&mut timing)}else{None};\n         let opened=if loan_enabled{\n             h2478_open_record_loan(&mut e,cfg.epoch,cfg.luid,cfg.ifindex,seq,wire,\n                 plain.len(),loan_storage,sample).map(|(used,kind,pn,offset,batch)|{\n                     loan=Some((offset,batch));(used,kind,pn)\n                 })\n         }else{\n             v5_open_record_entry_sampled(&mut e,cfg.epoch,cfg.luid,\n                 cfg.ifindex,seq,wire,plain,sample)\n         };"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "     match opened {\n         Ok((used,1,_))=>{\n             if owned_tunnel_dns_reply(&mut plain[..used],tunnel_dns)?{\n                 let started=sample_delivery.as_ref().map(|_|Instant::now());\n                 let result=tun.deliver_authenticated(&plain[..used]);",
    "     let result=(||{\n     match opened {\n         Ok((used,1,_))=>{\n             let data=if let Some((offset,batch))=loan.as_mut(){\n                 &mut batch.as_mut_slice()[0].wire_mut()[*offset..*offset+used]\n             }else{&mut plain[..used]};\n             if owned_tunnel_dns_reply(data,tunnel_dns)?{\n                 let started=sample_delivery.as_ref().map(|_|Instant::now());\n                 let result=tun.deliver_authenticated(data);"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "                 result.map_err(|_|BAD_STAGE)?;\n                 counters.rx_delivered.fetch_add(1,Ordering::Release);",
    "                 result.map_err(|_|BAD_STAGE)?;\n                 if loan_enabled{*loan_delivered+=1;}\n                 counters.rx_delivered.fetch_add(1,Ordering::Release);"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "         _=>Err(BAD_STAGE),\n     }\n }\n #[inline]\n fn flush_tx_wake",
    "         _=>Err(BAD_STAGE),\n     }\n     })();\n     if let Some((_,batch))=loan{*loan_storage=batch.recycle();}\n     result\n }\n #[inline]\n fn flush_tx_wake"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "                 tunnel_dns.as_ref(),None){",
    "                 tunnel_dns.as_ref(),None,loan_enabled,&mut loan_storage,&mut loan_delivered){"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "                 tunnel_dns.as_ref(),if sampled{Some(&mut costs)}else{None}){",
    "                 tunnel_dns.as_ref(),if sampled{Some(&mut costs)}else{None},loan_enabled,&mut loan_storage,&mut loan_delivered){"
  ],
  [
    "crates/wbd-engine/src/v4_windows_native_runtime.rs",
    "          previous_full=full;",
    "          previous_full=full;\n          costs.loan_delivered=loan_delivered;"
  ]
]
def sha(x):return hashlib.sha256(x).hexdigest()
def apply():
    records={}
    for name,a,b in CHANGES:
        path=pathlib.Path(name)
        if name not in records:records[name]={"before":sha(path.read_bytes())}
        text=path.read_text(encoding="utf-8")
        if text.count(a)!=1:raise ValueError("unexpected source anchor "+name)
        path.write_bytes(text.replace(a,b).encode("utf-8"))
        records[name]["after"]=sha(path.read_bytes())
    return records
if __name__=="__main__":
    out=pathlib.Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"base_source":"f18f907e1a1ce47f53bc5b27eb7fa2796754e01c","files":apply(),"patch_sha256":sha(pathlib.Path(__file__).read_bytes())},indent=2)+"\n")
