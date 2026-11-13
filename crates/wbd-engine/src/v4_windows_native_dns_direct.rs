//! PLAN029 private same-owner Direct DNS worker. One cold physical endpoint,
//! no fallback; no Wintun ring retained during DNS or filesystem I/O.
//! Completion flows through original native RX's bounded Wintun mailbox.
//! V3 is a private probe; NOT public product DNS/Stop qualification.
use std::collections::VecDeque;
use std::io::ErrorKind;
use std::net::{Ipv4Addr,SocketAddrV4};
use std::time::{SystemTime,UNIX_EPOCH};
use wbd_platform::windows_direct_udp::{
    PhysicalUdpSocket,parse_owned_ipv4_udp,encode_reverse_ipv4_udp,DirectUdpTuple,
};
use crate::v4_client_dns_pending::{
    DnsPending,DnsClient,QueryKey,ResolverLane,ValidatedReply,DnsPendingError,
};
use crate::v4_client_dns_answer::DnsAnswerStatus;
use crate::v4_client_dns_wire::{synthesize_cn_a,synthesize_cn_nodata};
use crate::v4_client_fake_pool::{FakeAllocator,FakeKey};
use crate::v4_client_fake_journal::FakeJournal;
use crate::v4_windows_native_dns_tcp::{TcpDnsFallback,TcpDnsPoll};

const MAX_PENDING:usize=256;
const MAX_READY:usize=256;
const MAX_POLL:usize=16;
const TIMEOUT_MS:u64=5_000;
const MAX_L3:usize=2048;
#[repr(C)]
struct PollFd{socket:usize,events:i16,revents:i16}
#[link(name="ws2_32")]
extern "system" { fn WSAPoll(fds:*mut PollFd,count:u32,timeout:i32)->i32; }
const POLLRDNORM:i16=0x0100;
struct Inflight{
    id:u16,key:QueryKey,socket:PhysicalUdpSocket,
    query:Vec<u8>,sent:bool,deadline:u64,
    tcp:Option<TcpDnsFallback>,
}
pub(crate) struct DirectDns{
    source:Ipv4Addr,ifindex:u32,lease:Ipv4Addr,endpoint:Ipv4Addr,
    mtu:usize,pending:DnsPending,inflight:Vec<Inflight>,
    completed:VecDeque<Vec<u8>>,cursor:usize,ip_id:u16,
}
fn wall_ms()->Option<u64>{
    SystemTime::now().duration_since(UNIX_EPOCH).ok()
        .and_then(|x|u64::try_from(x.as_millis()).ok())
}
/// An error/NODATA response containing no authority/additional real IP.
fn plain_dns(id:u16,name:&str,qtype:u16,rcode:u16)->Option<Vec<u8>>{
    let mut b=vec![0u8;12];
    b[..2].copy_from_slice(&id.to_be_bytes());
    b[2..4].copy_from_slice(&(0x8180u16|(rcode&15)).to_be_bytes());
    b[4..6].copy_from_slice(&1u16.to_be_bytes());
    for part in name.split('.'){
        if part.is_empty()||part.len()>63||!part.is_ascii()||
           b.len()+part.len()+6>512{return None}
        b.push(part.len() as u8);b.extend_from_slice(part.as_bytes());
    }
    b.push(0);b.extend_from_slice(&qtype.to_be_bytes());
    b.extend_from_slice(&1u16.to_be_bytes());
    Some(b)
}
impl DirectDns{
    pub(crate) fn new(source:Ipv4Addr,ifindex:u32,lease:Ipv4Addr,
        endpoint:Ipv4Addr,mtu:usize)->Self{
        Self{source,ifindex,lease,endpoint,mtu,
            pending:DnsPending::new(MAX_PENDING,1024),inflight:Vec::new(),
            completed:VecDeque::with_capacity(MAX_READY),cursor:0,ip_id:1}
    }
    pub(crate) fn has_work(&self)->bool{
        !self.inflight.is_empty()||!self.completed.is_empty()
    }
    pub(crate) fn counts(&self)->(usize,usize,usize){
        (self.inflight.len(),self.pending.counts().1,self.completed.len())
    }
    fn enqueue(&mut self,client:DnsClient,reply:&[u8]){
        if self.completed.len()>=MAX_READY{return}
        let tuple=DirectUdpTuple{client_ip:Ipv4Addr::from(client.src4),
            client_port:client.src_port,
            presented_ip:Ipv4Addr::from(client.requested_dns4),target_port:53};
        let mut l3=[0u8;MAX_L3];
        self.ip_id=self.ip_id.wrapping_add(1);
        if let Ok(n)=encode_reverse_ipv4_udp(tuple,reply,self.ip_id,self.mtu,&mut l3){
            self.completed.push_back(l3[..n].to_vec());
        }
    }
    fn fail(&mut self,clients:&[DnsClient],key:&QueryKey,rcode:u16){
        for &client in clients{
            if let Some(wire)=plain_dns(client.original_id,&key.name,key.qtype,rcode){
                self.enqueue(client,&wire)
            }
        }
    }
    /// Called only by the original TX after packet bytes have been copied
    /// and released from Wintun. Never directly touches the native ring.
    pub(crate) fn submit(&mut self,packet:&[u8],name:String,qtype:u16,
        id:u16,now_ms:u64,has_fake_writer:bool)->bool{
        if packet.len()<28{return false}
        let requested=Ipv4Addr::new(packet[16],packet[17],packet[18],packet[19]);
        let udp=match parse_owned_ipv4_udp(packet,self.lease,requested){
            Ok(p)=>p,Err(_)=>return false
        };
        if udp.data.len()<12||
           u16::from_be_bytes([udp.data[0],udp.data[1]])!=id{
            return false
        }
        let client=DnsClient{src4:u32::from(self.lease),
            src_port:udp.tuple.client_port,requested_dns4:u32::from(requested),
            original_id:id};
        let key=QueryKey{name,qtype,lane:ResolverLane::Direct,
            resolver4:u32::from(self.endpoint),resolver_port:53,
            policy_revision:1};
        if matches!(qtype,28|64|65){
            if let Ok(wire)=synthesize_cn_nodata(id,&key.name,qtype,false){
                self.enqueue(client,&wire)
            }
            return true
        }
        // CN A without durable file is SERVFAIL, NEVER unmodified CDN A.
        if qtype==1&&!has_fake_writer{
            self.fail(&[client],&key,2);return true
        }
        let ticket=match self.pending.begin(key.clone(),client,now_ms,TIMEOUT_MS){
            Ok(t)=>t,Err(_)=>{self.fail(&[client],&key,2);return true}
        };
        if !ticket.new_upstream_query{return true}
        let socket=match PhysicalUdpSocket::open(self.source,self.ifindex,
            SocketAddrV4::new(self.endpoint,53)){
            Ok(s)=>s,Err(_)=>{
                if let Some((key,clients))=self.pending.abort_one(ticket.upstream_id){
                    self.fail(&clients,&key,2)
                }
                return true
            }
        };
        let mut query=udp.data.to_vec();
        query[..2].copy_from_slice(&ticket.upstream_id.to_be_bytes());
        let mut inflight=Inflight{id:ticket.upstream_id,key,socket,query,
            sent:false,deadline:now_ms.saturating_add(TIMEOUT_MS),
            tcp:None};
        match inflight.socket.send_ready(&inflight.query){
            Ok(n) if n==inflight.query.len()=>inflight.sent=true,
            Err(e) if e.kind()==ErrorKind::WouldBlock=>{},
            _=>{
                if let Some((key,clients))=self.pending.abort_one(ticket.upstream_id){
                    self.fail(&clients,&key,2)
                }
                return true
            }
        }
        self.inflight.push(inflight);
        true
    }
    fn resolved(&mut self,reply:ValidatedReply,raw:&[u8],
        fake:Option<&mut FakeAllocator>,journal:Option<&mut FakeJournal>){
        let key=&reply.key;
        if key.qtype!=1{
            // Same verified physical endpoint and DNS question, original
            // transaction ID restored independently for every coalesced client.
            for client in reply.waiters{
                if raw.len()<12{continue}
                let mut bytes=raw.to_vec();
                bytes[..2].copy_from_slice(&client.original_id.to_be_bytes());
                self.enqueue(client,&bytes);
            }
            return
        }
        if reply.answer.status!=DnsAnswerStatus::Answered ||
           reply.answer.candidates.is_empty(){
            let rcode=match reply.answer.status{
                DnsAnswerStatus::NxDomain=>3,DnsAnswerStatus::NoData=>0,_=>2,
            };
            self.fail(&reply.waiters,key,rcode);return
        }
        let (Some(fake),Some(journal),Some(wall))=(fake,journal,wall_ms())else{
            self.fail(&reply.waiters,key,2);return
        };
        let mut batch=Vec::new();
        let mut bad=false;
        for candidate in &reply.answer.candidates{
            let identity=FakeKey{qname:key.name.clone(),
                canonical:reply.answer.canonical.clone(),real4:candidate.address,
                policy_rev:key.policy_revision,resolver_rev:1};
            match fake.prepare(identity,candidate.ttl,wall){
                Ok(p) if p.persist_before_reply=>{
                    if !batch.contains(&p.fake4){batch.push(p.fake4)}
                },
                Ok(_)=>{},Err(_)=>{bad=true;break}
            }
        }
        if !bad&&!batch.is_empty()&&
           journal.persist_batch(fake,&batch).is_err(){bad=true}
        if bad{self.fail(&reply.waiters,key,2);return}
        for client in reply.waiters{
            match synthesize_cn_a(client.original_id,&key.name,&reply.answer,
                fake,key.policy_revision,1,wall){
                Ok(wire)=>self.enqueue(client,&wire.packet),
                Err(_)=>self.fail(&[client],key,2),
            }
        }
    }
    /// The native TX worker calls this on its already-bounded ready-only
    /// 10ms Direct quantum, not in the ordinary Tunnel DATA seal loop.
    pub(crate) fn poll(&mut self,now_ms:u64,
        mut fake:Option<&mut FakeAllocator>,
        mut journal:Option<&mut FakeJournal>){
        let mut i=0;
        while i<self.inflight.len(){
            if now_ms<self.inflight[i].deadline{i+=1;continue}
            let id=self.inflight.swap_remove(i).id;
            if let Some((key,clients))=self.pending.abort_one(id){
                self.fail(&clients,&key,2)
            }
        }
        let count=self.inflight.len();
        if count==0{self.cursor=0;return}
        let quantum=count.min(MAX_POLL);
        let mut fds=Vec::with_capacity(quantum);
        for n in 0..quantum{
            let idx=(self.cursor+n)%count;
            fds.push(PollFd{socket:self.inflight[idx].socket.poll_socket(),
                events:POLLRDNORM,revents:0});
        }
        let rc=unsafe{WSAPoll(fds.as_mut_ptr(),quantum as u32,0)};
        if rc<0{return}
        // Complete/failed exact tickets are collected by their original
        // Vec index. Retire in reverse index order so swap_remove cannot
        // detach a different DNS request or leak its original transaction.
        let mut finished:Vec<(usize,Result<(ValidatedReply,Vec<u8>),()>)>=Vec::new();
        let mut bytes=[0u8;MAX_L3];
        for step in 0..quantum{
            let idx=(self.cursor+step)%count;
            let q=&mut self.inflight[idx];
            if let Some(tcp)=q.tcp.as_mut(){
                match tcp.poll(){
                    TcpDnsPoll::Pending=>{},
                    TcpDnsPoll::Failed=>finished.push((idx,Err(()))),
                    TcpDnsPoll::Answer(wire)=>{
                        let validated=self.pending.accept(q.id,
                            u32::from(self.endpoint),53,ResolverLane::Direct,
                            &wire,now_ms);
                        match validated{
                            Ok(answer)=>finished.push((idx,Ok((answer,wire)))),
                            Err(_)=>finished.push((idx,Err(()))),
                        }
                    },
                }
                continue
            }
            if !q.sent{
                if let Ok(n)=q.socket.send_ready(&q.query){
                    q.sent=n==q.query.len();
                }
                continue
            }
            if rc==0||fds[step].revents&POLLRDNORM==0{continue}
            let Ok(n)=q.socket.receive_ready(&mut bytes)else{continue};
            if n<12{continue}
            let id=u16::from_be_bytes([bytes[0],bytes[1]]);
            if id!=q.id{continue}
            match self.pending.accept(id,u32::from(self.endpoint),53,
                ResolverLane::Direct,&bytes[..n],now_ms){
                Ok(answer)=>finished.push((idx,Ok((answer,bytes[..n].to_vec())))),
                Err(DnsPendingError::TruncatedSameEndpointTcp)=>{
                    // Exactly the same resolver IPv4/53, source IPv4/ifindex
                    // and pending ticket; no new DNS transaction, system
                    // DNS or opposite-direction fallback. Nonblocking
                    // connect/read/write lives in this one Rust scheduler.
                    match TcpDnsFallback::start(self.source,self.ifindex,
                        self.endpoint,&q.query){
                        Ok(tcp)=>q.tcp=Some(tcp),
                        Err(())=>finished.push((idx,Err(()))),
                    }
                },
                Err(_)=>{},
            }
        }
        self.cursor=(self.cursor+quantum)%count;
        finished.sort_by_key(|(idx,_)|std::cmp::Reverse(*idx));
        for (idx,result) in finished{
            let query=self.inflight.swap_remove(idx);
            match result{
                Ok((answer,wire))=>{
                    self.resolved(answer,&wire,
                        fake.as_deref_mut(),journal.as_deref_mut())
                },
                Err(())=>{
                    if let Some((key,clients))=self.pending.abort_one(query.id){
                        self.fail(&clients,&key,2)
                    }
                },
            }
        }
        if self.inflight.is_empty(){self.cursor=0}
        else{self.cursor%=self.inflight.len()}
    }
    pub(crate) fn pop(&mut self)->Option<Vec<u8>>{self.completed.pop_front()}
}
#[cfg(test)]
mod tests{
    use super::*;
    #[test]
    fn plan029_direct_dns_one_socket_endpoint_bounded_no_journal_leak(){
        let mut dns=DirectDns::new(Ipv4Addr::new(10,1,0,7),14,
            Ipv4Addr::new(10,234,12,34),Ipv4Addr::new(223,5,5,5),1280);
        assert_eq!(dns.counts(),(0,0,0));
        let mut q=vec![0u8;44];
        q[0]=0x45;q[2..4].copy_from_slice(&44u16.to_be_bytes());
        q[9]=17;q[12..16].copy_from_slice(&[10,234,12,34]);
        q[16..20].copy_from_slice(&[8,8,8,8]);
        q[20..22].copy_from_slice(&45678u16.to_be_bytes());
        q[22..24].copy_from_slice(&53u16.to_be_bytes());
        q[24..26].copy_from_slice(&24u16.to_be_bytes());
        q[28..30].copy_from_slice(&0x1234u16.to_be_bytes());
        q[30..32].copy_from_slice(&0x0100u16.to_be_bytes());
        q[32..34].copy_from_slice(&1u16.to_be_bytes());
        assert!(dns.submit(&q,"cn.example".into(),1,0x1234,1,false));
        assert_eq!(dns.counts(),(0,0,1));
        let answer=dns.pop().unwrap();
        assert_eq!(&answer[12..16],&[8,8,8,8]);
        assert_eq!(&answer[16..20],&[10,234,12,34]);
        assert_eq!(&answer[28..30],&0x1234u16.to_be_bytes());
        assert_eq!(answer[31]&15,2); // fail closed, never real CN A
        assert_eq!(dns.counts(),(0,0,0));
    }
}
