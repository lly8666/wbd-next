//! B63: original Android physical DNS UDP-TC -> same bound kernel TCP.
//! Standard DNS length framing follows the existing PLAN029 native TCP
//! design. Only the original TX worker owns these transient DNS sockets.
use std::io::{Read,Write,ErrorKind};
use crate::v4_android_dns_physical_flow::MAX_DNS_WIRE;

struct DnsTcpFrame{request:Vec<u8>,sent:usize,received:Vec<u8>}
enum TcpStep{Pending,Answer(Vec<u8>),Failed}
impl DnsTcpFrame{
    fn new(query:&[u8])->Option<Self>{
        if !(17..=MAX_DNS_WIRE).contains(&query.len()){return None}
        let mut request=Vec::with_capacity(query.len()+2);
        request.extend_from_slice(&(query.len() as u16).to_be_bytes());
        request.extend_from_slice(query);
        Some(Self{request,sent:0,received:Vec::new()})
    }
    fn wants_write(&self)->bool{self.sent<self.request.len()}
    // One bounded nonblocking send/read turn; kernel TCP owns segments.
    fn step(&mut self,stream:&mut impl ReadWrite)->TcpStep{
        if self.wants_write(){
            match stream.write(&self.request[self.sent..]){
                Ok(0)=>return TcpStep::Failed,
                Ok(n)=>self.sent+=n,
                Err(e) if matches!(e.kind(),ErrorKind::WouldBlock|ErrorKind::Interrupted)=>
                    return TcpStep::Pending,
                Err(_)=>return TcpStep::Failed,
            }
            if self.wants_write(){return TcpStep::Pending}
        }
        let remaining=if self.received.len()<2{2-self.received.len()}else{
            let n=u16::from_be_bytes([self.received[0],self.received[1]]) as usize;
            if !(17..=MAX_DNS_WIRE).contains(&n){return TcpStep::Failed}
            n+2-self.received.len()
        };
        let mut scratch=[0u8;MAX_DNS_WIRE+2];
        match stream.read(&mut scratch[..remaining]){
            Ok(0)=>TcpStep::Failed,
            Ok(n)=>{
                self.received.extend_from_slice(&scratch[..n]);
                if self.received.len()<2{return TcpStep::Pending}
                let n=u16::from_be_bytes([self.received[0],self.received[1]]) as usize;
                if !(17..=MAX_DNS_WIRE).contains(&n){return TcpStep::Failed}
                if self.received.len()==n+2{TcpStep::Answer(self.received[2..].to_vec())}
                else{TcpStep::Pending}
            },
            Err(e) if matches!(e.kind(),ErrorKind::WouldBlock|ErrorKind::Interrupted)=>TcpStep::Pending,
            Err(_)=>TcpStep::Failed,
        }
    }
}
trait ReadWrite:Read+Write{}
impl<T:Read+Write> ReadWrite for T{}

#[cfg(target_os="android")]
mod android{
    use super::*;
    use std::{net::TcpStream,os::fd::AsRawFd};
    use crate::v4_android_dns_physical_flow::{PhysicalDnsUdpFlows,TcpFallbackTicket};
    use wbd_platform::android_root_io::{
        AndroidBoundPhysicalDnsUdp,AndroidDnsTcpInterest,MAX_DNS_TCP_FALLBACKS};
    const TIMEOUT_MS:u64=2_000;
    struct Pending{
        ticket:TcpFallbackTicket,tc:Vec<u8>,stream:TcpStream,
        frame:DnsTcpFrame,deadline:u64,connecting:bool,
    }
    pub(crate) struct Completed{
        pub ticket:TcpFallbackTicket,pub truncated:Vec<u8>,pub full:Option<Vec<u8>>,
    }
    #[derive(Default)]
    pub(crate) struct PhysicalDnsTcpFallbacks{pending:Vec<Pending>}
    impl PhysicalDnsTcpFallbacks{
        pub(crate) fn try_start(&mut self,socket:&AndroidBoundPhysicalDnsUdp,
            flows:&PhysicalDnsUdpFlows,wire:&[u8],now:u64)->bool{
            let Some((ticket,query))=flows.fallback_question(wire,now)else{return false};
            if self.pending.iter().any(|p|p.ticket==ticket){return true}
            if self.pending.len()>=MAX_DNS_TCP_FALLBACKS{return false}
            let Some(frame)=DnsTcpFrame::new(query)else{return false};
            let Ok(stream)=socket.open_tcp()else{return false};
            self.pending.push(Pending{ticket,tc:wire.to_vec(),stream,frame,
                deadline:now.saturating_add(TIMEOUT_MS),connecting:true});
            true
        }
        pub(crate) fn interests(&self)->([AndroidDnsTcpInterest;MAX_DNS_TCP_FALLBACKS],usize){
            let mut fds=[AndroidDnsTcpInterest::default();MAX_DNS_TCP_FALLBACKS];
            for (i,p) in self.pending.iter().enumerate(){
                fds[i]=AndroidDnsTcpInterest{fd:p.stream.as_raw_fd(),
                    writable:p.connecting||p.frame.wants_write(),ready:false};
            }
            (fds,self.pending.len())
        }
        pub(crate) fn limit_timeout(&self,timeout:i32,now:u64)->i32{
            self.pending.iter().map(|p|p.deadline.saturating_sub(now) as i32)
                .min().map_or(timeout,|due|timeout.min(due))
        }
        pub(crate) fn ready(&mut self,interests:&[AndroidDnsTcpInterest],now:u64)->Vec<Completed>{
            let mut finished=Vec::new();
            // Process backwards so swap_remove never mismatches poll slots.
            for i in (0..self.pending.len()).rev(){
                let p=&mut self.pending[i];
                let result=if now>=p.deadline{TcpStep::Failed}
                else if !interests.get(i).is_some_and(|interest|interest.ready){continue}
                else{
                    if p.connecting{
                        match p.stream.take_error(){
                            Ok(None)=>p.connecting=false,
                            _=>{
                                let p=self.pending.swap_remove(i);
                                finished.push(Completed{ticket:p.ticket,truncated:p.tc,full:None});
                                continue
                            }
                        }
                    }
                    p.frame.step(&mut p.stream)
                };
                let full=match result{
                    TcpStep::Pending=>continue,
                    TcpStep::Answer(answer)=>Some(answer),
                    TcpStep::Failed=>None,
                };
                let p=self.pending.swap_remove(i);
                finished.push(Completed{ticket:p.ticket,truncated:p.tc,full});
            }
            finished
        }
        pub(crate) fn stop(&mut self){self.pending.clear();}
    }
}
#[cfg(target_os="android")]
pub(crate) use android::PhysicalDnsTcpFallbacks;

#[cfg(test)]
mod tests{
    use super::*;
    #[test]
    fn b63_physical_dns_tcp_real_loopback_framing(){
        use std::{net::{TcpListener,TcpStream},thread,time::{Instant,Duration}};
        let listener=TcpListener::bind(("127.0.0.1",0)).unwrap();
        let mut query=vec![0u8;12];query[0]=0x71;query[2]=1;query[5]=1;
        query.extend_from_slice(&[3,b'w',b'b',b'd',7,b'e',b'x',b'a',b'm',b'p',b'l',b'e',0,0,1,0,1]);
        let expected=query.clone();
        let address=listener.local_addr().unwrap();
        let server=thread::spawn(move||{
            let (mut peer,_)=listener.accept().unwrap();
            peer.set_read_timeout(Some(Duration::from_secs(2))).unwrap();
            let mut len=[0;2];peer.read_exact(&mut len).unwrap();
            let mut received=vec![0;u16::from_be_bytes(len) as usize];
            peer.read_exact(&mut received).unwrap();
            assert_eq!(received,expected);
            received[2]=0x81;received[3]=0x80;received[7]=1;
            received.extend_from_slice(&[0xc0,12,0,1,0,1,0,0,0,60,0,4,1,2,3,4]);
            let len=(received.len() as u16).to_be_bytes();
            peer.write_all(&len[..1]).unwrap();peer.write_all(&len[1..]).unwrap();
            peer.write_all(&received).unwrap();
            received
        });
        let mut client=TcpStream::connect(address).unwrap();
        client.set_nonblocking(true).unwrap();
        let mut frame=DnsTcpFrame::new(&query).unwrap();
        let end=Instant::now()+Duration::from_secs(2);
        let response=loop{
            assert!(Instant::now()<end,"loopback deadline");
            match frame.step(&mut client){
                TcpStep::Answer(answer)=>break answer,
                TcpStep::Pending=>thread::sleep(Duration::from_millis(1)),
                TcpStep::Failed=>panic!("real TCP framing failed"),
            }
        };
        assert_eq!(response,server.join().unwrap());
    }
}
