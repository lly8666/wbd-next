//! PLAN029 DNS UDP TC=1 same-endpoint TCP fallback, owned by the single
//! original Rust Direct DNS scheduler. No detached DNS thread, no alternate
//! resolver, no system DNS, no Wintun slot across connect/read/write.
//! Source/ifindex binding is identical to the physical Direct UDP socket.
use std::io::{Read,Write,ErrorKind};
use std::net::{Ipv4Addr,SocketAddrV4,TcpStream};
use wbd_platform::windows_direct_tcp::{PhysicalTcpSocket,ConnectProgress};

const MAX_DNS_WIRE:usize=2048-28;
#[derive(Clone,Debug)]
struct DnsTcpFrame{
    request:Vec<u8>,
    sent:usize,
    received:Vec<u8>,
}
impl DnsTcpFrame{
    fn new(query:&[u8])->Option<Self>{
        if query.len()<12||query.len()>MAX_DNS_WIRE{return None}
        let mut request=Vec::with_capacity(query.len()+2);
        request.extend_from_slice(&(query.len() as u16).to_be_bytes());
        request.extend_from_slice(query);
        Some(Self{request,sent:0,received:Vec::new()})
    }
    fn take_answer(&mut self,chunk:&[u8])->Result<Option<Vec<u8>>,()>{
        if self.received.len()+chunk.len()>MAX_DNS_WIRE+2{return Err(())}
        self.received.extend_from_slice(chunk);
        if self.received.len()<2{return Ok(None)}
        let n=u16::from_be_bytes([self.received[0],self.received[1]]) as usize;
        if !(12..=MAX_DNS_WIRE).contains(&n){return Err(())}
        if self.received.len()>n+2{return Err(())}
        if self.received.len()<n+2{return Ok(None)}
        Ok(Some(self.received[2..].to_vec()))
    }
}
#[derive(Debug,Eq,PartialEq)]
pub(crate) enum TcpDnsPoll{Pending,Answer(Vec<u8>),Failed}
pub(crate) struct TcpDnsFallback {
    connecting:Option<PhysicalTcpSocket>,
    stream:Option<TcpStream>,
    framed:DnsTcpFrame,
}
impl TcpDnsFallback{
    pub(crate) fn start(source:Ipv4Addr,ifindex:u32,endpoint:Ipv4Addr,
        query:&[u8])->Result<Self,()>{
        let frame=DnsTcpFrame::new(query).ok_or(())?;
        let socket=PhysicalTcpSocket::start(source,ifindex,
            SocketAddrV4::new(endpoint,53)).map_err(|_|())?;
        Ok(Self{connecting:Some(socket),stream:None,framed:frame})
    }
    /// One readiness-only bounded turn. The physical connect uses
    /// zero-time WSAPoll+SO_ERROR, then at most one nonblocking write and
    /// read. A large/invalid answer fails just this ticket; no fallback.
    pub(crate) fn poll(&mut self)->TcpDnsPoll{
        if let Some(mut socket)=self.connecting.take(){
            match socket.poll_connected(){
                Ok(ConnectProgress::Pending)=>{
                    self.connecting=Some(socket);
                    return TcpDnsPoll::Pending
                },
                Ok(ConnectProgress::Connected)=>{
                    match socket.into_connected_stream(){
                        Ok(stream)=>self.stream=Some(stream),
                        Err(_)=>return TcpDnsPoll::Failed,
                    }
                },
                Err(_)=>return TcpDnsPoll::Failed,
            }
        }
        let Some(stream)=self.stream.as_mut()else{return TcpDnsPoll::Failed};
        if self.framed.sent<self.framed.request.len(){
            match stream.write(&self.framed.request[self.framed.sent..]){
                Ok(0)=>return TcpDnsPoll::Failed,
                Ok(n)=>self.framed.sent+=n,
                Err(e) if e.kind()==ErrorKind::WouldBlock=>{},
                Err(e) if e.kind()==ErrorKind::Interrupted=>{},
                Err(_)=>return TcpDnsPoll::Failed,
            }
            if self.framed.sent<self.framed.request.len(){
                return TcpDnsPoll::Pending
            }
        }
        let mut bytes=[0u8;MAX_DNS_WIRE+2];
        match stream.read(&mut bytes){
            Ok(0)=>TcpDnsPoll::Failed,
            Ok(n)=>match self.framed.take_answer(&bytes[..n]){
                Ok(Some(reply))=>TcpDnsPoll::Answer(reply),
                Ok(None)=>TcpDnsPoll::Pending,
                Err(())=>TcpDnsPoll::Failed,
            },
            Err(e) if e.kind()==ErrorKind::WouldBlock=>TcpDnsPoll::Pending,
            Err(e) if e.kind()==ErrorKind::Interrupted=>TcpDnsPoll::Pending,
            Err(_)=>TcpDnsPoll::Failed,
        }
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    #[test]
    fn plan029_tcp_dns_same_endpoint_frame_exact_wire_chunks_and_rejects_overlength(){
        let query=[0xabu8;12];
        let mut f=DnsTcpFrame::new(&query).unwrap();
        assert_eq!(&f.request[..2],&12u16.to_be_bytes());
        assert_eq!(&f.request[2..],&query);
        assert_eq!(f.take_answer(&[0]).unwrap(),None);
        assert_eq!(f.take_answer(&[12,0xab,0xab]).unwrap(),None);
        assert_eq!(f.take_answer(&[0xab;10]).unwrap(),Some(vec![0xab;12]));
        let mut malformed=DnsTcpFrame::new(&query).unwrap();
        assert_eq!(malformed.take_answer(&[0,0]),Err(()));
        let mut excess=DnsTcpFrame::new(&query).unwrap();
        assert_eq!(excess.take_answer(&[0,12].iter().copied().chain([0xab;14]).collect::<Vec<_>>()),Err(()));
        assert!(DnsTcpFrame::new(&[]).is_none());
        assert!(DnsTcpFrame::new(&vec![0;MAX_DNS_WIRE+1]).is_none());
    }
    #[test]
    fn plan029_dns_tcp_no_alt_endpoint_and_no_per_flow_worker(){
        // PhysicalTcpSocket::start(source,ifindex,ONLY endpoint:53);
        // invalid source/index returns before any Winsock connection.
        assert!(TcpDnsFallback::start(Ipv4Addr::LOCALHOST,14,
            Ipv4Addr::new(223,5,5,5),&[0;12]).is_err());
        assert!(TcpDnsFallback::start(Ipv4Addr::new(10,1,0,7),0,
            Ipv4Addr::new(223,5,5,5),&[0;12]).is_err());
    }
}
