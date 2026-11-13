//! PLAN029 one Windows physical UDP socket half and exact IPv4/UDP inverse.
//! No second Wintun session, no per-flow Go FFI and no hidden tunnel fallback.
//! The original Rust ingress/owner MUST call this from its one bounded IO
//! scheduler and join/close it before the current-generation Wintun loan Stop.
//! This module alone does NOT qualify a product Direct UDP exit.
use std::net::Ipv4Addr;

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub enum DirectUdpError {
    InvalidPacket,
    WrongSourceLease,
    WrongDestination,
    FragmentNeedsReassembly,
    InvalidRemote,
    PacketTooLarge,
    SocketBind,
    InterfaceBind,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct DirectUdpTuple {
    pub client_ip:Ipv4Addr,
    pub client_port:u16,
    /// IPv4 presented to the caller (possibly an announced FakeIP); must
    /// never appear as the remote physical socket's destination.
    pub presented_ip:Ipv4Addr,
    pub target_port:u16,
}
#[derive(Clone,Copy,Debug)]
pub struct DirectUdpPayload<'a>{
    pub tuple:DirectUdpTuple,
    pub data:&'a [u8],
}
fn read16(x:&[u8])->u16{u16::from_be_bytes([x[0],x[1]])}
fn checksum(parts:&[&[u8]])->u16{
    let mut sum=0u32;
    for part in parts {
        let mut chunks=part.chunks_exact(2);
        for word in &mut chunks{
            sum+=u32::from(read16(word));
        }
        if let Some(&last)=chunks.remainder().first(){
            sum+=u32::from(last)<<8
        }
    }
    while sum>>16!=0{sum=(sum&0xffff)+(sum>>16)}
    !(sum as u16)
}
pub fn parse_owned_ipv4_udp(packet:&[u8],lease:Ipv4Addr,
    presented:Ipv4Addr)->Result<DirectUdpPayload<'_>,DirectUdpError>{
    if packet.len()<28||packet.len()>65535||packet[0]>>4!=4||
       packet[9]!=17{return Err(DirectUdpError::InvalidPacket)}
    let ihl=usize::from(packet[0]&15)*4;
    if ihl<20||ihl+8>packet.len()||usize::from(read16(&packet[2..4]))!=packet.len(){
        return Err(DirectUdpError::InvalidPacket)
    }
    if (read16(&packet[6..8])&0x3fff)!=0{
        return Err(DirectUdpError::FragmentNeedsReassembly)
    }
    let src=Ipv4Addr::new(packet[12],packet[13],packet[14],packet[15]);
    if src!=lease{return Err(DirectUdpError::WrongSourceLease)}
    let dst=Ipv4Addr::new(packet[16],packet[17],packet[18],packet[19]);
    if dst!=presented{return Err(DirectUdpError::WrongDestination)}
    let udp=&packet[ihl..];
    if read16(&udp[4..6]) as usize!=udp.len()||read16(&udp[2..4])==0||
       read16(&udp[..2])==0{
        return Err(DirectUdpError::InvalidPacket)
    }
    Ok(DirectUdpPayload{
        tuple:DirectUdpTuple{
            client_ip:src,client_port:read16(&udp[..2]),
            presented_ip:dst,target_port:read16(&udp[2..4]),
        },
        data:&udp[8..],
    })
}
/// Build the actual L3 reverse packet ONLY after a physical UDP socket has
/// confirmed that bytes arrived from this flow's connected remote address.
/// No Wintun slot is allocated here. The caller must prepare bytes first,
/// then AllocateSendPacket, immediate copy and SendPacket.
pub fn encode_reverse_ipv4_udp(tuple:DirectUdpTuple,data:&[u8],ip_id:u16,
    inner_mtu:usize,out:&mut [u8])->Result<usize,DirectUdpError>{
    let total=28usize.checked_add(data.len()).ok_or(DirectUdpError::PacketTooLarge)?;
    if total>65535||total>inner_mtu||total>out.len()||tuple.client_port==0||
       tuple.target_port==0{return Err(DirectUdpError::PacketTooLarge)}
    let (head,rest)=out[..total].split_at_mut(20);
    let (udp,body)=rest.split_at_mut(8);
    head.fill(0);head[0]=0x45;
    head[2..4].copy_from_slice(&(total as u16).to_be_bytes());
    head[4..6].copy_from_slice(&ip_id.to_be_bytes());
    head[6..8].copy_from_slice(&0x4000u16.to_be_bytes()); // DF=1
    head[8]=64;head[9]=17;
    head[12..16].copy_from_slice(&tuple.presented_ip.octets());
    head[16..20].copy_from_slice(&tuple.client_ip.octets());
    let ip_checksum=checksum(&[head]);
    head[10..12].copy_from_slice(&ip_checksum.to_be_bytes());
    udp[0..2].copy_from_slice(&tuple.target_port.to_be_bytes());
    udp[2..4].copy_from_slice(&tuple.client_port.to_be_bytes());
    udp[4..6].copy_from_slice(&((data.len()+8) as u16).to_be_bytes());
    udp[6..8].fill(0);
    body.copy_from_slice(data);
    let mut pseudo=[0u8;12];
    pseudo[..4].copy_from_slice(&tuple.presented_ip.octets());
    pseudo[4..8].copy_from_slice(&tuple.client_ip.octets());
    pseudo[9]=17;
    pseudo[10..12].copy_from_slice(&((data.len()+8) as u16).to_be_bytes());
    let c=checksum(&[&pseudo,udp,body]);
    // An all-zero UDP checksum is encoded as 0xffff, not "disabled".
    udp[6..8].copy_from_slice(&(if c==0{0xffff}else{c}).to_be_bytes());
    Ok(total)
}

#[cfg(target_os="windows")]
mod win{
    use super::DirectUdpError;
    use std::net::{Ipv4Addr,SocketAddr,SocketAddrV4,UdpSocket};
    use std::os::windows::io::AsRawSocket;
    #[link(name="Ws2_32")]
    extern "system" {
        fn setsockopt(socket:usize,level:i32,optname:i32,value:*const i8,len:i32)->i32;
        fn getsockopt(socket:usize,level:i32,optname:i32,value:*mut i8,len:*mut i32)->i32;
    }
    // IPPROTO_IP=0, IP_UNICAST_IF=31. Windows expects an interface index in
    // network byte order, not an IPv4 address or a host-order DWORD.
    const IP_UNICAST_IF:i32=31;
    /// One cold-created nonblocking socket, physically source-bound and
    /// connected to ONE real remote IPv4. Windows filters nonmatching peer
    /// responses in kernel. Never share a socket between different clients.
    pub struct PhysicalUdpSocket{
        socket:UdpSocket,
        physical_src:Ipv4Addr,
        interface_index:u32,
        remote:SocketAddrV4,
    }
    impl PhysicalUdpSocket{
        pub fn open(physical_src:Ipv4Addr,ifindex:u32,
            remote:SocketAddrV4)->Result<Self,DirectUdpError>{
            if ifindex==0||ifindex==u32::MAX||physical_src.is_unspecified()||
               physical_src.is_multicast()||physical_src.is_broadcast()||
               physical_src.is_loopback()||remote.ip().is_unspecified()||
               remote.ip().is_multicast()||remote.port()==0{
                return Err(DirectUdpError::InvalidRemote)
            }
            let sock=UdpSocket::bind(SocketAddrV4::new(physical_src,0))
                .map_err(|_|DirectUdpError::SocketBind)?;
            let native=sock.as_raw_socket() as usize;
            let network_index=ifindex.to_be();
            let ret=unsafe{setsockopt(native,0,IP_UNICAST_IF,
                (&network_index as *const u32).cast(),4)};
            if ret!=0{return Err(DirectUdpError::InterfaceBind)}
            let mut observed=0u32;
            let mut size=4i32;
            let ret=unsafe{getsockopt(native,0,IP_UNICAST_IF,
                (&mut observed as *mut u32).cast(),&mut size)};
            if ret!=0||size!=4||u32::from_be(observed)!=ifindex{
                return Err(DirectUdpError::InterfaceBind)
            }
            sock.connect(remote).map_err(|_|DirectUdpError::InterfaceBind)?;
            sock.set_nonblocking(true).map_err(|_|DirectUdpError::SocketBind)?;
            Ok(Self{socket:sock,physical_src,interface_index:ifindex,remote})
        }
        pub fn local_addr(&self)->Result<SocketAddrV4,DirectUdpError>{
            match self.socket.local_addr().map_err(|_|DirectUdpError::SocketBind)?{
                SocketAddr::V4(v)=>Ok(v),_=>Err(DirectUdpError::SocketBind)
            }
        }
        pub fn selected_underlay(&self)->(Ipv4Addr,u32){(self.physical_src,self.interface_index)}
        pub fn remote(&self)->SocketAddrV4{self.remote}
        pub fn send_ready(&self,data:&[u8])->std::io::Result<usize>{
            // Nonblocking and no hidden queue/retry or tunnel fallback.
            self.socket.send(data)
        }
        pub fn receive_ready(&self,into:&mut [u8])->std::io::Result<usize>{
            self.socket.recv(into)
        }
    }
    #[cfg(test)]
    mod tests {
        use super::*;
        #[test]
        fn plan029_physical_udp_binder_never_uses_unknown_nic_or_loopback(){
            let remote=SocketAddrV4::new(Ipv4Addr::new(203,0,113,2),53);
            assert!(matches!(PhysicalUdpSocket::open(Ipv4Addr::new(10,1,0,10),0,remote),
                Err(DirectUdpError::InvalidRemote)));
            assert!(matches!(PhysicalUdpSocket::open(Ipv4Addr::LOCALHOST,9,remote),
                Err(DirectUdpError::InvalidRemote)));
        }
    }
}
#[cfg(target_os="windows")]
pub use win::PhysicalUdpSocket;

#[cfg(test)]
mod tests{
    use super::*;
    fn sum4(x:&[u8])->u16{checksum(&[x])}
    #[test]
    fn plan029_reverse_physical_udp_preserves_announced_fake_and_valid_checksums(){
        let tuple=DirectUdpTuple{
            client_ip:Ipv4Addr::new(10,234,12,34),client_port:44001,
            presented_ip:Ipv4Addr::new(198,18,9,77),target_port:9999,
        };
        let mut back=[0u8;1500];
        let n=encode_reverse_ipv4_udp(tuple,b"actual-remote-udp",27,1460,&mut back).unwrap();
        assert_eq!(n,45);
        assert_eq!(&back[12..16],&tuple.presented_ip.octets());
        assert_eq!(&back[16..20],&tuple.client_ip.octets());
        assert_eq!(read16(&back[20..22]),tuple.target_port);
        assert_eq!(read16(&back[22..24]),tuple.client_port);
        assert_eq!(sum4(&back[..20]),0);
        let mut pseudo=[0u8;12];
        pseudo[..4].copy_from_slice(&tuple.presented_ip.octets());
        pseudo[4..8].copy_from_slice(&tuple.client_ip.octets());
        pseudo[9]=17;pseudo[10..12].copy_from_slice(&((n-20) as u16).to_be_bytes());
        assert_eq!(checksum(&[&pseudo,&back[20..n]]),0);
        assert_eq!(encode_reverse_ipv4_udp(tuple,&vec![0u8;1400],7,1280,&mut back),
            Err(DirectUdpError::PacketTooLarge));
    }
    #[test]
    fn plan029_direct_udp_requires_exact_lease_port_ipv4_and_no_fragments(){
        let tuple=DirectUdpTuple{
            client_ip:Ipv4Addr::new(10,234,12,34),client_port:44001,
            presented_ip:Ipv4Addr::new(203,0,113,9),target_port:53,
        };
        let mut out=[0u8;100];
        let n=encode_reverse_ipv4_udp(tuple,b"payload",2,1500,&mut out).unwrap();
        // Exchange addresses and ports for a test forward request.
        out[12..16].copy_from_slice(&tuple.client_ip.octets());
        out[16..20].copy_from_slice(&tuple.presented_ip.octets());
        out[20..22].copy_from_slice(&tuple.client_port.to_be_bytes());
        out[22..24].copy_from_slice(&tuple.target_port.to_be_bytes());
        let req=parse_owned_ipv4_udp(&out[..n],tuple.client_ip,tuple.presented_ip).unwrap();
        assert_eq!(req.data,b"payload");
        assert_eq!(req.tuple,tuple);
        assert_eq!(parse_owned_ipv4_udp(&out[..n],Ipv4Addr::new(10,1,0,1),tuple.presented_ip),
            Err(DirectUdpError::WrongSourceLease));
        assert_eq!(parse_owned_ipv4_udp(&out[..n],tuple.client_ip,Ipv4Addr::new(8,8,8,8)),
            Err(DirectUdpError::WrongDestination));
        out[6..8].copy_from_slice(&0x2000u16.to_be_bytes());
        assert_eq!(parse_owned_ipv4_udp(&out[..n],tuple.client_ip,tuple.presented_ip),
            Err(DirectUdpError::FragmentNeedsReassembly));
    }
}
