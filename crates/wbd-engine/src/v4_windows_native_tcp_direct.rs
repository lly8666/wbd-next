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
const IDLE_MS:u64=120_000;

enum TcpPhase{
    Connecting(TcpStream,PhysicalTcpSocket),
    Relaying(TcpDirectRelay),
}
struct Active{
    key:TcpNatKey,phase:Option<TcpPhase>,last_activity_ms:u64,
}
pub(crate) struct NativeTcpActor{
    lease:u32,synthetic:u32,
    physical:Ipv4Addr,ifindex:u32,
    listener:TcpListener,nat:DirectTcpNat,
    pending:HashMap<u16,(TcpNatKey,u64)>,
    deadlines:VecDeque<(u16,u64)>,
    active:Vec<Active>,cursor:usize,
    ready:VecDeque<Vec<u8>>,
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
            ready:VecDeque::with_capacity(MAX_READY)})
    }
    pub(crate) fn has_work(&self)->bool{
        self.nat.len()>0||!self.ready.is_empty()
    }
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
                    key:entry.key,phase:Some(TcpPhase::Connecting(stream,socket)),
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
            if now_ms.saturating_sub(flow.last_activity_ms)>=IDLE_MS{
                to_remove.push(idx);
                continue
            }
            let Some(phase)=flow.phase.take()else{
                to_remove.push(idx);continue
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
                                Err(_)=>to_remove.push(idx),
                            }
                        },
                        Err(_)=>to_remove.push(idx),
                    }
                },
                TcpPhase::Relaying(mut pair)=>{
                    match pair.service_once(){
                        Ok(tick)=>{
                            if tick.bytes_read>0||tick.bytes_written>0{
                                flow.last_activity_ms=now_ms;
                            }
                            if tick.finished{to_remove.push(idx)}
                            else{flow.phase=Some(TcpPhase::Relaying(pair))}
                        },
                        Err(_)=>to_remove.push(idx),
                    }
                }
            }
        }
        // Remove descending to preserve the original bounded readiness
        // snapshot indices. Never drop a different live NAT association.
        to_remove.sort_unstable();to_remove.dedup();
        for idx in to_remove.into_iter().rev(){
            let flow=self.active.remove(idx);
            self.nat.retire(flow.key);
            retired.push(flow.key)
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
        retired
    }
}
#[cfg(test)]
mod tests{
    use super::*;
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
