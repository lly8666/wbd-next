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
