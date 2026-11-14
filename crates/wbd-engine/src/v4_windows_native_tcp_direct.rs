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
use wbd_platform::windows_direct_tcp::{
    PhysicalTcpSocket,ConnectProgress,TcpDirectRelay,open_kernel_tcp_listener,
};
use crate::v4_client_direct_tcp_nat::{DirectTcpNat,TcpNatKey};
use crate::v4_windows_native_dns_client_tcp::{ClientDnsTcp,NativeTcpDnsEndpoints};
use crate::v4_client_split::DnsEgress;
use crate::v4_client_fake_pool::FakeAllocator;
use crate::v4_client_fake_journal::FakeJournal;

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

enum TcpPhase{
    Connecting(TcpStream,PhysicalTcpSocket),
    Relaying(TcpDirectRelay),
}
struct Active{
    key:TcpNatKey,proxy_port:u16,phase:Option<TcpPhase>,
    last_activity_ms:u64,
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
}
pub(crate) struct NativeTcpActor{
    lease:u32,synthetic:u32,
    physical:Ipv4Addr,ifindex:u32,
    listener:TcpListener,nat:DirectTcpNat,
    pending:HashMap<u16,(TcpNatKey,u64)>,
    deadlines:VecDeque<(u16,u64)>,
    active:Vec<Active>,cursor:usize,
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
    diagnosis:Option<TcpLegDiagnosis>,
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
        Ok(Self{lease:u32::from(lease),synthetic:u32::from(synthetic),
            physical,ifindex,listener,nat,pending:HashMap::new(),
            deadlines:VecDeque::new(),active:Vec::new(),cursor:0,
            closing:ClosedNatGrace::default(),
            dns_nat,dns_pending:HashMap::new(),
            dns_deadlines:VecDeque::new(),dns_active:Vec::new(),
            dns_cursor:0,dns_closing:ClosedNatGrace::default(),
            dns_tunnel_sources:HashSet::new(),
            ready:VecDeque::with_capacity(MAX_READY),
            buffered_bytes:0,resident_bytes:0,
            diagnosis:(std::env::var("WBD_PLAN029_P2_RELAY_DIAG").ok()
                .as_deref()==Some("1")).then(TcpLegDiagnosis::default)})
    }
    /// A post-Apply generation-owned listener's actual ephemeral port.
    /// Never guess this value in Go or open a global firewall wildcard.
    pub(crate) fn listener_port(&self)->Result<u16,()>{
        self.listener.local_addr().map(|a|a.port()).map_err(|_|())
    }
    pub(crate) fn has_work(&self)->bool{
        // Closed NAT grace is metadata waiting for the kernel, not work
        // that warrants the original TX worker's 10ms active wait.
        !self.pending.is_empty()||!self.active.is_empty()||
            !self.dns_pending.is_empty()||!self.dns_active.is_empty()||
            !self.ready.is_empty()
    }
    pub(crate) fn next_close_due_ms(&self)->Option<u64>{
        match (self.closing.next_due(),self.dns_closing.next_due()){
            (Some(a),Some(b))=>Some(a.min(b)),
            (a,None)|(None,a)=>a,
        }
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
    fn enqueue(&mut self,wire:&[u8])->Result<(),()>{
        if self.ready.len()>=MAX_READY{return Err(())}
        self.ready.push_back(wire.to_vec());
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
        let mut rewritten=[0u8;MAX_L3];
        let (n,entry)=self.dns_nat.to_listener(packet,presented,
            now_ms,&mut rewritten).map_err(|_|())?;
        if self.enqueue(&rewritten[..n]).is_err(){
            if self.dns_nat.len()>prior{self.dns_nat.retire(entry.key);}
            return Err(())
        }
        if self.dns_nat.len()>prior{
            let due=now_ms.saturating_add(PENDING_MS);
            self.dns_pending.insert(entry.proxy_port,(entry.key,due));
            self.dns_deadlines.push_back((entry.proxy_port,due));
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
        if packet.len()<40||packet.len()>MAX_L3||self.ready.len()>=MAX_READY{
            return Err(())
        }
        let was=self.nat.len();
        let mut rewritten=[0u8;MAX_L3];
        let (n,entry)=self.nat.to_listener(packet,real,now_ms,&mut rewritten)
            .map_err(|_|())?;
        if self.enqueue(&rewritten[..n]).is_err(){
            if self.nat.len()>was{self.nat.retire(entry.key);}
            return Err(())
        }
        if self.nat.len()>was{
            let deadline=now_ms.saturating_add(PENDING_MS);
            self.pending.insert(entry.proxy_port,(entry.key,deadline));
            self.deadlines.push_back((entry.proxy_port,deadline));
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
        let mut rewritten=[0u8;MAX_L3];
        let n=match self.dns_nat.to_app(packet,&mut rewritten)
            .or_else(|_|self.nat.to_app(packet,&mut rewritten)){
            Ok((n,_))=>n,Err(_)=>return Some(Err(()))
        };
        Some(self.enqueue(&rewritten[..n]))
    }
    /// One existing owner tick services at most 8 accepted connections and
    /// 8 existing relays (bounded rotating quantum); no per-flow thread
    /// or whole-table polling on every Wintun packet.
    pub(crate) fn tick(&mut self,now_ms:u64)->TcpServiceTick{
        let mut retired=Vec::new();
        let mut advanced=false;
        for _ in 0..MAX_QUANTUM{
            let (stream,peer)=match self.listener.accept(){
                Ok(ok)=>{advanced=true;ok},
                Err(e) if e.kind()==ErrorKind::WouldBlock=>break,
                Err(_)=>break,
            };
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
            let dst=SocketAddrV4::new(Ipv4Addr::from(entry.real_dst),
                entry.key.target_port);
            match PhysicalTcpSocket::start(self.physical,self.ifindex,dst){
                Ok(socket)=>self.active.push(Active{
                    key:entry.key,proxy_port:entry.proxy_port,
                    phase:Some(TcpPhase::Connecting(stream,socket)),
                    last_activity_ms:now_ms,
                }),
                Err(_)=>{
                    self.nat.retire(entry.key);
                    retired.push(entry.key)
                }
            }
        }
        let count=self.active.len();
        let quantum=count.min(MAX_QUANTUM);
        let mut to_remove=Vec::new();
        for step in 0..quantum{
            let idx=(self.cursor+step)%count;
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
                            match outer.into_connected_stream()
                                .and_then(|outside|TcpDirectRelay::new(inner,outside)){
                                Ok(relay)=>{
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
                    let free=TCP_PENDING_POOL_LIMIT.saturating_sub(self.resident_bytes);
                    match pair.service_once_with_read_budget(free){
                        Ok(tick)=>{
                            let after=pair.resident_bytes();
                            let retained=self.resident_bytes
                                .saturating_sub(before).saturating_add(after);
                            if retained>TCP_PENDING_POOL_LIMIT{
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
                                d.read_inner=d.read_inner.saturating_add(tick.inner_read as u64);
                                d.read_outer=d.read_outer.saturating_add(tick.outer_read as u64);
                                d.wrote_inner=d.wrote_inner.saturating_add(tick.inner_write as u64);
                                d.wrote_outer=d.wrote_outer.saturating_add(tick.outer_write as u64);
                            }
                            self.buffered_bytes=self.buffered_bytes
                                .saturating_sub(previous).saturating_add(tick.buffered);
                            if tick.bytes_read>0||tick.bytes_written>0{
                                advanced=true;
                                flow.last_activity_ms=now_ms;
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
        // Remove descending to preserve the original bounded readiness
        // snapshot indices. Never drop a different live NAT association.
        to_remove.sort_unstable_by_key(|(idx,_)|*idx);
        to_remove.dedup_by_key(|(idx,_)|*idx);
        for (idx,keep_reverse) in to_remove.into_iter().rev(){
            let flow=self.active.remove(idx);
            if keep_reverse{
                // Closing the accepted kernel socket releases its user
                // buffers, but must NOT erase its synthetic reverse NAT
                // before Windows has delivered all TCP segments to Wintun.
                self.closing.defer(flow.proxy_port,flow.key,now_ms);
            }else if self.nat.retire(flow.key){
                retired.push(flow.key)
            }
        }
        if self.active.is_empty(){self.cursor=0}
        else{self.cursor=(self.cursor+quantum)%self.active.len()}
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
                eprintln!("PLAN029_H1839_NATIVE_TCP_LEGS active={} pending={} dns_active={} inner_read={} outer_read={} inner_write={} outer_write={} buffered={} resident={} source=real_kernel_two_leg",
                    self.active.len(),self.pending.len(),self.dns_active.len(),
                    d.read_inner,d.read_outer,d.wrote_inner,d.wrote_outer,
                    self.buffered_bytes,self.resident_bytes);
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
