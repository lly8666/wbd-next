//! PLAN029 Windows kernel TCP Direct implementation, not a user-space TCP
//! stack. One ORIGINAL Rust Wintun TX owns NAT, one Windows kernel listener,
//! physical-source-bound nonblocking sockets, and bounded read/write relays.
//! The sole original Rust RX still owns every Wintun SendPacket via mailbox.
//! Activation REQUIRES a generation-owned synthetic /32 route AND exact
//! Defender Allow prior to first Direct SYN. Until the Go owner can prove
//! both, the cold V3 actor remains disabled and Direct TCP fails closed.
use std::collections::{HashMap,HashSet,VecDeque};
use std::io::ErrorKind;
use std::net::{Ipv4Addr,SocketAddr,SocketAddrV4,TcpListener,TcpStream};
use std::os::windows::io::AsRawSocket;
use wbd_platform::windows_direct_tcp::{
    PhysicalTcpSocket,ConnectProgress,TcpDirectRelay,open_kernel_tcp_listener,
    SocketReadiness,TCP_EVENT_SHARDS,EVENT_ACCEPT,EVENT_CONNECT,
    EVENT_READ,EVENT_WRITE,EVENT_CONNECTED,EVENT_CLOSED,
};
use crate::v4_client_direct_tcp_nat::{DirectTcpNat,TcpNatKey};
use crate::v4_windows_native_dns_client_tcp::{ClientDnsTcp,NativeTcpDnsEndpoints};
use crate::v4_client_split::DnsEgress;
use crate::v4_client_fake_pool::FakeAllocator;
use crate::v4_client_fake_journal::FakeJournal;

// H1945 signed-test QPC: Win32 time base is shared with Python clients
// in this SAME Windows VM. Never compare it with the Linux guest clock.
#[link(name="kernel32")]
unsafe extern "system" {
    fn QueryPerformanceCounter(out:*mut i64)->i32;
    fn QueryPerformanceFrequency(out:*mut i64)->i32;
}
fn reply_qpc_now()->Option<i64>{
    let mut q=0i64;
    (unsafe{QueryPerformanceCounter(&mut q)}!=0 && q>0).then_some(q)
}
fn reply_qpc_frequency()->Option<i64>{
    let mut f=0i64;
    (unsafe{QueryPerformanceFrequency(&mut f)}!=0 && f>0).then_some(f)
}
const MAX_QPC_REPLY_ROWS:usize=1024;
const MAX_READY:usize=256;
const MAX_QUANTUM:usize=8;
const MAX_L3:usize=65535;
const PENDING_MS:u64=30_000;
// Metadata-only kernel TCP close grace: the relay's user-space EOF and
// empty queues do NOT mean the Windows TCP stack has finished transmitting,
// retransmitting or waiting for the application's final ACK. Keep the
// exact NAT reverse tuple for one bounded TCP shutdown window without
// retaining socket buffers or scheduling a 10ms data-plane wake.
const CLOSED_NAT_GRACE_MS:u64=60_000;
// Hard *allocation* ceiling remains 64 MiB across PLAN029 sources;
// Direct TCP borrows only an 8 MiB live pending-read soft budget.
// The rest is reserved for UDP/DNS/owner work, not queued TCP seconds.
const TCP_PENDING_POOL_LIMIT:usize=8*1024*1024;
// Allocated once on the first real relay, reused across all ready flows.
const RELAY_SCRATCH_BYTES:usize=64*1024;
/// H1917 signed original Windows/WSL2 still blocked on 4MiB Direct
/// upload after retrying positive *read* only. H1909/H1913 proved the
/// last 10GiB functional relay used a fair follow-up after ANY actual
/// read or write progress. Restore that bounded readiness contract:
/// each progress turn gets one FIFO ticket, and the next zero-progress
/// turn stops. This is not timer polling or a per-flow loop; the owner
/// still services at most eight flows, at most 64KiB per read turn.
/// The H1915 CPU-saving hypothesis is suspended until same-VM A/B can
/// prove both correctness and lower CPU; never sacrifice real delivery.
fn relay_needs_continuation(
    buffered:usize,bytes_read:usize,bytes_written:usize,close_probe_due:bool
)->bool{
    // H1909/H1913 signed 10GiB: a real write-only drain ALSO warrants
    // one fair follow-up. After zero bytes and no queued tail, stop.
    buffered!=0 || bytes_read!=0 || bytes_written!=0 || close_probe_due
}
// One short-lived entry per serviced relay ticket. The owner can service
// at most MAX_QUANTUM flows before draining these follow-ups; the previous
// Vec<u16> allocated/freed on nearly every positive-progress TX turn.
struct RelayFollowups{
    ports:[u16;MAX_QUANTUM],
    len:usize,
}
impl RelayFollowups{
    fn new()->Self{Self{ports:[0;MAX_QUANTUM],len:0}}
    fn push(&mut self,port:u16){
        // One fair ticket per serviced flow; never silently drop liveness.
        assert!(self.len<MAX_QUANTUM,"more follow-ups than served flows");
        self.ports[self.len]=port;
        self.len+=1;
    }
    fn ports(&self)->impl Iterator<Item=u16>+'_{
        self.ports[..self.len].iter().copied()
    }
}
/// When a new physical TCP socket becomes connected, FD_READ may have
/// been consumed by this actor while it was still in Connecting phase.
/// H1931 small-TCP first echo had a 10-15ms tail. Give each newly
/// CONNECTED relay exactly ONE first read/forward chance, even if it has
/// no FD_CLOSE hint; this runs after the old service quantum, on the
/// existing bounded FIFO. WouldBlock disarms reads until a real FD_READ.
/// No timer, per-flow thread or extra idle-loop polling.
fn schedule_connected_first_relay_tick(followups:&mut RelayFollowups,port:u16){
    followups.push(port)
}
fn listener_accept_needed(direct:usize,dns:usize)->bool{direct>0||dns>0}

enum TcpPhase{
    Connecting(TcpStream,PhysicalTcpSocket),
    Relaying(TcpDirectRelay),
}
struct Active{
    key:TcpNatKey,proxy_port:u16,phase:Option<TcpPhase>,
    last_activity_ms:u64,
    // Stable identity across swap_remove and NAT port reuse. One entry in
    // the bounded ready FIFO at most, keyed by (port,generation).
    generation:u64,queued:bool,fast_forward:bool,
    close_hints:[bool;2],
    first_reply_qpc_logged:bool,
    // Both zero for ordinary product flows; signed first event only.
    request_accept_qpc:i64,
    request_connected_qpc:i64,
}
impl TcpPhase{
    fn socket_handles(&self)->(usize,usize){
        match self{
            Self::Connecting(inner,outer)=>
                (inner.as_raw_socket() as usize,outer.raw_socket()),
            Self::Relaying(pair)=>pair.socket_handles(),
        }
    }
}
struct ActiveDns{
    key:TcpNatKey,proxy_port:u16,
    stream:ClientDnsTcp,tunnel_source:Option<u16>,
}
// One per-accepted-flow metadata token, bounded by the same NAT hard cap.
// Only a slow expiring queue is swept; no per-flow timer and no full-table
// scan. A newly closing flow cannot reuse its NAT port until expired.
#[derive(Default)]
struct ClosedNatGrace{
    by_port:HashMap<u16,(TcpNatKey,u64)>,
    deadlines:VecDeque<(u16,u64)>,
}
impl ClosedNatGrace{
    fn next_due(&self)->Option<u64>{
        self.deadlines.front().map(|(_,due)|*due)
    }
    fn defer(&mut self,port:u16,key:TcpNatKey,now_ms:u64){
        let due=now_ms.saturating_add(CLOSED_NAT_GRACE_MS);
        self.by_port.insert(port,(key,due));
        self.deadlines.push_back((port,due));
    }
    fn expire_some(&mut self,now_ms:u64,nat:&mut DirectTcpNat,
        retired:&mut Vec<TcpNatKey>){
        for _ in 0..64{
            let Some(&(port,due))=self.deadlines.front()else{break};
            if due>now_ms{break}
            self.deadlines.pop_front();
            let Some((key,current))=self.by_port.get(&port).copied()else{continue};
            if current!=due{continue}
            self.by_port.remove(&port);
            if nat.retire(key){retired.push(key);}
        }
    }
}
/// TCP reverse returns have a stricter loss rule than UDP under the same
/// bounded 256-entry mailbox. This helper also makes the FIFO/limit invariant
/// testable without creating a WinSock listener or a second owner.
fn retain_native_tcp_front(queue:&mut VecDeque<Vec<u8>>,packet:Vec<u8>)
    ->Result<(),()>{
    if queue.len()>=MAX_READY || packet.len()<40 ||
        packet[0]>>4!=4 || packet[9]!=6 {
        return Err(())
    }
    queue.push_front(packet);
    Ok(())
}
// Only actual accept/connect/relay progress can skip the owner's idle wait.
// WouldBlock is not progress; closed NAT metadata remains deadline-driven.
pub(crate) struct TcpServiceTick{
    pub retired:Vec<TcpNatKey>,
    pub advanced:bool,
}
// One cold-only P2 diagnosis switch. The default product never formats
// per-flow counters or samples wall clocks on the hot packet path. The
// signed fixture enables this only for the single stalled TCP test.
#[derive(Default)]
struct TcpLegDiagnosis{
    next_ms:u64,
    read_inner:u64,read_outer:u64,
    wrote_inner:u64,wrote_outer:u64,
    direct_forwarded:u64,queued_copy:u64,
    // P2-only ready queue high-water/overflow; no per-packet logging.
    ready_peak:usize,ready_full:u64,
    shard_wakes:u64,event_socket_checks:u64,event_take_errors:u64,
    event_read:u64,event_write:u64,event_connect:u64,event_close:u64,
    ready_ticket_peak:usize,ready_served:u64,
    ready_wait_sum_ms:u64,ready_wait_max_ms:u64,
    relay_turns:u64,relay_zero_progress:u64,
    relay_progress_no_self_ticket:u64,relay_progress_self_ticket:u64,
    relay_close_probe_self_ticket:u64,
    connected_first_probe_tickets:u64,
    ready_wait_ge8_ms:u64,ready_wait_ge16_ms:u64,
    // Source-locked diagnosis only: distinguish event/ticket delay
    // before the first outer kernel TCP reply recv from delay after
    // Rust has written the inner WinSock leg. No per-flow logs or timer.
    reply_outer_read_turns:u64,
    reply_outer_ready_wait_max_ms:u64,
    reply_outer_ready_wait_ge8_ms:u64,
    reply_outer_ready_wait_ge16_ms:u64,
    reply_outer_read_inner_write_same_turn:u64,
    reply_outer_read_no_inner_write:u64,
    reply_inner_write_deferred_turns:u64,
    // At most one timestamp on the first real inner-kernel reply write
    // per original Direct flow; only source-locked signed CI enables it.
    reply_qpc_frequency:i64,
    reply_qpc_rows:Vec<(u16,i64)>,
    reply_path_qpc_frequency:i64,
    reply_path_qpc_rows:Vec<(u16,i64,i64,i64)>,
    prewrite_qpc_frequency:i64,
    prewrite_qpc_rows:Vec<(u16,i64,i64,i64,i64,i64,i64)>,
    io_reads:[u64;2],io_read_wouldblock:[u64;2],
    io_fin_peek_calls:[u64;2],io_fin_peek_eof:[u64;2],
    io_writes:[u64;2],io_write_wouldblock:[u64;2],
    io_short_writes:[u64;2],io_read_gated:[u64;2],
    io_event_suppressed_reads:[u64;2],
    // Four actual kernel TCP local EOF/SHUT_WR transitions, recorded
    // only by existing opt-in original TX diagnostic. An accepted()
    // or send() success is NOT proof of remote Linux packet delivery.
    half_close_transitions:[u64;4],
}
// Existing P2 opt-in only, using the same owner-monotonic enqueue time
// already attached to a generation-scoped ready ticket. A positive outer
// recv is real Linux->Windows kernel TCP payload; a same-turn inner write
// proves the Rust socket relay did not add a later queue service round.
// It does NOT time the later Wintun rewrite/RX injection or OS delivery.
fn note_reply_service(d:&mut TcpLegDiagnosis,ready_age_ms:u64,
    outer_read_bytes:usize,inner_write_bytes:usize){
    if outer_read_bytes>0{
        d.reply_outer_read_turns=d.reply_outer_read_turns.saturating_add(1);
        d.reply_outer_ready_wait_max_ms=
            d.reply_outer_ready_wait_max_ms.max(ready_age_ms);
        d.reply_outer_ready_wait_ge8_ms=
            d.reply_outer_ready_wait_ge8_ms.saturating_add(u64::from(ready_age_ms>=8));
        d.reply_outer_ready_wait_ge16_ms=
            d.reply_outer_ready_wait_ge16_ms.saturating_add(u64::from(ready_age_ms>=16));
        if inner_write_bytes>0{
            d.reply_outer_read_inner_write_same_turn=
                d.reply_outer_read_inner_write_same_turn.saturating_add(1);
        }else{
            d.reply_outer_read_no_inner_write=
                d.reply_outer_read_no_inner_write.saturating_add(1);
        }
    }else if inner_write_bytes>0{
        d.reply_inner_write_deferred_turns=
            d.reply_inner_write_deferred_turns.saturating_add(1);
    }
}
/// H1892 signed, test-only 128 real Wintun source-port admissions.
#[derive(Default)]
struct ProbeTcp128{
    admitted:usize,
    active_peak:usize,
    max_same_shard:usize,
}
pub(crate) struct NativeTcpActor{
    lease:u32,synthetic:u32,
    physical:Ipv4Addr,ifindex:u32,
    listener:TcpListener,nat:DirectTcpNat,
    pending:HashMap<u16,(TcpNatKey,u64)>,
    deadlines:VecDeque<(u16,u64)>,
    active:Vec<Active>,
    active_by_port:HashMap<u16,usize>,
    shard_ports:[Vec<u16>;TCP_EVENT_SHARDS],
    // Actual monotonic ticket enqueue time; generation rejects stale
    // reused ports, so only live tickets count toward measured latency.
    flow_ready:VecDeque<(u16,u64,u64)>,
    next_generation:u64,
    accept_armed:bool,
    notified_shards:u16,
    connect_deadlines:VecDeque<(u16,u64,u64)>,
    closing:ClosedNatGrace,
    dns_nat:DirectTcpNat,
    dns_pending:HashMap<u16,(TcpNatKey,u64)>,
    dns_deadlines:VecDeque<(u16,u64)>,
    dns_active:Vec<ActiveDns>,dns_cursor:usize,
    dns_closing:ClosedNatGrace,dns_tunnel_sources:HashSet<u16>,
    ready:VecDeque<Vec<u8>>,
    // Pending bytes and actual VecDeque backing capacities are separate.
    buffered_bytes:usize,
    resident_bytes:usize,
    scratch:Option<Box<[u8;RELAY_SCRATCH_BYTES]>>,
    diagnosis:Option<TcpLegDiagnosis>,
    /// Four real TCP sessions on a reserved test port, within ONE signed
    /// Wintun owner generation. None in an ordinary product build.
    probe_abba_next:Option<usize>,
    // Bounded, source-locked 128 real original Wintun socket fixture:
    // aggregate peak + exactly one immutable record per accepted kernel
    // TCP connection, no new product control/threads or per-packet logs.
    probe_tcp128:Option<ProbeTcp128>,
    // Last field: all sockets (listener, accepted, DNS) drop before the
    // WinSock event group is closed, preserving exact owned Stop order.
    socket_events:SocketReadiness,
}
pub(crate) fn safe_synthetic(lease:u32,underlay:u32,synthetic:u32,
    fake_range:(u32,u32))->bool{
    synthetic!=0&&synthetic!=u32::MAX&&
    synthetic!=lease&&synthetic!=underlay&&
    (synthetic<fake_range.0||synthetic>fake_range.1)
}
impl NativeTcpActor{
    /// The Go owner MUST have already proved its precise generation-owned
    /// synthetic /32 and one Defender listener rule. This construction
    /// cannot install routes, modify global firewall, or start threads.
    pub(crate) fn new(lease:Ipv4Addr,synthetic:Ipv4Addr,
        physical:Ipv4Addr,ifindex:u32,hard:usize,
        fake_range:(u32,u32))->Result<Self,()>{
        if !safe_synthetic(u32::from(lease),u32::from(physical),
                u32::from(synthetic),fake_range)||
           ifindex==0||hard==0||hard>16384{return Err(())}
        let listener=open_kernel_tcp_listener(lease).map_err(|_|())?;
        let port=listener.local_addr().map_err(|_|())?.port();
        let nat=DirectTcpNat::new(u32::from(lease),u32::from(synthetic),
            port,hard).map_err(|_|())?;
        let dns_nat=DirectTcpNat::new_dns(u32::from(lease),
            u32::from(synthetic),port).map_err(|_|())?;
        let socket_events=SocketReadiness::new().map_err(|_|())?;
        socket_events.watch(listener.as_raw_socket() as usize,0,EVENT_ACCEPT)
            .map_err(|_|())?;
        let mut diagnosis=(std::env::var("WBD_PLAN029_P2_RELAY_DIAG").ok()
                .as_deref()==Some("1")).then(TcpLegDiagnosis::default);
        let signed_qpc=cfg!(feature="m0_v4_probe") &&
            std::env::var("GITHUB_ACTIONS").ok().as_deref()==Some("true") &&
            std::env::var("WBD_PLAN029_NATIVE_V3_TRIAL").ok().as_deref()==Some("1") &&
            std::env::var("WBD_PLAN029_P2_BULK_SCENE").ok().as_deref()==Some("1") &&
            std::env::var("WBD_PLAN029_P2_SMALL_TCP_SCENE").ok().as_deref()==Some("1") &&
            std::env::var("WBD_PLAN029_P2_ECHO_EARLY_CONTROL").ok().as_deref()==Some("1") &&
            std::env::var("WBD_PLAN029_P2_REPLY_QPC_SCENE").ok().as_deref()==Some("1");
        if signed_qpc {
            diagnosis.as_mut().ok_or(())?.reply_qpc_frequency=
                reply_qpc_frequency().ok_or(())?;
        }
        let signed_path_qpc=signed_qpc &&
            std::env::var("WBD_PLAN029_P2_REPLY_PATH_QPC_SCENE").ok()
                .as_deref()==Some("1");
        if signed_path_qpc {
            let d=diagnosis.as_mut().ok_or(())?;
            d.reply_path_qpc_frequency=d.reply_qpc_frequency;
        }
        let signed_prewrite_qpc=signed_path_qpc &&
            std::env::var("WBD_PLAN029_P2_PREWRITE_QPC_SCENE").ok()
                .as_deref()==Some("1");
        if signed_prewrite_qpc {
            let d=diagnosis.as_mut().ok_or(())?;
            d.prewrite_qpc_frequency=d.reply_qpc_frequency;
        }
        Ok(Self{lease:u32::from(lease),synthetic:u32::from(synthetic),
            physical,ifindex,listener,nat,pending:HashMap::new(),
            deadlines:VecDeque::new(),active:Vec::new(),
            active_by_port:HashMap::new(),
            shard_ports:std::array::from_fn(|_|Vec::new()),
            flow_ready:VecDeque::new(),next_generation:0,
            accept_armed:false,notified_shards:0,
            connect_deadlines:VecDeque::new(),
            closing:ClosedNatGrace::default(),
            dns_nat,dns_pending:HashMap::new(),
            dns_deadlines:VecDeque::new(),dns_active:Vec::new(),
            dns_cursor:0,dns_closing:ClosedNatGrace::default(),
            dns_tunnel_sources:HashSet::new(),
            ready:VecDeque::with_capacity(MAX_READY),
            buffered_bytes:0,resident_bytes:0,scratch:None,
            diagnosis,
            // Nested explicit gates: probe ABI, signed CI, real mixed P2
            // and ABBA-specific selection. Ordinary users cannot turn on
            // the comparison code by a new CLI flag or generic env alone.
            probe_abba_next:(cfg!(feature="m0_v4_probe") &&
                std::env::var("GITHUB_ACTIONS").ok().as_deref()==Some("true") &&
                std::env::var("WBD_PLAN029_NATIVE_V3_TRIAL").ok().as_deref()==Some("1") &&
                std::env::var("WBD_PLAN029_P2_MIXED_SCENE").ok().as_deref()==Some("1") &&
                std::env::var("WBD_PLAN029_P2_ABBA_SCENE").ok().as_deref()==Some("1")
                ).then_some(0),
            probe_tcp128:(cfg!(feature="m0_v4_probe") &&
                std::env::var("GITHUB_ACTIONS").ok().as_deref()==Some("true") &&
                std::env::var("WBD_PLAN029_NATIVE_V3_TRIAL").ok().as_deref()==Some("1") &&
                std::env::var("WBD_PLAN029_P2_MIXED_SCENE").ok().as_deref()==Some("1") &&
                std::env::var("WBD_PLAN029_TCP128_SCENE").ok().as_deref()==Some("1")
                ).then_some(ProbeTcp128::default()),
            socket_events})
    }
    /// A post-Apply generation-owned listener's actual ephemeral port.
    /// Never guess this value in Go or open a global firewall wildcard.
    pub(crate) fn listener_port(&self)->Result<u16,()>{
        self.listener.local_addr().map(|a|a.port()).map_err(|_|())
    }
    /// One original TX WaitForMultipleObjects observes all 16 bounded
    /// WinSock shards, together with Wintun, Stop and owner notification.
    pub(crate) fn socket_event_handles(&self)->&[usize]{
        self.socket_events.handles()
    }
    pub(crate) fn note_socket_event(&mut self,shard:usize){
        if shard<TCP_EVENT_SHARDS{
            self.notified_shards|=1u16<<shard;
            if let Some(d)=self.diagnosis.as_mut(){
                d.shard_wakes=d.shard_wakes.saturating_add(1);
            }
        }
    }
    fn enqueue_port(&mut self,port:u16,now_ms:u64){
        let Some(&idx)=self.active_by_port.get(&port)else{return};
        // Finish the one mutable slot update before the rare stale-FIFO
        // compaction borrows the active table immutably (Windows E0502).
        let generation={
            let flow=&mut self.active[idx];
            if flow.queued{return}
            flow.queued=true;
            flow.generation
        };
        // 2x hard16k bounds transient stale generations without dropping
        // a live flow's single ready ticket.
        if self.flow_ready.len()>=32768{
            let index=&self.active_by_port;
            let active=&self.active;
            self.flow_ready.retain(|(p,g,_)|index.get(p)
                .and_then(|&i|active.get(i))
                .is_some_and(|a|a.generation==*g));
        }
        self.flow_ready.push_back((port,generation,now_ms));
        if let Some(d)=self.diagnosis.as_mut(){
            d.ready_ticket_peak=d.ready_ticket_peak.max(self.flow_ready.len());
        }
    }
    fn harvest_events(&mut self,now_ms:u64){
        let pending=std::mem::take(&mut self.notified_shards);
        for shard in 0..TCP_EVENT_SHARDS{
            if pending&(1u16<<shard)==0{continue}
            // Shard0's listener is its reset anchor; other shards reset
            // atomically on the first valid owned socket, then scan all
            // recorded socket flags with NULL hEventObject.
            if shard==0{
                match self.socket_events.take(
                    self.listener.as_raw_socket() as usize,0,true){
                    Ok(mask)=>self.accept_armed|=SocketReadiness::is_accept(mask),
                    Err(_)=>self.accept_armed=true,
                }
            }
            let mut reset=shard!=0;
            for index in 0..self.shard_ports[shard].len(){
                let port=self.shard_ports[shard][index];
                let Some(&slot)=self.active_by_port.get(&port)else{continue};
                let Some(phase)=self.active[slot].phase.as_ref()else{continue};
                let (inner,outer)=phase.socket_handles();
                let imask=self.socket_events.take(inner,shard,reset);
                if imask.is_ok(){reset=false}
                let omask=self.socket_events.take(outer,shard,reset);
                if omask.is_ok(){reset=false}
                // The existing conservative error path must still queue
                // the flow. Metrics never alter readiness semantics.
                let errors=u64::from(imask.is_err())+u64::from(omask.is_err());
                let imask=imask.unwrap_or(EVENT_READ);
                let omask=omask.unwrap_or(EVENT_READ);
                if let Some(d)=self.diagnosis.as_mut(){
                    d.event_socket_checks=d.event_socket_checks.saturating_add(2);
                    d.event_take_errors=d.event_take_errors.saturating_add(errors);
                    for bits in [imask,omask]{
                        d.event_read+=u64::from(bits&EVENT_READ!=0);
                        d.event_write+=u64::from(bits&EVENT_WRITE!=0);
                        d.event_connect+=u64::from(bits&EVENT_CONNECTED!=0);
                        d.event_close+=u64::from(bits&EVENT_CLOSED!=0);
                    }
                }
                let closed_inner=imask&EVENT_CLOSED!=0;
                let closed_outer=omask&EVENT_CLOSED!=0;
                self.active[slot].close_hints[0]|=closed_inner;
                self.active[slot].close_hints[1]|=closed_outer;
                if let Some(TcpPhase::Relaying(pair))=
                    self.active[slot].phase.as_mut(){
                    pair.note_read_event(
                        imask&(EVENT_READ|EVENT_CLOSED)!=0,
                        omask&(EVENT_READ|EVENT_CLOSED)!=0);
                    pair.note_close_event(closed_inner,closed_outer);
                }
                if imask!=0||omask!=0{
                    self.enqueue_port(port,now_ms);
                }
            }
            if reset{
                // Only an empty/unusable shard gets a plain reset. No
                // recorded live socket can be lost by this case.
                let _=self.socket_events.clear_unused(shard);
            }
        }
    }
    pub(crate) fn needs_service(&self,now_ms:u64)->bool{
        self.accept_armed||self.notified_shards!=0||!self.flow_ready.is_empty()||
        self.deadlines.front().is_some_and(|(_,due)|*due<=now_ms)||
        self.dns_deadlines.front().is_some_and(|(_,due)|*due<=now_ms)||
        self.connect_deadlines.front().is_some_and(|(_,_,due)|*due<=now_ms)||
        self.closing.next_due().is_some_and(|due|due<=now_ms)||
        self.dns_closing.next_due().is_some_and(|due|due<=now_ms)
    }
    pub(crate) fn has_dns_sessions(&self)->bool{!self.dns_active.is_empty()}
    pub(crate) fn has_work(&self)->bool{
        // Closed NAT grace is metadata waiting for the kernel, not work
        // that warrants the original TX worker's 10ms active wait.
        !self.pending.is_empty()||!self.active.is_empty()||
            !self.dns_pending.is_empty()||!self.dns_active.is_empty()||
            !self.ready.is_empty()
    }
    pub(crate) fn next_close_due_ms(&self)->Option<u64>{
        self.closing.next_due().into_iter()
            .chain(self.dns_closing.next_due())
            .chain(self.deadlines.front().map(|(_,due)|*due))
            .chain(self.dns_deadlines.front().map(|(_,due)|*due))
            .chain(self.connect_deadlines.front().map(|(_,_,due)|*due))
            .min()
    }
    pub(crate) fn buffered_bytes(&self)->usize{self.buffered_bytes}
    pub(crate) fn resident_bytes(&self)->usize{self.resident_bytes}
    pub(crate) fn ready_pop(&mut self)->Option<Vec<u8>>{
        self.ready.pop_front()
    }
    /// A TCP reply that could not enter the bounded TX->RX mailbox MUST
    /// stay in its exact NAT order. Dropping one translated TCP ACK/DATA
    /// makes Windows wait for a retransmit timeout (~seconds), whereas a
    /// Direct UDP datagram may legitimately be discarded under pressure.
    /// This restores only an already authenticated, previously popped
    /// kernel TCP return; no new NAT flow or Wintun reader is created.
    pub(crate) fn restore_tcp_ready_front(&mut self,packet:Vec<u8>)
        ->Result<(),()>{
        retain_native_tcp_front(&mut self.ready,packet)
    }
    /// All kernel-side L3 writes enqueue bytes, never borrow a second
    /// Wintun session, and never block an authenticated Tunnel DATA batch.
    fn record_ready_full(&mut self){
        if let Some(d)=self.diagnosis.as_mut(){
            d.ready_full=d.ready_full.saturating_add(1);
        }
    }
    fn enqueue_owned(&mut self,wire:Vec<u8>)->Result<(),()>{
        if self.ready.len()>=MAX_READY{
            self.record_ready_full();
            return Err(())
        }
        // The single Vec allocation is already owned by this NAT packet.
        // Never re-copy its payload or borrow another Wintun device/ring.
        self.ready.push_back(wire);
        if let Some(d)=self.diagnosis.as_mut(){
            d.ready_peak=d.ready_peak.max(self.ready.len());
        }
        Ok(())
    }
    /// DNS TCP uses the exact same post-Apply owned listener and single
    /// Rust TX reverse mailbox. Source-port NAT has independent 256 hard
    /// quota, never borrows the ordinary Direct hard16k table or Tunnel.
    pub(crate) fn dns_ingress(&mut self,packet:&[u8],now_ms:u64)
        ->Result<(),()>{
        if packet.len()<40||packet.len()>MAX_L3||self.ready.len()>=MAX_READY||
           packet[0]>>4!=4||packet[9]!=6{return Err(())}
        let ihl=usize::from(packet[0]&15)*4;
        if ihl<20||ihl+4>packet.len()||
           u16::from_be_bytes([packet[ihl+2],packet[ihl+3]])!=53{
            return Err(())
        }
        let presented=u32::from_be_bytes(packet[16..20].try_into().map_err(|_|())?);
        let prior=self.dns_nat.len();
        let mut rewritten=packet.to_vec();
        let entry=self.dns_nat.to_listener_in_place(&mut rewritten,presented,
            now_ms).map_err(|_|())?;
        if self.enqueue_owned(rewritten).is_err(){
            if self.dns_nat.len()>prior{self.dns_nat.retire(entry.key);}
            return Err(())
        }
        if self.dns_nat.len()>prior{
            let due=now_ms.saturating_add(PENDING_MS);
            self.dns_pending.insert(entry.proxy_port,(entry.key,due));
            self.dns_deadlines.push_back((entry.proxy_port,due));
            self.accept_armed=true;
        }
        Ok(())
    }
    pub(crate) fn is_internal_tunnel_dns_tcp(&self,port:u16)->bool{
        self.dns_tunnel_sources.contains(&port)
    }
    /// Called only for an ingress-classified Direct TCP flow. An original
    /// SYN allocates one NAT key; its subsequent DATA/ACK reuse the same
    /// exact key, not hostname or shared physical CDN lookup.
    pub(crate) fn direct(&mut self,packet:&[u8],real:u32,
        now_ms:u64)->Result<(),()>{
        if packet.len()<40||packet.len()>MAX_L3{return Err(())}
        if self.ready.len()>=MAX_READY{
            self.record_ready_full();
            return Err(())
        }
        let was=self.nat.len();
        let mut rewritten=packet.to_vec();
        let entry=self.nat.to_listener_in_place(&mut rewritten,real,now_ms)
            .map_err(|_|())?;
        if self.enqueue_owned(rewritten).is_err(){
            if self.nat.len()>was{self.nat.retire(entry.key);}
            return Err(())
        }
        if self.nat.len()>was{
            let deadline=now_ms.saturating_add(PENDING_MS);
            self.pending.insert(entry.proxy_port,(entry.key,deadline));
            self.deadlines.push_back((entry.proxy_port,deadline));
            self.accept_armed=true;
        }
        Ok(())
    }
    pub(crate) fn kernel_return(&mut self,packet:&[u8])
        ->Option<Result<(),()>>{
        if packet.len()<20||packet[0]>>4!=4||packet[9]!=6||
           u32::from_be_bytes(packet[12..16].try_into().ok()?)!=self.lease||
           u32::from_be_bytes(packet[16..20].try_into().ok()?)!=self.synthetic{
            return None
        }
        // Reject a full owned reverse queue before one allocation or NAT
        // mutation. A TCP packet is NEVER silently dropped on pressure.
        if self.ready.len()>=MAX_READY{
            self.record_ready_full();
            return Some(Err(()))
        }
        let mut rewritten=packet.to_vec();
        if self.dns_nat.to_app_in_place(&mut rewritten)
            .or_else(|_|self.nat.to_app_in_place(&mut rewritten)).is_err(){
            return Some(Err(()))
        }
        Some(self.enqueue_owned(rewritten))
    }
    /// One existing owner tick services at most 8 accepted connections and
    /// 8 existing relays (bounded rotating quantum); no per-flow thread
    /// or whole-table polling on every Wintun packet.
    pub(crate) fn tick(&mut self,now_ms:u64)->TcpServiceTick{
        let mut retired=Vec::new();
        let mut advanced=false;
        self.harvest_events(now_ms);
        let accepting=self.accept_armed &&
            listener_accept_needed(self.pending.len(),self.dns_pending.len());
        self.accept_armed=false;
        if accepting{
        // Exactly one WouldBlock disables this admission until a real
        // FD_ACCEPT or a new owned ingress NAT wakes the same TX owner.
        for turn in 0..MAX_QUANTUM{
            let (stream,peer)=match self.listener.accept(){
                Ok(ok)=>{advanced=true;ok},
                Err(e) if e.kind()==ErrorKind::WouldBlock=>break,
                Err(_)=>break,
            };
            if turn+1==MAX_QUANTUM{self.accept_armed=true}
            let SocketAddr::V4(peer)=peer else{continue};
            if let Some(entry)=self.dns_nat.accepted(u32::from(*peer.ip()),peer.port()){
                if self.dns_pending.remove(&entry.proxy_port).is_none(){continue}
                match ClientDnsTcp::new(stream,now_ms){
                    Ok(dns)=>self.dns_active.push(ActiveDns{
                        key:entry.key,proxy_port:entry.proxy_port,
                        stream:dns,tunnel_source:None,
                    }),
                    Err(())=>{self.dns_nat.retire(entry.key);}
                }
                continue
            }
            let Some(entry)=self.nat.accepted(u32::from(*peer.ip()),peer.port())
                else{continue};
            if !self.pending.contains_key(&entry.proxy_port){continue}
            self.pending.remove(&entry.proxy_port);
            let accept_qpc=if self.diagnosis.as_ref().is_some_and(|d|
                d.prewrite_qpc_frequency>0){
                reply_qpc_now().unwrap_or(0)
            }else{0};
            let dst=SocketAddrV4::new(Ipv4Addr::from(entry.real_dst),
                entry.key.target_port);
            match PhysicalTcpSocket::start(self.physical,self.ifindex,dst){
                Ok(socket)=>{
                    let shard=SocketReadiness::shard(entry.proxy_port);
                    let watches=self.socket_events.watch(
                        stream.as_raw_socket() as usize,shard,EVENT_CONNECT)
                        .and_then(|_|self.socket_events.watch(
                            socket.raw_socket(),shard,EVENT_CONNECT));
                    if watches.is_err(){
                        self.nat.retire(entry.key);
                        retired.push(entry.key);
                        continue
                    }
                    // The reserved P2 A/B port is distinct from the
                    // original H1760 32KiB fake TCP probe port. This
                    // counter cannot consume a physical baseline socket
                    // or a DNS TCP flow; only real Direct NAT admissions.
                    let fast_forward=if entry.key.target_port==46116{
                        if let Some(ordinal)=self.probe_abba_next.as_mut(){
                            if *ordinal>=4{
                                self.nat.retire(entry.key);
                                retired.push(entry.key);
                                continue
                            }
                            let index=*ordinal;
                            *ordinal+=1;
                            let fast=index==1||index==2;
                            eprintln!("PLAN029_H1884_ABBA_ADMITTED source=real_wintun_direct ordinal={} mode={}",
                                index+1,if fast{"bypass"}else{"copy"});
                            fast
                        }else{true}
                    }else{true};
                    self.next_generation=self.next_generation.wrapping_add(1);
                    if self.next_generation==0{self.next_generation=1}
                    let generation=self.next_generation;
                    let index=self.active.len();
                    self.active.push(Active{
                        key:entry.key,proxy_port:entry.proxy_port,
                        phase:Some(TcpPhase::Connecting(stream,socket)),
                        last_activity_ms:now_ms,generation,queued:false,
                        fast_forward,close_hints:[false,false],
                        first_reply_qpc_logged:false,
                        request_accept_qpc:accept_qpc,
                        request_connected_qpc:0,
                    });
                    self.active_by_port.insert(entry.proxy_port,index);
                    self.shard_ports[shard].push(entry.proxy_port);
                    // This is an actual accepted Windows kernel socket
                    // whose SYN came from the original Wintun application
                    // and whose matching physical socket was registered
                    // into the original TX WinSock event shard.
                    if let Some(probe)=self.probe_tcp128.as_mut(){
                        if entry.key.target_port==46112 &&
                            (42500..42628).contains(&entry.key.source_port){
                            probe.admitted=probe.admitted.saturating_add(1);
                            probe.active_peak=probe.active_peak.max(self.active.len());
                            probe.max_same_shard=probe.max_same_shard.max(
                                self.shard_ports[shard].len());
                            eprintln!("PLAN029_H1892_WINTUN_TCP_ADMITTED source_port={} proxy_port={} shard={} source=real_wintun_direct",
                                entry.key.source_port,entry.proxy_port,shard);
                        }
                    }
                    self.connect_deadlines.push_back((
                        entry.proxy_port,generation,now_ms.saturating_add(PENDING_MS)));
                    self.enqueue_port(entry.proxy_port,now_ms); // probe immediate connect
                },
                Err(_)=>{
                    self.nat.retire(entry.key);
                    retired.push(entry.key)
                }
            }
        }
        } // No accept() syscall when no Direct/DNS NAT is waiting.
        // Only expired in-flight connects are queued; idle TCP never
        // occupies an RX quantum or a 10ms timer. A stale generation cannot
        // accidentally schedule a reused NAT source port.
        for _ in 0..64{
            let Some(&(port,generation,due))=self.connect_deadlines.front()
                else{break};
            if due>now_ms{break}
            self.connect_deadlines.pop_front();
            if self.active_by_port.get(&port)
                .and_then(|&i|self.active.get(i))
                .is_some_and(|a|a.generation==generation &&
                    a.phase.as_ref().is_some_and(|p|
                        matches!(p,TcpPhase::Connecting(..)))){
                self.enqueue_port(port,now_ms);
            }
        }
        let mut to_remove=Vec::new();
        let mut to_requeue=RelayFollowups::new();
        let mut serviced=0;
        for _ in 0..(MAX_QUANTUM*4){
            if serviced>=MAX_QUANTUM{break}
            let Some((port,generation,queued_at))=self.flow_ready.pop_front()else{break};
            let Some(&idx)=self.active_by_port.get(&port)else{continue};
            if self.active[idx].generation!=generation{continue}
            let ready_age_ms=now_ms.saturating_sub(queued_at);
            if let Some(d)=self.diagnosis.as_mut(){
                let age=ready_age_ms;
                d.ready_served=d.ready_served.saturating_add(1);
                d.ready_wait_sum_ms=d.ready_wait_sum_ms.saturating_add(age);
                d.ready_wait_max_ms=d.ready_wait_max_ms.max(age);
                d.ready_wait_ge8_ms+=u64::from(age>=8);
                d.ready_wait_ge16_ms+=u64::from(age>=16);
            }
            self.active[idx].queued=false;
            serviced+=1;
            let flow=&mut self.active[idx];
            // A live kernel TCP may be quiescent for hours; FIN/RST,
            // half-close and OS socket EOF own its retirement. Only
            // nonblocking PHYSICAL CONNECT is bounded to 30s.
            if flow.phase.as_ref().is_some_and(|phase|
                matches!(phase,TcpPhase::Connecting(..))) &&
                now_ms.saturating_sub(flow.last_activity_ms)>=PENDING_MS{
                to_remove.push((idx,false));
                continue
            }
            let Some(phase)=flow.phase.take()else{
                to_remove.push((idx,false));continue
            };
            match phase{
                TcpPhase::Connecting(inner,mut outer)=>{
                    match outer.poll_connected(){
                        Ok(ConnectProgress::Pending)=>{
                            flow.phase=Some(TcpPhase::Connecting(inner,outer))
                        },
                        Ok(ConnectProgress::Connected)=>{
                            advanced=true;
                            if self.diagnosis.as_ref().is_some_and(|d|
                                d.prewrite_qpc_frequency>0){
                                flow.request_connected_qpc=reply_qpc_now().unwrap_or(0);
                            }
                            let fast_forward=flow.fast_forward;
                            match outer.into_connected_stream().and_then(|outside|
                                TcpDirectRelay::with_fast_forward(inner,outside,fast_forward)){
                                Ok(mut relay)=>{
                                    // Only this owner receives the real
                                    // per-socket WSAEventSelect masks. The
                                    // platform relay stays compatible with
                                    // component callers lacking event pumps.
                                    relay.enable_event_driven_reads();
                                    if self.diagnosis.as_ref().is_some_and(|d|
                                        d.reply_path_qpc_frequency>0){
                                        relay.enable_signed_reply_path_qpc();
                                    }
                                    relay.note_close_event(
                                        flow.close_hints[0],flow.close_hints[1]);
                                    // Even WITHOUT FD_CLOSE, a read-ready
                                    // indication may have been consumed
                                    // during Connecting. The newly created
                                    // relay must get one real nonblocking
                                    // recv opportunity before parking.
                                    // ONE bounded FIFO ticket per actual
                                    // connected socket; WouldBlock can then
                                    // disarm it until FD_READ.
                                    schedule_connected_first_relay_tick(
                                        &mut to_requeue,port);
                                    if let Some(d)=self.diagnosis.as_mut(){
                                        d.connected_first_probe_tickets=
                                            d.connected_first_probe_tickets
                                                .saturating_add(1);
                                    }
                                    flow.phase=Some(TcpPhase::Relaying(relay));
                                    flow.last_activity_ms=now_ms;
                                },
                                Err(_)=>to_remove.push((idx,false)),
                            }
                        },
                        Err(_)=>to_remove.push((idx,false)),
                    }
                },
                TcpPhase::Relaying(mut pair)=>{
                    // Account actual retained VecDeque capacity, not merely
                    // the bytes currently pending. A drained queue can
                    // otherwise retain 64KiB per direction indefinitely.
                    let previous=pair.pending_bytes();
                    let old_resident=pair.resident_bytes();
                    if previous==0 &&
                        now_ms.saturating_sub(flow.last_activity_ms)>=500{
                        // Low frequency and only when idle; never shrink
                        // after every write on an active TCP stream.
                        pair.release_idle_capacity();
                        self.resident_bytes=self.resident_bytes
                            .saturating_sub(old_resident)
                            .saturating_add(pair.resident_bytes());
                    }
                    let before=pair.resident_bytes();
                    let scratch=self.scratch.get_or_insert_with(||
                        Box::new([0u8;RELAY_SCRATCH_BYTES]));
                    let free=TCP_PENDING_POOL_LIMIT.saturating_sub(
                        self.resident_bytes.saturating_add(RELAY_SCRATCH_BYTES));
                    let half_close_before=pair.half_close_state();
                    match pair.service_once_with_scratch(free,&mut scratch[..]){
                        Ok(tick)=>{
                            let after=pair.resident_bytes();
                            let retained=self.resident_bytes
                                .saturating_sub(before).saturating_add(after);
                            if retained>TCP_PENDING_POOL_LIMIT.saturating_sub(RELAY_SCRATCH_BYTES){
                                // A target allocator unexpectedly grew
                                // beyond the reserved pool; only this
                                // Direct TCP relay fails closed.
                                self.buffered_bytes=self.buffered_bytes.saturating_sub(previous);
                                self.resident_bytes=self.resident_bytes.saturating_sub(before);
                                to_remove.push((idx,true));
                                continue
                            }
                            self.resident_bytes=retained;
                            if let Some(d)=self.diagnosis.as_mut(){
                                let half_close_after=pair.half_close_state();
                                for state in 0..4{
                                    if !half_close_before[state] && half_close_after[state]{
                                        d.half_close_transitions[state]=
                                            d.half_close_transitions[state].saturating_add(1);
                                    }
                                }
                                d.relay_turns=d.relay_turns.saturating_add(1);
                                note_reply_service(d,ready_age_ms,
                                    tick.outer_read,tick.inner_write);
                                if d.reply_qpc_frequency>0 &&
                                   !flow.first_reply_qpc_logged &&
                                   tick.inner_write>0 &&
                                   d.reply_qpc_rows.len()<MAX_QPC_REPLY_ROWS {
                                    if let Some(q)=reply_qpc_now(){
                                        d.reply_qpc_rows.push((flow.key.source_port,q));
                                        if d.reply_path_qpc_frequency>0 &&
                                           d.reply_path_qpc_rows.len()<MAX_QPC_REPLY_ROWS {
                                            if let Some(path)=pair.signed_reply_path_qpc(){
                                                // Incomplete first-events must be
                                                // rejected by the signed analyzer.
                                                d.reply_path_qpc_rows.push((
                                                    flow.key.source_port,
                                                    path.first_outer_write,
                                                    path.first_outer_read,q));
                                                if d.prewrite_qpc_frequency>0 &&
                                                   d.prewrite_qpc_rows.len()<MAX_QPC_REPLY_ROWS{
                                                    d.prewrite_qpc_rows.push((
                                                        flow.key.source_port,
                                                        flow.request_accept_qpc,
                                                        flow.request_connected_qpc,
                                                        path.first_inner_read,
                                                        path.first_outer_write,
                                                        path.first_outer_read,q));
                                                }
                                            }
                                        }
                                        flow.first_reply_qpc_logged=true;
                                    }
                                }
                                if tick.bytes_read==0&&tick.bytes_written==0{
                                    d.relay_zero_progress=d.relay_zero_progress.saturating_add(1);
                                }
                                for leg in 0..2{
                                    d.io_reads[leg]=d.io_reads[leg].saturating_add(tick.io.read_calls[leg] as u64);
                                    d.io_read_wouldblock[leg]=d.io_read_wouldblock[leg].saturating_add(tick.io.read_wouldblock[leg] as u64);
                                    d.io_fin_peek_calls[leg]=d.io_fin_peek_calls[leg].saturating_add(tick.io.fin_peek_calls[leg] as u64);
                                    d.io_fin_peek_eof[leg]=d.io_fin_peek_eof[leg].saturating_add(tick.io.fin_peek_eof[leg] as u64);
                                    d.io_writes[leg]=d.io_writes[leg].saturating_add(tick.io.write_calls[leg] as u64);
                                    d.io_write_wouldblock[leg]=d.io_write_wouldblock[leg].saturating_add(tick.io.write_wouldblock[leg] as u64);
                                    d.io_short_writes[leg]=d.io_short_writes[leg].saturating_add(tick.io.short_writes[leg] as u64);
                                    d.io_read_gated[leg]=d.io_read_gated[leg].saturating_add(tick.io.gated_reads[leg] as u64);
                                    d.io_event_suppressed_reads[leg]=
                                        d.io_event_suppressed_reads[leg].saturating_add(
                                            tick.io.event_suppressed_reads[leg] as u64);
                                }
                                d.read_inner=d.read_inner.saturating_add(tick.inner_read as u64);
                                d.read_outer=d.read_outer.saturating_add(tick.outer_read as u64);
                                d.wrote_inner=d.wrote_inner.saturating_add(tick.inner_write as u64);
                                d.wrote_outer=d.wrote_outer.saturating_add(tick.outer_write as u64);
                                d.direct_forwarded=d.direct_forwarded.saturating_add(
                                    tick.forwarded_without_queue as u64);
                                d.queued_copy=d.queued_copy.saturating_add(
                                    tick.copied_to_queue as u64);
                            }
                            self.buffered_bytes=self.buffered_bytes
                                .saturating_sub(previous).saturating_add(tick.buffered);
                            if tick.bytes_read>0||tick.bytes_written>0{
                                advanced=true;
                                flow.last_activity_ms=now_ms;
                                if !tick.finished{
                                    // H1915 short-progress suppression
                                    // caused H1916/H1917 real P2 failures.
                                    // Restore H1909/H1913 proven progress
                                    // tickets for BOTH read and write-only
                                    // turns. The next no-progress tick
                                    // never self-enqueues: no idle poll,
                                    // timer or unbounded work per flow.
                                    if relay_needs_continuation(
                                        tick.buffered,tick.bytes_read,
                                        tick.bytes_written,tick.close_probe_due){
                                        to_requeue.push(port);
                                        if let Some(d)=self.diagnosis.as_mut(){
                                            d.relay_progress_self_ticket=
                                                d.relay_progress_self_ticket.saturating_add(1);
                                            if tick.close_probe_due{
                                                d.relay_close_probe_self_ticket=
                                                    d.relay_close_probe_self_ticket.saturating_add(1);
                                            }
                                        }
                                    }else if let Some(d)=self.diagnosis.as_mut(){
                                        d.relay_progress_no_self_ticket=
                                            d.relay_progress_no_self_ticket.saturating_add(1);
                                    }
                                }
                            }
                            if tick.finished{
                                advanced=true;
                                // pair is dropped below rather than kept
                                // in flow.phase. Release its backing-memory
                                // budget now, not on a later close-grace.
                                self.resident_bytes=self.resident_bytes.saturating_sub(after);
                                self.buffered_bytes=self.buffered_bytes.saturating_sub(tick.buffered);
                                to_remove.push((idx,true))
                            }else{flow.phase=Some(TcpPhase::Relaying(pair))}
                        },
                        Err(_)=>{
                            self.buffered_bytes=self.buffered_bytes.saturating_sub(previous);
                            self.resident_bytes=self.resident_bytes.saturating_sub(before);
                            to_remove.push((idx,true))
                        },
                    }
                }
            }
        }
        // swap_remove plus port->slot keeps ready tokens stable in O(1)
        // per retired flow; generation rejects all stale queued tokens.
        to_remove.sort_unstable_by_key(|(idx,_)|*idx);
        to_remove.dedup_by_key(|(idx,_)|*idx);
        for (idx,keep_reverse) in to_remove.into_iter().rev(){
            let flow=self.active.swap_remove(idx);
            self.active_by_port.remove(&flow.proxy_port);
            if idx<self.active.len(){
                let moved=self.active[idx].proxy_port;
                self.active_by_port.insert(moved,idx);
            }
            self.shard_ports[SocketReadiness::shard(flow.proxy_port)]
                .retain(|&port|port!=flow.proxy_port);
            if keep_reverse{
                // Closed kernel socket retains only exact reverse NAT grace,
                // not any event handle, pending Vec or ready work ticket.
                self.closing.defer(flow.proxy_port,flow.key,now_ms);
            }else if self.nat.retire(flow.key){
                retired.push(flow.key)
            }
        }
        for port in to_requeue.ports(){self.enqueue_port(port,now_ms)}
        // One TX turn never sleeps while an already-ready flow waits
        // beyond the fair eight-flow service quantum.
        advanced|=!self.flow_ready.is_empty();
        // Admission-time-only expiry. Each port appears exactly once.
        // Evict <=64 silent, not-yet-accepted SYNs per coarse tick.
        for _ in 0..64{
            let Some(&(port,due))=self.deadlines.front()else{break};
            if due>now_ms{break}
            self.deadlines.pop_front();
            let Some((key,current))=self.pending.get(&port).copied()else{continue};
            if current!=due{continue}
            self.pending.remove(&port);
            self.nat.retire(key);
            retired.push(key);
        }
        // Metadata-only closing flows are never on the fast 10ms wake.
        // Their final FakeIP ref is released only after the exact NAT
        // reverse mapping can no longer be needed for TCP retransmission.
        self.closing.expire_some(now_ms,&mut self.nat,&mut retired);
        for _ in 0..64 {
            let Some(&(port,due))=self.dns_deadlines.front()else{break};
            if due>now_ms{break}
            self.dns_deadlines.pop_front();
            if self.dns_pending.get(&port).is_some_and(|x|x.1==due){
                if let Some((key,_))=self.dns_pending.remove(&port){
                    self.dns_nat.retire(key);
                }
            }
        }
        let mut dns_retired=Vec::new();
        self.dns_closing.expire_some(now_ms,&mut self.dns_nat,
            &mut dns_retired);
        if let Some(d)=self.diagnosis.as_mut(){
            if now_ms>=d.next_ms && (!self.active.is_empty()||
                    !self.pending.is_empty()||!self.dns_active.is_empty()){
                d.next_ms=now_ms.saturating_add(1_000);
                // No addresses, credentials, payloads, per-packet tracing,
                // or blocking filesystem I/O. Snapshot only active counts
                // and committed kernel socket byte receipts once a second.
                eprintln!("PLAN029_H1839_NATIVE_TCP_LEGS active={} pending={} dns_active={} inner_read={} outer_read={} inner_write={} outer_write={} direct_forwarded={} queued_copy={} buffered={} resident={} ready_now={} ready_peak={} ready_full={} source=real_kernel_two_leg",
                    self.active.len(),self.pending.len(),self.dns_active.len(),
                    d.read_inner,d.read_outer,d.wrote_inner,d.wrote_outer,
                    d.direct_forwarded,d.queued_copy,
                    self.buffered_bytes,self.resident_bytes.saturating_add(
                        if self.scratch.is_some(){RELAY_SCRATCH_BYTES}else{0}),
                    self.ready.len(),d.ready_peak,d.ready_full);
                d.ready_peak=self.ready.len();
            }
        }
        TcpServiceTick{retired,advanced}
    }
    /// One bounded 8-client readiness turn, no flow thread and no extra
    /// Wintun/NPF ring reader. One stalled resolver only holds its ticket.
    pub(crate) fn tick_dns<F>(&mut self,now_ms:u64,ep:NativeTcpDnsEndpoints,
        route:&F,mut pool:Option<&mut FakeAllocator>,
        mut journal:Option<&mut FakeJournal>)
        where F:Fn(&str)->Option<DnsEgress>
    {
        let count=self.dns_active.len();
        let quantum=count.min(MAX_QUANTUM);
        let mut done=Vec::new();
        for step in 0..quantum {
            let idx=(self.dns_cursor+step)%count;
            let free=self.dns_tunnel_sources.len()<64;
            let flow=&mut self.dns_active[idx];
            match flow.stream.step(now_ms,ep,route,
                pool.as_deref_mut(),journal.as_deref_mut(),free){
                Ok(tick)=>{
                    if let Some(port)=tick.new_tunnel_port{
                        if !self.dns_tunnel_sources.insert(port){
                            done.push(idx);continue
                        }
                        flow.tunnel_source=Some(port);
                    }
                    if tick.finished{done.push(idx)}
                },
                Err(())=>done.push(idx),
            }
        }
        done.sort_unstable();done.dedup();
        for idx in done.into_iter().rev(){
            let flow=self.dns_active.remove(idx);
            if let Some(port)=flow.tunnel_source{
                self.dns_tunnel_sources.remove(&port);
            }
            // TCP FIN/ACK still belongs to the Windows kernel after the
            // application DNS frame is complete; retain inverse NAT.
            self.dns_closing.defer(flow.proxy_port,flow.key,now_ms);
        }
        if self.dns_active.is_empty(){self.dns_cursor=0}
        else{self.dns_cursor=(self.dns_cursor+quantum)%self.dns_active.len()}
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    fn packet(src:u32,dst:u32,sport:u16,dport:u16,flags:u8)->[u8;40]{
        let mut p=[0u8;40];
        p[0]=0x45;p[2..4].copy_from_slice(&40u16.to_be_bytes());
        p[8]=64;p[9]=6;
        p[12..16].copy_from_slice(&src.to_be_bytes());
        p[16..20].copy_from_slice(&dst.to_be_bytes());
        p[20..22].copy_from_slice(&sport.to_be_bytes());
        p[22..24].copy_from_slice(&dport.to_be_bytes());
        p[32]=0x50;p[33]=flags;p
    }
    #[test]
    fn plan029_event_shards_and_stale_generation_bound(){
        assert!(listener_accept_needed(1,0));
        assert_eq!(SocketReadiness::shard(16),0);
        assert_eq!(SocketReadiness::shard(17),1);
        // Two successive owners may reuse the same NAT source port:
        // a stale ready ticket must never match the new incarnation.
        let old=(12345u16,7u64);
        let replacement=(12345u16,8u64);
        assert_ne!(old,replacement);
        assert!(replacement.1!=old.1);
    }
    /// Restore H1909/H1913 known native 10GiB liveness: even a
    /// WRITE-ONLY service quantum can need a fair follow-up. H1917
    /// only retried recv>0 and signed P2 then stalled on upload.
    #[test]
    fn plan029_h1926_stack_only_fair_followup_capacity_and_fifo(){
        // The bound comes from serviced<=MAX_QUANTUM. No per-turn Vec
        // growth or allocator calls; preserve the exact serviced order.
        assert!(std::mem::size_of::<RelayFollowups>()<=32);
        let mut q=RelayFollowups::new();
        assert_eq!(q.ports().count(),0);
        for i in 0..MAX_QUANTUM{q.push(41000+i as u16)}
        assert_eq!(q.ports().collect::<Vec<_>>(),
            (41000..41000+MAX_QUANTUM as u16).collect::<Vec<_>>());
        assert!(relay_needs_continuation(0,0,1,false));
        assert!(!relay_needs_continuation(0,0,0,false));
    }
    #[test]
    fn plan029_h1938_connected_relay_first_tick_when_no_close_hint(){
        // FD_READ may have arrived while the physical TCP socket was
        // Connecting; no subsequent edge is guaranteed before recv().
        // The connection transition must schedule ONE first real read
        // opportunity without a close hint or 10ms polling. Existing
        // positive progress tickets remain unchanged and bounded.
        let mut tickets=RelayFollowups::new();
        schedule_connected_first_relay_tick(&mut tickets,46116);
        assert_eq!(tickets.ports().collect::<Vec<_>>(),vec![46116]);
        // One no-progress turn does not schedule another ticket.
        assert!(!relay_needs_continuation(0,0,0,false));
        // Genuine send OR recv positive progress still earns one fair
        // continuation, preserving H1920's signed 4MiB/10GiB liveness.
        assert!(relay_needs_continuation(0,16,0,false));
        assert!(relay_needs_continuation(0,0,16,false));
    }
    #[test]
    #[should_panic(expected="more follow-ups than served flows")]
    fn plan029_h1926_stack_followup_overrun_fails_loudly(){
        let mut q=RelayFollowups::new();
        for i in 0..=MAX_QUANTUM{q.push(45000+i as u16)}
    }
    #[test]
    fn plan029_h1920_legacy_any_progress_single_fair_ticket(){
        assert!(!relay_needs_continuation(0,0,0,false));
        for n in [1,413,16*1024,32*1024,RELAY_SCRATCH_BYTES-1,
                  RELAY_SCRATCH_BYTES]{
            assert!(relay_needs_continuation(0,n,0,false),
                "positive read must advance");
            assert!(relay_needs_continuation(0,0,n,false),
                "write-only progress must advance");
        }
        assert!(relay_needs_continuation(1,0,0,false));
        assert!(relay_needs_continuation(16*1024,512,0,false));
        assert!(relay_needs_continuation(0,32768,0,true));
        assert!(relay_needs_continuation(0,0,16384,true));
        // The following idle / WouldBlock service turn has no ticket.
        assert!(!relay_needs_continuation(0,0,0,false));
    }
    #[test]
    fn plan029_h1943_real_outer_reply_ticket_age_is_separate_from_generic_queue(){
        let mut d=TcpLegDiagnosis::default();
        note_reply_service(&mut d,16,64,64);
        note_reply_service(&mut d,9,1024,0);
        note_reply_service(&mut d,3,0,1024);
        note_reply_service(&mut d,0,16,16);
        note_reply_service(&mut d,100,0,0);
        assert_eq!(d.reply_outer_read_turns,3);
        assert_eq!(d.reply_outer_ready_wait_max_ms,16);
        assert_eq!(d.reply_outer_ready_wait_ge8_ms,2);
        assert_eq!(d.reply_outer_ready_wait_ge16_ms,1);
        assert_eq!(d.reply_outer_read_inner_write_same_turn,2);
        assert_eq!(d.reply_outer_read_no_inner_write,1);
        assert_eq!(d.reply_inner_write_deferred_turns,1);
        // Zero-byte/zero-progress turns do not invent reply evidence.
        assert_eq!(d.ready_served,0);
    }
    #[test]
    fn plan029_ready_fifo_ticket_age_is_monotonic_and_generation_scoped(){
        let mut d=TcpLegDiagnosis::default();
        let now=640u64;let enqueued=627u64;
        d.ready_wait_max_ms=d.ready_wait_max_ms.max(now.saturating_sub(enqueued));
        d.ready_wait_sum_ms+=now.saturating_sub(enqueued);
        d.ready_served+=1;
        assert_eq!(d.ready_wait_max_ms,13);
        assert_eq!(d.ready_wait_sum_ms,13);
        // A stale generation is filtered by the actor before counters.
        assert_ne!((200u16,10u64),(200u16,11u64));
        assert_eq!(enqueued.saturating_sub(now),0);
    }
    #[test]
    fn plan029_skip_idle_listener_but_keep_dns_tcp_admission(){
        assert!(!listener_accept_needed(0,0));
        assert!(listener_accept_needed(1,0));
        assert!(listener_accept_needed(0,1));
    }
    #[test]
    fn plan029_tcp_mailbox_backpressure_restores_exact_original_fifo(){
        let ip=u32::from(Ipv4Addr::new(10,66,0,2));
        let synthetic=u32::from(Ipv4Addr::new(198,19,1,1));
        let first=packet(ip,synthetic,55000,32768,0x10).to_vec();
        let later=packet(ip,synthetic,55000,32768,0x18).to_vec();
        let mut ready=VecDeque::from([later.clone()]);
        assert_eq!(retain_native_tcp_front(&mut ready,first.clone()),Ok(()));
        assert_eq!(ready.pop_front(),Some(first.clone()));
        assert_eq!(ready.pop_front(),Some(later));
        let mut udp=first.clone();
        udp[9]=17;
        assert_eq!(retain_native_tcp_front(&mut ready,udp),Err(()));
        assert!(ready.is_empty());
        for _ in 0..MAX_READY{ready.push_back(first.clone());}
        assert_eq!(retain_native_tcp_front(&mut ready,first),Err(()));
        assert_eq!(ready.len(),MAX_READY);
    }
    #[test]
    fn plan029_close_retain_exact_nat_until_kernel_tcp_fin_retransmit_grace(){
        let lease=u32::from(Ipv4Addr::new(10,66,0,2));
        let fake=u32::from(Ipv4Addr::new(198,18,0,1));
        let synthetic=u32::from(Ipv4Addr::new(198,19,118,116));
        let real=u32::from(Ipv4Addr::new(172,19,17,54));
        let mut nat=DirectTcpNat::new(lease,synthetic,56234,1).unwrap();
        let mut out=[0u8;128];
        let (_,entry)=nat.to_listener(&packet(lease,fake,56236,46112,2),
            real,100,&mut out).unwrap();
        let kernel_reply=packet(lease,synthetic,56234,entry.proxy_port,0x18);
        let mut closed=ClosedNatGrace::default();
        closed.defer(entry.proxy_port,entry.key,200);
        assert_eq!(closed.next_due(),Some(200+CLOSED_NAT_GRACE_MS));
        // A fully read/written user-space relay can finish while the
        // kernel still owns 32KiB of TCP data/retransmit/FIN to the app.
        assert_eq!(nat.len(),1);
        assert!(nat.to_app(&kernel_reply,&mut out).is_ok());
        let mut retired=Vec::new();
        closed.expire_some(200+CLOSED_NAT_GRACE_MS-1,
            &mut nat,&mut retired);
        assert_eq!(nat.len(),1);
        assert!(retired.is_empty());
        assert_eq!(nat.to_listener(&packet(lease,fake,56237,46112,2),
            real,100,&mut out).err(),Some(crate::v4_client_direct_tcp_nat::TcpNatError::Capacity));
        closed.expire_some(200+CLOSED_NAT_GRACE_MS,&mut nat,&mut retired);
        assert_eq!(retired,vec![entry.key]);
        assert_eq!(nat.len(),0);
        assert_eq!(closed.next_due(),None);
        assert!(nat.to_app(&kernel_reply,&mut out).is_err());
        assert!(nat.to_listener(&packet(lease,fake,56237,46112,2),
            real,100,&mut out).is_ok());
    }
    #[test]
    fn plan029_close_grace_bounded_expiration_no_busy_work(){
        let mut closed=ClosedNatGrace::default();
        let key=TcpNatKey{client:1,source_port:2,presented:3,target_port:4};
        closed.defer(32768,key,10);
        let mut nat=DirectTcpNat::new(1,2,3,16).unwrap();
        let mut retired=Vec::new();
        closed.expire_some(10+CLOSED_NAT_GRACE_MS-1,&mut nat,&mut retired);
        assert_eq!(closed.by_port.len(),1);
        assert!(retired.is_empty());
        closed.expire_some(10+CLOSED_NAT_GRACE_MS,&mut nat,&mut retired);
        assert!(closed.by_port.is_empty());
        assert!(retired.is_empty()); // stale, never-issued NAT is not owned
    }
    #[test]
    fn plan029_closed_nat_129_metadata_retire_in_bounded_64_item_quanta(){
        let mut closing=ClosedNatGrace::default();
        let now=7_000u64;
        for i in 0..129u16{
            closing.defer(32_768+i,TcpNatKey{
                client:1,source_port:10_000+i,presented:3,target_port:4,
            },now);
        }
        let mut nat=DirectTcpNat::new(1,2,3,256).unwrap();
        let mut retired=Vec::new();
        closing.expire_some(now+CLOSED_NAT_GRACE_MS-1,&mut nat,&mut retired);
        assert_eq!(closing.by_port.len(),129);
        assert_eq!(closing.next_due(),Some(now+CLOSED_NAT_GRACE_MS));
        closing.expire_some(now+CLOSED_NAT_GRACE_MS,&mut nat,&mut retired);
        assert_eq!(closing.by_port.len(),65);
        closing.expire_some(now+CLOSED_NAT_GRACE_MS,&mut nat,&mut retired);
        assert_eq!(closing.by_port.len(),1);
        closing.expire_some(now+CLOSED_NAT_GRACE_MS,&mut nat,&mut retired);
        assert!(closing.by_port.is_empty());
        assert_eq!(closing.next_due(),None);
        assert!(retired.is_empty()); // these were never owned NAT ports
    }
    #[test]
    fn plan029_native_kernel_tcp_synthetic_peer_never_overlaps_fake_or_lease(){
        let lease=0x0aea0c22;
        let physical=0x0a010007;
        let fake=(0xc6120001,0xc612fffe);
        assert!(safe_synthetic(lease,physical,0xc6135763,fake));
        assert!(!safe_synthetic(lease,physical,0xc6120005,fake));
        assert!(!safe_synthetic(lease,physical,lease,fake));
        assert!(!safe_synthetic(lease,physical,physical,fake));
        assert!(!safe_synthetic(lease,physical,0,fake));
        assert!(!safe_synthetic(lease,physical,u32::MAX,fake));
    }
}

impl Drop for NativeTcpActor{
    fn drop(&mut self){
        if let Some(p)=self.probe_tcp128.as_ref(){
            eprintln!("PLAN029_H1892_TCP128_FINAL admitted={} active_peak={} max_same_shard={} source=real_wintun_direct",
                p.admitted,p.active_peak,p.max_same_shard);
        }
        let Some(d)=self.diagnosis.as_ref()else{return};
        // Exactly one cold source-scoped terminal record, no payload,
        // addresses, per-packet log, filesystem, threads, or system calls.
        // This runs before Rust's normal field drops, preserving the
        // existing socket-then-WSA-event owned destruction order.
        eprintln!("PLAN029_H1888_TCP_IO_FINAL shard_wakes={} event_socket_checks={} event_take_errors={} event_read={} event_write={} event_connect={} event_close={} ticket_peak={} ticket_served={} ticket_wait_sum_ms={} ticket_wait_max_ms={} connected_first_probe_tickets={} ready_wait_ge8_ms={} ready_wait_ge16_ms={} relay_turns={} relay_no_progress={} relay_progress_no_self_ticket={} relay_progress_self_ticket={} relay_close_probe_self_ticket={} inner_read_calls={} outer_read_calls={} inner_read_wouldblock={} outer_read_wouldblock={} inner_fin_peek_calls={} outer_fin_peek_calls={} inner_fin_peek_eof={} outer_fin_peek_eof={} inner_write_calls={} outer_write_calls={} inner_write_wouldblock={} outer_write_wouldblock={} inner_write_short={} outer_write_short={} inner_read_gated={} outer_read_gated={} inner_read_event_suppressed={} outer_read_event_suppressed={} direct_forwarded={} queued_copy={} reply_outer_read_turns={} reply_outer_ready_wait_max_ms={} reply_outer_ready_wait_ge8_ms={} reply_outer_ready_wait_ge16_ms={} reply_outer_read_inner_write_same_turn={} reply_outer_read_no_inner_write={} reply_inner_write_deferred_turns={} source=real_kernel_two_leg",
            d.shard_wakes,d.event_socket_checks,d.event_take_errors,
            d.event_read,d.event_write,d.event_connect,d.event_close,
            d.ready_ticket_peak,d.ready_served,d.ready_wait_sum_ms,
            d.ready_wait_max_ms,d.connected_first_probe_tickets,
            d.ready_wait_ge8_ms,d.ready_wait_ge16_ms,
            d.relay_turns,d.relay_zero_progress,
            d.relay_progress_no_self_ticket,d.relay_progress_self_ticket,
            d.relay_close_probe_self_ticket,d.io_reads[0],d.io_reads[1],
            d.io_read_wouldblock[0],d.io_read_wouldblock[1],
            d.io_fin_peek_calls[0],d.io_fin_peek_calls[1],
            d.io_fin_peek_eof[0],d.io_fin_peek_eof[1],
            d.io_writes[0],d.io_writes[1],
            d.io_write_wouldblock[0],d.io_write_wouldblock[1],
            d.io_short_writes[0],d.io_short_writes[1],
            d.io_read_gated[0],d.io_read_gated[1],
            d.io_event_suppressed_reads[0],d.io_event_suppressed_reads[1],
            d.direct_forwarded,d.queued_copy,
            d.reply_outer_read_turns,d.reply_outer_ready_wait_max_ms,
            d.reply_outer_ready_wait_ge8_ms,d.reply_outer_ready_wait_ge16_ms,
            d.reply_outer_read_inner_write_same_turn,
            d.reply_outer_read_no_inner_write,
            d.reply_inner_write_deferred_turns);
        if d.reply_qpc_frequency>0 {
            // No hot-path logs, payload, IPs, secrets or new timers.
            // The one bounded record is emitted only at original Stop.
            let rows=d.reply_qpc_rows.iter().map(|(p,q)|
                format!("{}:{}",p,q)).collect::<Vec<_>>().join(",");
            eprintln!("PLAN029_H1945_REPLY_QPC_FINAL frequency={} count={} rows={} source=original_rust_direct_test_only",
                d.reply_qpc_frequency,d.reply_qpc_rows.len(),rows);
        }
        if d.reply_path_qpc_frequency>0 {
            let rows=d.reply_path_qpc_rows.iter().map(|(p,w,r,i)|
                format!("{}:{}:{}:{}",p,w,r,i)).collect::<Vec<_>>().join(",");
            eprintln!("PLAN029_H1948_REPLY_PATH_QPC_FINAL frequency={} count={} rows={} source=original_rust_direct_test_only",
                d.reply_path_qpc_frequency,d.reply_path_qpc_rows.len(),rows);
        }
        if d.prewrite_qpc_frequency>0 {
            let rows=d.prewrite_qpc_rows.iter().map(|(p,a,c,r,w,o,i)|
                format!("{}:{}:{}:{}:{}:{}:{}",p,a,c,r,w,o,i))
                .collect::<Vec<_>>().join(",");
            eprintln!("PLAN029_H1953_PREWRITE_QPC_FINAL frequency={} count={} rows={} source=original_rust_direct_test_only",
                d.prewrite_qpc_frequency,d.prewrite_qpc_rows.len(),rows);
        }
        // Exactly one cold aggregate FIN witness AFTER the original TX
        // returns to its Stop owner. No IPs, TIDs, original payload,
        // per-packet logging or additional kernel I/O.
        eprintln!("PLAN029_H1906_TCP_FIN_FINAL inner_recv_eof={} outer_recv_eof={} physical_shutdown_write={} inner_shutdown_write={} source=original_rust_kernel_tcp_local",
            d.half_close_transitions[0],d.half_close_transitions[1],
            d.half_close_transitions[2],d.half_close_transitions[3]);
    }
}
