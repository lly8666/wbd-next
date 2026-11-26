"""Apply the exact H2474 experiment to a frozen Windows Rust build workspace only."""
import hashlib,json,pathlib,sys
PATH=pathlib.Path("crates/wbd-engine/src/v4_windows_native_runtime.rs")
CHANGES=[
  [
    "     let mut boundary_rx=BoundaryQpcTrace::new(\"RX_WINTUN_SEND\");",
    "     let mut boundary_rx=BoundaryQpcTrace::new(\"RX_WINTUN_SEND\");\n     // Experiment H2474 only. The original Go handoff verifies nonblocking.\n     let continuation=std::env::var(\"WBD_H2474_RX_CONTINUE\").ok().as_deref()==Some(\"1\");\n     struct TurnReceipt {\n         continuation:bool, waits:u64, timeouts:u64, turns:u64, full:u64,\n         bypass:u64, bypass_empty:u64,\n     }\n     impl Drop for TurnReceipt {\n         fn drop(&mut self){\n             eprintln!(\"H2474_RX_TURN continuation={} waits={} timeouts={} turns={} full={} bypass={} bypass_empty={}\",\n                 u8::from(self.continuation),self.waits,self.timeouts,self.turns,self.full,self.bypass,self.bypass_empty);\n         }\n     }\n     eprintln!(\"H2474_RX_MODE continuation={}\",u8::from(continuation));\n     let mut stats=TurnReceipt{continuation,waits:0,timeouts:0,turns:0,full:0,bypass:0,bypass_empty:0};\n     let mut previous_full=false;"
  ],
  [
    "         match io::wait_ready(&[stop.handle(),event,early_notify.handle()],wait_ms){\n             Ok(WaitResult::Ready(0))=>return OK,\n             Ok(WaitResult::Ready(1|2))=>{},\n             Ok(WaitResult::Timeout)=>continue,\n             Err(_)=>return BAD_STAGE,\n             _=>return BAD_STAGE,\n         }\n         let mut npf_wakes=TxWakeBatch::default();",
    "         // Only a just-completed full ready turn can justify a speculative\n         // nonblocking read. Stop/early/direct work above still runs each turn.\n         // A deferred direct TCP return retains the original wait policy.\n         let bypass=continuation&&previous_full&&deferred_direct_tcp.is_none();\n         previous_full=false;\n         if bypass{\n             stats.bypass+=1;\n         }else{\n             stats.waits+=1;\n             match io::wait_ready(&[stop.handle(),event,early_notify.handle()],wait_ms){\n                 Ok(WaitResult::Ready(0))=>return OK,\n                 Ok(WaitResult::Ready(1|2))=>{},\n                 Ok(WaitResult::Timeout)=>{stats.timeouts+=1;continue},\n                 Err(_)=>return BAD_STAGE,\n                 _=>return BAD_STAGE,\n             }\n         }\n         stats.turns+=1;\n         let mut full_turn=true;\n         let mut npf_wakes=TxWakeBatch::default();"
  ],
  [
    "                 Ok(ReadResult::NoPacket)=>break,",
    "                 Ok(ReadResult::NoPacket)=>{full_turn=false;break},"
  ],
  [
    "          // Advance only on a genuine authenticated RX ready batch; this",
    "          if full_turn{stats.full+=1;}\n          else if bypass{stats.bypass_empty+=1;}\n          previous_full=full_turn;\n          // Advance only on a genuine authenticated RX ready batch; this"
  ]
]
def apply(source):
    start=source.index(" fn rx_loop(")
    end=source.index(" #[repr(C)]",start)
    rx=source[start:end]
    for a,b in CHANGES:
        if rx.count(a)!=1:raise ValueError("unexpected frozen rx_loop anchor "+a[:100])
        rx=rx.replace(a,b)
    return source[:start]+rx+source[end:]
def sha(b):return hashlib.sha256(b).hexdigest()
if __name__=="__main__":
    before=PATH.read_bytes();after=apply(before.decode("utf-8").replace("\r\n","\n")).encode("utf-8")
    PATH.write_bytes(after)
    out=pathlib.Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"base_source":"db8f56e0d8094c6393dbbc2c8ab92d8db7a2c141","path":str(PATH),"before_sha256":sha(before),"after_sha256":sha(after),"patch_sha256":sha(pathlib.Path(__file__).read_bytes())},indent=2)+"\n")
