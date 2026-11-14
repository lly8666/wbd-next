//! PLAN029 genuine original Windows app TCP/53: one already-owned kernel
//! Direct TCP listener supplies the stream. DNS QNAME is determined only
//! after bounded TCP length-prefix framing. The one original Rust TX owner
//! polls one client and one nonblocking single-endpoint upstream per quantum;
//! NO per-query thread, Go packet pump, extra Wintun reader, or fallback.
use std::io::{Read,Write,ErrorKind};
use std::net::{Ipv4Addr,TcpStream,Shutdown};
use std::time::{SystemTime,UNIX_EPOCH};
use crate::v4_client_split::DnsEgress;
use crate::v4_client_split_wire::dns_tcp_ingress::{
    TcpClientDnsAssembler,TcpClientDnsQuestion,
};
use crate::v4_client_dns_answer::{extract_a,DnsAResolution,DnsAnswerStatus};
use crate::v4_client_dns_wire::{synthesize_cn_a,synthesize_cn_nodata};
use crate::v4_client_fake_pool::{FakeAllocator,FakeKey};
use crate::v4_client_fake_journal::FakeJournal;
use crate::v4_windows_native_dns_tcp::{TcpDnsFallback,TcpDnsPoll};
use crate::v4_windows_native_dns_direct::plain_dns;

const CLIENT_TCP_DNS_LIMIT:usize=2048-42;
const CLIENT_TCP_DNS_DEADLINE_MS:u64=5_000;
#[derive(Clone,Copy)]
pub(crate) struct NativeTcpDnsEndpoints{
    pub physical:Ipv4Addr,
    pub physical_ifindex:u32,
    pub lease:Ipv4Addr,
    pub wintun_ifindex:u32,
    pub direct:Ipv4Addr,
    pub tunnel:Ipv4Addr,
}
impl NativeTcpDnsEndpoints{
    pub fn valid(self)->bool{
        self.physical_ifindex!=0&&self.wintun_ifindex!=0&&
        self.physical!=self.lease&&!self.lease.is_unspecified()&&
        !self.physical.is_unspecified()&&self.direct!=self.tunnel&&
        !self.direct.is_unspecified()&&!self.tunnel.is_unspecified()
    }
}
#[derive(Clone,Copy,Debug,Default,Eq,PartialEq)]
pub(crate) struct ClientDnsTcpTick{
    pub finished:bool,
    // Exact source port from an owned Wintun-bound tunnel DNS TCP socket,
    // installed by the TX owner before its subsequent Wintun drain quantum.
    pub new_tunnel_port:Option<u16>,
}
enum Phase{
    Reading(TcpClientDnsAssembler),
    Upstream{ticket:TcpClientDnsQuestion,lane:DnsEgress,
        tcp:TcpDnsFallback},
    Sending{bytes:Vec<u8>,sent:usize},
    Closed,
}
pub(crate) struct ClientDnsTcp{
    client:TcpStream,
    phase:Phase,
    deadline_ms:u64,
}
fn unix_ms()->Option<u64>{
    SystemTime::now().duration_since(UNIX_EPOCH).ok()
        .and_then(|x|u64::try_from(x.as_millis()).ok())
}
/// The same FakeIP cold writer used by original Direct UDP DNS. This
/// function never exposes a real CN CDN address or an unpersisted fake.
fn persist_and_synthesize(id:u16,name:&str,a:&DnsAResolution,
    pool:Option<&mut FakeAllocator>,journal:Option<&mut FakeJournal>)
    ->Option<Vec<u8>>{
    let (Some(pool),Some(journal),Some(now))=(pool,journal,unix_ms())else{
        return None
    };
    if a.status!=DnsAnswerStatus::Answered||a.candidates.is_empty(){
        return None
    }
    let mut required=Vec::with_capacity(a.candidates.len());
    for candidate in &a.candidates{
        let key=FakeKey{qname:name.into(),canonical:a.canonical.clone(),
            real4:candidate.address,policy_rev:1,resolver_rev:1};
        let p=pool.prepare(key,candidate.ttl,now).ok()?;
        if p.persist_before_reply&&!required.contains(&p.fake4){
            required.push(p.fake4);
        }
    }
    if !required.is_empty()&&journal.persist_batch(pool,&required).is_err(){
        return None
    }
    synthesize_cn_a(id,name,a,pool,1,1,now).ok().map(|p|p.packet)
}
fn checked_client_reply(q:&TcpClientDnsQuestion,lane:DnsEgress,
    raw:&[u8],pool:Option<&mut FakeAllocator>,
    journal:Option<&mut FakeJournal>)->Option<Vec<u8>>{
    let resolved=extract_a(raw,q.original_id,&q.qname,q.qtype).ok()?;
    if resolved.status==DnsAnswerStatus::Truncated{return None}
    if lane==DnsEgress::Tunnel || q.qtype!=1{
        // Verified original DNS question and ID; retain normal non-CN
        // answers verbatim (including any non-A records) on the chosen lane.
        return Some(raw.to_vec())
    }
    if resolved.status!=DnsAnswerStatus::Answered ||
       resolved.candidates.is_empty(){
        let rcode=match resolved.status{
            DnsAnswerStatus::NxDomain=>3,DnsAnswerStatus::NoData=>0,_=>2,
        };
        return plain_dns(q.original_id,&q.qname,q.qtype,rcode)
    }
    persist_and_synthesize(q.original_id,&q.qname,&resolved,pool,journal)
}
fn tcp_frame(wire:&[u8])->Option<Vec<u8>>{
    if !(12..=CLIENT_TCP_DNS_LIMIT).contains(&wire.len()){return None}
    let mut v=Vec::with_capacity(wire.len()+2);
    v.extend_from_slice(&(wire.len() as u16).to_be_bytes());
    v.extend_from_slice(wire);
    Some(v)
}
impl ClientDnsTcp{
    pub fn new(client:TcpStream,now_ms:u64)->Result<Self,()>{
        client.set_nonblocking(true).map_err(|_|())?;
        Ok(Self{client,phase:Phase::Reading(TcpClientDnsAssembler::new()),
            deadline_ms:now_ms.saturating_add(CLIENT_TCP_DNS_DEADLINE_MS)})
    }
    fn response(&mut self,wire:Vec<u8>)->Result<(),()>{
        self.phase=Phase::Sending{bytes:tcp_frame(&wire).ok_or(())?,sent:0};
        Ok(())
    }
    /// At most one nonblocking kernel read/write or one upstream poll in
    /// each owner round-robin quantum. A timeout fails just this stream;
    /// never block an existing Direct TCP relay or ordinary Tunnel DATA.
    pub fn step<F>(&mut self,now_ms:u64,ep:NativeTcpDnsEndpoints,
        route:&F,mut pool:Option<&mut FakeAllocator>,
        mut journal:Option<&mut FakeJournal>,tunnel_slot_free:bool)
        ->Result<ClientDnsTcpTick,()>
        where F:Fn(&str)->Option<DnsEgress>
    {
        if !ep.valid(){return Err(())}
        let mut result=ClientDnsTcpTick::default();
        if now_ms>=self.deadline_ms{
            let pending=std::mem::replace(&mut self.phase,Phase::Closed);
            match pending{
                Phase::Upstream{ticket,..}=>{
                    let wire=plain_dns(ticket.original_id,&ticket.qname,
                        ticket.qtype,2).ok_or(())?;
                    self.response(wire)?;
                },
                Phase::Sending{..}|Phase::Reading(..)|Phase::Closed=>{
                    return Err(())
                },
            }
        }
        let current=std::mem::replace(&mut self.phase,Phase::Closed);
        match current{
            Phase::Reading(mut parse)=>{
                let mut buf=[0u8;CLIENT_TCP_DNS_LIMIT+2];
                let finished=match self.client.read(&mut buf){
                    Ok(0)=>return Err(()),
                    Ok(n)=>parse.ingest(&buf[..n]).map_err(|_|())?,
                    Err(e) if matches!(e.kind(),ErrorKind::WouldBlock|ErrorKind::Interrupted)=>{
                        self.phase=Phase::Reading(parse);return Ok(result)
                    },
                    Err(_)=>return Err(()),
                };
                let Some(q)=finished else{
                    self.phase=Phase::Reading(parse);return Ok(result)
                };
                let Some(lane)=route(&q.qname)else{return Err(())};
                if lane==DnsEgress::Direct&&matches!(q.qtype,28|64|65){
                    self.response(synthesize_cn_nodata(q.original_id,
                        &q.qname,q.qtype,false).map_err(|_|())?)?;
                    return Ok(result)
                }
                if lane==DnsEgress::Tunnel&&!tunnel_slot_free{
                    self.response(plain_dns(q.original_id,&q.qname,
                        q.qtype,2).ok_or(())?)?;
                    return Ok(result)
                }
                let (source,ifindex,target)=if lane==DnsEgress::Tunnel{
                    (ep.lease,ep.wintun_ifindex,ep.tunnel)
                }else{(ep.physical,ep.physical_ifindex,ep.direct)};
                match TcpDnsFallback::start(source,ifindex,target,&q.wire){
                    Ok(tcp)=>{
                        if lane==DnsEgress::Tunnel{
                            let p=tcp.source_port().ok_or(())?;
                            result.new_tunnel_port=Some(p);
                        }
                        self.phase=Phase::Upstream{ticket:q,lane,tcp};
                    },
                    Err(())=>{
                        self.response(plain_dns(q.original_id,&q.qname,
                            q.qtype,2).ok_or(())?)?;
                    },
                };
            },
            Phase::Upstream{ticket,lane,mut tcp}=>{
                match tcp.poll(){
                    TcpDnsPoll::Pending=>{
                        self.phase=Phase::Upstream{ticket,lane,tcp}
                    },
                    TcpDnsPoll::Failed=>{
                        self.response(plain_dns(ticket.original_id,&ticket.qname,
                            ticket.qtype,2).ok_or(())?)?;
                    },
                    TcpDnsPoll::Answer(reply)=>{
                        let wire=checked_client_reply(&ticket,lane,&reply,
                            pool.as_deref_mut(),journal.as_deref_mut())
                            .or_else(||plain_dns(ticket.original_id,
                                &ticket.qname,ticket.qtype,2))
                            .ok_or(())?;
                        self.response(wire)?;
                    },
                }
            },
            Phase::Sending{bytes,mut sent}=>{
                match self.client.write(&bytes[sent..]){
                    Ok(0)=>return Err(()),
                    Ok(n)=>sent+=n,
                    Err(e) if matches!(e.kind(),ErrorKind::WouldBlock|ErrorKind::Interrupted)=>{},
                    Err(_)=>return Err(()),
                }
                if sent==bytes.len(){
                    let _=self.client.shutdown(Shutdown::Write);
                    self.phase=Phase::Closed;
                    result.finished=true;
                }else{
                    self.phase=Phase::Sending{bytes,sent};
                }
            },
            Phase::Closed=>result.finished=true,
        }
        Ok(result)
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    use crate::v4_client_dns_answer::ResolvedA;
    #[test]
    fn plan029_app_dns_tcp_framing_cap_and_two_pinned_upstream_sources(){
        assert!(tcp_frame(&[0u8;12]).is_some());
        assert!(tcp_frame(&vec![0u8;CLIENT_TCP_DNS_LIMIT+1]).is_none());
        assert!(!NativeTcpDnsEndpoints{physical:Ipv4Addr::new(10,1,2,3),
            physical_ifindex:14,lease:Ipv4Addr::new(10,66,0,2),
            wintun_ifindex:0,direct:Ipv4Addr::new(223,5,5,5),
            tunnel:Ipv4Addr::new(1,1,1,1)}.valid());
    }
    #[test]
    fn plan029_app_cn_tcp53_only_durable_fake_never_shared_cdn_real(){
        let resolved=DnsAResolution{status:DnsAnswerStatus::Answered,
            canonical:"cn.example".into(),cname_chain:vec![],
            candidates:vec![ResolvedA{address:0xc633644d,ttl:30}]};
        assert!(persist_and_synthesize(10,"cn.example",&resolved,None,None).is_none());
        let mut pool=FakeAllocator::new(0xc6120001,0xc612007f,&[],8,1024*1024).unwrap();
        let path=std::env::temp_dir().join(format!("wbd-dns-client-tcp-{}.db",
            std::process::id()));
        let (mut journal,_) =FakeJournal::open(&path).unwrap();
        let made=persist_and_synthesize(10,"cn.example",&resolved,
            Some(&mut pool),Some(&mut journal)).unwrap();
        assert!(!made.windows(4).any(|x|x==0xc633644du32.to_be_bytes()));
        assert!(made.windows(4).any(|x|x==0xc6120001u32.to_be_bytes()));
        assert_eq!(pool.announced_real(0xc6120001),Some(0xc633644d));
        drop(journal);
        std::fs::remove_file(path).unwrap();
    }
}
