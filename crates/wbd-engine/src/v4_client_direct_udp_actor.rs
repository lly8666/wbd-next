//! PLAN029 Direct-only UDP physical socket actor.
//! Intended to be owned by one original-generation Rust I/O scheduler,
//! NEVER a second Wintun reader or a Go packet pump. One socket per live
//! original five-tuple, with its original presented FakeIP retained for
//! exact reverse. No source/ifindex fallback and no tunnel reclassification.
//! Socket readiness uses one WSAPoll batch rather than per-flow OS threads.
//! Not activated in the authenticated NativeOwner until the cold policy
//! ABI, forced Tunnel DNS and Stop generations are wired and proven.
use std::net::{Ipv4Addr,SocketAddrV4};
use std::collections::HashMap;
use std::io::ErrorKind;
use wbd_platform::windows_direct_udp::{
    DirectUdpError,DirectUdpTuple,PhysicalUdpSocket,
    parse_owned_ipv4_udp,encode_reverse_ipv4_udp,
};

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) enum NativeUdpFault{
    BadUnderlay,
    InvalidOriginal,
    Capacity,
    Socket(DirectUdpError),
    LocalSend,
    RemoteReceive,
    DatagramTooLarge,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq,Hash)]
struct UdpFlowKey{
    source:u32,source_port:u16,
    presented:u32,destination_port:u16,
}
impl From<DirectUdpTuple> for UdpFlowKey{
    fn from(t:DirectUdpTuple)->Self{
        Self{source:u32::from(t.client_ip),source_port:t.client_port,
            presented:u32::from(t.presented_ip),
            destination_port:t.target_port}
    }
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) struct NativeUdpBudget{
    pub hard_flows:usize,
    pub rx_quantum:usize,
    pub ttl_ms:u64,
    pub inner_mtu:usize,
}
impl NativeUdpBudget{
    fn valid(self)->bool{
        (1..=16_384).contains(&self.hard_flows) &&
        (1..=64).contains(&self.rx_quantum) &&
        (5_000..=600_000).contains(&self.ttl_ms) &&
        (576..=1500).contains(&self.inner_mtu)
    }
}
struct UdpFlow{
    key:UdpFlowKey,
    tuple:DirectUdpTuple,
    real4:u32,
    socket:PhysicalUdpSocket,
    last_used_ms:u64,
}
#[cfg(target_os="windows")]
#[repr(C)]
#[derive(Clone,Copy)]
struct PollFd{
    socket:usize,
    events:i16,
    revents:i16,
}
#[cfg(target_os="windows")]
#[link(name="Ws2_32")]
extern "system"{
    fn WSAPoll(fd_array:*mut PollFd,fds:u32,timeout:i32)->i32;
}
const POLLRDNORM:i16=0x0100;
const POLLERR:i16=0x0001;
const POLLHUP:i16=0x0002;
const POLLNVAL:i16=0x0004;

/// This actor is intentionally !Sync: only its one Rust native I/O owner
/// mutates socket/flow policy. Other actors must hand over copied bounded
/// datagrams, never a borrowed WintunReceivePacket pointer.
pub(crate) struct DirectUdpActor{
    physical_source:Ipv4Addr,
    physical_ifindex:u32,
    lease4:Ipv4Addr,
    fake_bounds:(u32,u32),
    budget:NativeUdpBudget,
    flow_index:HashMap<UdpFlowKey,usize>,
    flows:Vec<UdpFlow>,
    #[cfg(target_os="windows")]
    poll_fds:Vec<PollFd>,
    poll_dirty:bool,
    scan_cursor:usize,
    next_ipv4_id:u16,
}
impl DirectUdpActor{
    pub fn new(source:Ipv4Addr,ifindex:u32,lease4:Ipv4Addr,
        fake_bounds:(u32,u32),budget:NativeUdpBudget)
        ->Result<Self,NativeUdpFault>{
        if !budget.valid()||ifindex==0||
            source.is_loopback()||source.is_multicast()||
            source.is_unspecified()||source.is_broadcast()||
            lease4.is_unspecified()||lease4.is_multicast()||
            lease4==source||fake_bounds.0>fake_bounds.1||
            (fake_bounds.0..=fake_bounds.1).contains(&u32::from(lease4))||
            (fake_bounds.0..=fake_bounds.1).contains(&u32::from(source)){
            return Err(NativeUdpFault::BadUnderlay)
        }
        Ok(Self{physical_source:source,physical_ifindex:ifindex,
            lease4,fake_bounds,budget,
            flow_index:HashMap::new(),flows:Vec::new(),
            #[cfg(target_os="windows")]poll_fds:Vec::new(),
            poll_dirty:false,scan_cursor:0,next_ipv4_id:1})
    }
    pub fn len(&self)->usize{self.flows.len()}
    pub fn max_flows(&self)->usize{self.budget.hard_flows}
    fn discard_index(&mut self,index:usize){
        let removed=self.flows.swap_remove(index);
        self.flow_index.remove(&removed.key);
        if index<self.flows.len(){
            self.flow_index.insert(self.flows[index].key,index);
        }
        self.poll_dirty=true;
        if !self.flows.is_empty(){self.scan_cursor%=self.flows.len()}
        else{self.scan_cursor=0}
    }
    /// Packet is a COPY after Wintun RX has released its borrowed loan.
    /// The real destination comes ONLY from already-pinned Direct policy:
    /// a FakeIP or original presentation must never be used as the socket
    /// remote address. A full/failed Direct socket is never Tunnel fallback.
    pub fn send_direct_datagram(&mut self,packet:&[u8],
        presented4:Ipv4Addr,real4:Ipv4Addr,
        now_ms:u64)->Result<(),NativeUdpFault>{
        // Direct real-IP business may have real==presented. A presented
        // FakeIP NEVER equals the socket destination or escapes physical:
        // reject any remote inside the owned local synthetic pool.
        if real4.is_unspecified()||real4.is_multicast()||
            real4.is_broadcast()||real4.is_loopback()||
            (self.fake_bounds.0..=self.fake_bounds.1)
                .contains(&u32::from(real4)){
            return Err(NativeUdpFault::InvalidOriginal)
        }
        let parsed=parse_owned_ipv4_udp(packet,self.lease4,presented4)
            .map_err(NativeUdpFault::Socket)?;
        // Ordinary captured port 53 is a DNS PURPOSE. Only the separate
        // QNAME-aware resolver dispatcher may use a physical DNS socket;
        // do not leak its raw query through a normal Direct-UDP flow.
        if parsed.tuple.target_port==53{
            return Err(NativeUdpFault::InvalidOriginal)
        }
        if parsed.data.len()+28>self.budget.inner_mtu {
            return Err(NativeUdpFault::DatagramTooLarge)
        }
        let key=UdpFlowKey::from(parsed.tuple);
        let index=match self.flow_index.get(&key).copied(){
            Some(i)=>{
                if self.flows[i].real4!=u32::from(real4){
                    return Err(NativeUdpFault::InvalidOriginal)
                }
                i
            }
            None=>{
                if self.flows.len()>=self.budget.hard_flows{
                    return Err(NativeUdpFault::Capacity)
                }
                let remote=SocketAddrV4::new(real4,parsed.tuple.target_port);
                let socket=PhysicalUdpSocket::open(
                    self.physical_source,self.physical_ifindex,remote
                ).map_err(NativeUdpFault::Socket)?;
                let i=self.flows.len();
                self.flows.push(UdpFlow{key,tuple:parsed.tuple,
                    real4:u32::from(real4),socket,last_used_ms:now_ms});
                self.flow_index.insert(key,i);
                self.poll_dirty=true;i
            }
        };
        let flow=&mut self.flows[index];
        flow.last_used_ms=now_ms;
        match flow.socket.send_ready(parsed.data){
            Ok(n) if n==parsed.data.len()=>Ok(()),
            // Datagram-specific nonblocking pressure cannot stall other
            // Direct sockets, DNS queries or Tunnel; caller records a
            // locally dropped UDP datagram, never a fabricated success.
            Err(e) if e.kind()==ErrorKind::WouldBlock=>{
                Err(NativeUdpFault::LocalSend)
            }
            _=>{self.discard_index(index);Err(NativeUdpFault::LocalSend)}
        }
    }
    #[cfg(target_os="windows")]
    fn refresh_poll(&mut self){
        if !self.poll_dirty{return}
        self.poll_fds=self.flows.iter().map(|flow|PollFd{
            socket:flow.socket.poll_socket(),
            events:POLLRDNORM,revents:0,
        }).collect();
        self.poll_dirty=false;
    }
    /// ONE readiness quantum. Physical responses are prepared as complete
    /// L3 bytes into caller-owned storage; only the ORIGINAL authenticated
    /// Rust Wintun TX owner may AllocateSendPacket afterward. Does not
    /// acquire Wintun slots, wait for network I/O or call Go.
    #[cfg(target_os="windows")]
    pub fn poll_reverse_ready(&mut self,out:&mut [u8],now_ms:u64)
        ->Result<Option<usize>,NativeUdpFault>{
        if self.flows.is_empty(){return Ok(None)}
        self.refresh_poll();
        let rc=unsafe{WSAPoll(self.poll_fds.as_mut_ptr(),
            self.poll_fds.len() as u32,0)};
        if rc<0{return Err(NativeUdpFault::RemoteReceive)}
        if rc==0{return Ok(None)}
        let count=self.flows.len();
        for step in 0..count.min(self.budget.rx_quantum){
            let i=(self.scan_cursor+step)%count;
            let flags=self.poll_fds[i].revents;
            if flags&POLLRDNORM==0{
                if flags&(POLLERR|POLLHUP|POLLNVAL)!=0{
                    self.discard_index(i);
                    return Err(NativeUdpFault::RemoteReceive)
                }
                continue
            }
            // A single bounded packet, not a socket read loop. If this
            // flow is continuously ready it consumes at most one packet
            // per service turn; other flows remain on the ready list.
            let mut buf=[0u8;2048];
            let flow=&mut self.flows[i];
            let n=match flow.socket.receive_ready(&mut buf){
                Ok(n)=>n,
                Err(e) if e.kind()==ErrorKind::WouldBlock=>continue,
                Err(_)=>{
                    self.discard_index(i);
                    return Err(NativeUdpFault::RemoteReceive)
                }
            };
            if n+28>self.budget.inner_mtu{
                self.discard_index(i);
                return Err(NativeUdpFault::DatagramTooLarge)
            }
            let bytes=encode_reverse_ipv4_udp(
                flow.tuple,&buf[..n],self.next_ipv4_id,
                self.budget.inner_mtu,out
            ).map_err(NativeUdpFault::Socket)?;
            self.next_ipv4_id=self.next_ipv4_id.wrapping_add(1);
            flow.last_used_ms=now_ms;
            self.scan_cursor=(i+1)%count;
            return Ok(Some(bytes))
        }
        self.scan_cursor=(self.scan_cursor+self.budget.rx_quantum)%count;
        Ok(None)
    }
    /// One coarse scheduler tick, no whole-flow-table scan. At most budget
    /// previously admitted sockets are inspected, not each DATA packet.
    pub fn expire_some(&mut self,now_ms:u64,budget:usize)->usize{
        let mut evicted=0;
        for _ in 0..budget.min(1024){
            if self.flows.is_empty(){break}
            let idx=self.scan_cursor%self.flows.len();
            if now_ms.saturating_sub(self.flows[idx].last_used_ms)>=
               self.budget.ttl_ms{
                self.discard_index(idx);
                evicted+=1;
            }else{
                self.scan_cursor=(idx+1)%self.flows.len();
            }
        }
        evicted
    }
    pub fn stop(mut self)->usize{
        let n=self.flows.len();
        self.flows.clear();
        self.flow_index.clear();
        n
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    fn underlay()->NativeUdpBudget{
        NativeUdpBudget{hard_flows:64,rx_quantum:16,
            ttl_ms:60_000,inner_mtu:1280}
    }
    #[test]
    fn plan029_actor_never_sends_local_fake_or_raw_dns53_on_physical_socket(){
        let lease=Ipv4Addr::new(10,234,12,34);
        let fake=Ipv4Addr::new(198,18,0,9);
        let pool=(u32::from_be_bytes([198,18,0,0]),
            u32::from_be_bytes([198,18,255,255]));
        let mut actor=DirectUdpActor::new(
            Ipv4Addr::new(10,1,0,7),14,lease,pool,underlay()
        ).unwrap();
        let mut packet=[0u8;28];
        packet[0]=0x45;
        packet[2..4].copy_from_slice(&28u16.to_be_bytes());
        packet[9]=17;
        packet[12..16].copy_from_slice(&lease.octets());
        packet[16..20].copy_from_slice(&fake.octets());
        packet[20..22].copy_from_slice(&34567u16.to_be_bytes());
        packet[22..24].copy_from_slice(&9000u16.to_be_bytes());
        packet[24..26].copy_from_slice(&8u16.to_be_bytes());
        // The physical socket target is always the REAL selected address,
        // never the local fake; reject before CreateSocket.
        assert_eq!(actor.send_direct_datagram(&packet,fake,fake,0),
            Err(NativeUdpFault::InvalidOriginal));
        assert_eq!(actor.len(),0);
        packet[22..24].copy_from_slice(&53u16.to_be_bytes());
        assert_eq!(actor.send_direct_datagram(&packet,fake,
            Ipv4Addr::new(203,0,113,2),0),
            Err(NativeUdpFault::InvalidOriginal));
        assert_eq!(actor.len(),0);
        packet[12..16].copy_from_slice(&Ipv4Addr::new(10,2,0,1).octets());
        assert_eq!(actor.send_direct_datagram(&packet,fake,
            Ipv4Addr::new(203,0,113,2),1),
            Err(NativeUdpFault::Socket(DirectUdpError::WrongSourceLease)));
        assert_eq!(actor.len(),0);
        assert_eq!(actor.expire_some(500_000,128),0);
    }
    #[test]
    fn plan029_actor_rejects_unbounded_flow_and_unsafe_physical_defaults(){
        let src=Ipv4Addr::new(10,1,0,7);
        let lease=Ipv4Addr::new(10,234,12,34);
        let pool=(u32::from_be_bytes([198,18,0,0]),
            u32::from_be_bytes([198,18,255,255]));
        assert!(matches!(DirectUdpActor::new(Ipv4Addr::LOCALHOST,15,
            lease,pool,underlay()),Err(NativeUdpFault::BadUnderlay)));
        assert!(matches!(DirectUdpActor::new(src,0,lease,pool,underlay()),
            Err(NativeUdpFault::BadUnderlay)));
        let mut cap=underlay();cap.hard_flows=16_385;
        assert!(matches!(DirectUdpActor::new(src,14,lease,pool,cap),
            Err(NativeUdpFault::BadUnderlay)));
        let actor=DirectUdpActor::new(src,14,lease,pool,underlay()).unwrap();
        assert_eq!(actor.len(),0);
        assert_eq!(actor.max_flows(),64);
        assert_eq!(actor.stop(),0);
    }
}
