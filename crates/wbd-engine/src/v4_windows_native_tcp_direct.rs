//! PLAN029 Windows kernel TCP Direct implementation, not a user-space TCP
//! stack. One ORIGINAL Rust Wintun TX owns NAT, one Windows kernel listener,
//! physical-source-bound nonblocking sockets, and bounded read/write relays.
//! The sole original Rust RX still owns every Wintun SendPacket via mailbox.
//! Activation REQUIRES a generation-owned synthetic /32 route AND exact
//! Defender Allow prior to first Direct SYN. Until the Go owner can prove
//! both, the cold V3 actor remains disabled and Direct TCP fails closed.
use std::collections::{HashMap,VecDeque};
use std::io::ErrorKind;
use std::net::{Ipv4Addr,SocketAddr,SocketAddrV4,TcpListener,TcpStream};
use wbd_platform::windows_direct_tcp::{
    PhysicalTcpSocket,ConnectProgress,TcpDirectRelay,open_kernel_tcp_listener,
};
use crate::v4_client_direct_tcp_nat::{DirectTcpNat,TcpNatKey};

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
pub(crate) struct NativeTcpActor{
    lease:u32,synthetic:u32,
    physical:Ipv4Addr,ifindex:u32,
    listener:TcpListener,nat:DirectTcpNat,
    pending:HashMap<u16,(TcpNatKey,u64)>,
    deadlines:VecDeque<(u16,u64)>,
    active:Vec<Active>,cursor:usize,
    closing:ClosedNatGrace,
    ready:VecDeque<Vec<u8>>,
    buffered_bytes:usize,
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
        Ok(Self{lease:u32::from(lease),synthetic:u32::from(synthetic),
            physical,ifindex,listener,nat,pending:HashMap::new(),
            deadlines:VecDeque::new(),active:Vec::new(),cursor:0,
            closing:ClosedNatGrace::default(),
            ready:VecDeque::with_capacity(MAX_READY),buffered_bytes:0})
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
            !self.ready.is_empty()
    }
    pub(crate) fn next_close_due_ms(&self)->Option<u64>{
        self.closing.next_due()
    }
    pub(crate) fn buffered_bytes(&self)->usize{self.buffered_bytes}
    pub(crate) fn ready_pop(&mut self)->Option<Vec<u8>>{
        self.ready.pop_front()
    }
    /// All kernel-side L3 writes enqueue bytes, never borrow a second
    /// Wintun session, and never block an authenticated Tunnel DATA batch.
    fn enqueue(&mut self,wire:&[u8])->Result<(),()>{
        if self.ready.len()>=MAX_READY{return Err(())}
        self.ready.push_back(wire.to_vec());
        Ok(())
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
        let n=match self.nat.to_app(packet,&mut rewritten){
            Ok((n,_))=>n,Err(_)=>return Some(Err(()))
        };
        Some(self.enqueue(&rewritten[..n]))
    }
    /// One existing owner tick services at most 8 accepted connections and
    /// 8 existing relays (bounded rotating quantum); no per-flow thread
    /// or whole-table polling on every Wintun packet.
    pub(crate) fn tick(&mut self,now_ms:u64)->Vec<TcpNatKey>{
        let mut retired=Vec::new();
        for _ in 0..MAX_QUANTUM{
            let (stream,peer)=match self.listener.accept(){
                Ok(ok)=>ok,
                Err(e) if e.kind()==ErrorKind::WouldBlock=>break,
                Err(_)=>break,
            };
            let SocketAddr::V4(peer)=peer else{continue};
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
                    let previous=pair.pending_bytes();
                    let free=TCP_PENDING_POOL_LIMIT.saturating_sub(self.buffered_bytes);
                    match pair.service_once_with_read_budget(free){
                        Ok(tick)=>{
                            self.buffered_bytes=self.buffered_bytes
                                .saturating_sub(previous).saturating_add(tick.buffered);
                            debug_assert!(self.buffered_bytes<=TCP_PENDING_POOL_LIMIT);
                            if tick.bytes_read>0||tick.bytes_written>0{
                                flow.last_activity_ms=now_ms;
                            }
                            if tick.finished{to_remove.push((idx,true))}
                            else{flow.phase=Some(TcpPhase::Relaying(pair))}
                        },
                        Err(_)=>{
                            self.buffered_bytes=self.buffered_bytes.saturating_sub(previous);
                            // The kernel may still need to deliver RST/FIN
                            // and reverse ACKs after an accepted relay fails.
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
        retired
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
