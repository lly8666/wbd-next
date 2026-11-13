//! PLAN029 bounded DNS query-level coalescing owned by the ONE native
//! Rust ingress scheduler. No per-query thread, no fallback DNS, no socket,
//! no per-DATA work and no Wintun receive/send loan held during a query.
//! Physical/Tunnel I/O workers are responsible for actually transmitting
//! and accepting replies from their independently selected endpoint.
use std::collections::HashMap;
use crate::v4_client_split::DnsEgress;
use crate::v4_client_dns_answer::{extract_a,DnsAResolution,DnsAnswerStatus,DnsReplyError};

#[derive(Clone,Copy,Debug,Eq,PartialEq,Hash)]
pub(crate) enum ResolverLane{Direct,Tunnel}
impl From<DnsEgress> for ResolverLane{
    fn from(v:DnsEgress)->Self{match v{
        DnsEgress::Direct=>Self::Direct,DnsEgress::Tunnel=>Self::Tunnel,
    }}
}
#[derive(Clone,Debug,Eq,PartialEq,Hash)]
pub(crate) struct QueryKey{
    pub name:String,pub qtype:u16,
    pub lane:ResolverLane,
    pub resolver4:u32,pub resolver_port:u16,
    pub policy_revision:u64,
}
impl QueryKey{
    pub fn validate(&self)->bool{
        !self.name.is_empty()&&self.name.len()<=253&&
            self.name.bytes().all(|b|b.is_ascii_graphic())&&
            self.resolver4!=0&&self.resolver_port!=0&&self.qtype!=0
    }
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) struct DnsClient{
    pub src4:u32,pub src_port:u16,pub requested_dns4:u32,
    pub original_id:u16,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) enum DnsPendingError{
    InvalidQuery,TransactionFull,WaitersFull,UnknownTransaction,
    SourceMismatch,MalformedAnswer,TruncatedSameEndpointTcp,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) struct QueryTicket{
    pub upstream_id:u16,
    pub new_upstream_query:bool,
}
#[derive(Debug)]
struct PendingQuery{
    key:QueryKey,
    deadline_ms:u64,
    waiters:Vec<DnsClient>,
}
#[derive(Clone,Debug,Eq,PartialEq)]
pub(crate) struct ValidatedReply{
    pub key:QueryKey,
    pub waiters:Vec<DnsClient>,
    pub answer:DnsAResolution,
}
pub(crate) struct DnsPending{
    keys:HashMap<QueryKey,u16>,
    entries:HashMap<u16,PendingQuery>,
    max_concurrent:usize,
    max_waiters:usize,
    active_waiters:usize,
    next_id:u16,
}
impl DnsPending{
    pub fn new(max_concurrent:usize,max_waiters:usize)->Self{
        Self{keys:HashMap::new(),entries:HashMap::new(),
            max_concurrent,max_waiters,active_waiters:0,next_id:1}
    }
    pub fn counts(&self)->(usize,usize){(self.entries.len(),self.active_waiters)}
    pub fn begin(&mut self,key:QueryKey,client:DnsClient,now_ms:u64,
        timeout_ms:u64)->Result<QueryTicket,DnsPendingError>{
        if !key.validate()||timeout_ms==0||timeout_ms>5_000{
            return Err(DnsPendingError::InvalidQuery)
        }
        if self.active_waiters>=self.max_waiters{
            return Err(DnsPendingError::WaitersFull)
        }
        if let Some(&id)=self.keys.get(&key){
            let existing=self.entries.get_mut(&id).ok_or(DnsPendingError::UnknownTransaction)?;
            if existing.deadline_ms>now_ms{
                existing.waiters.push(client);
                self.active_waiters+=1;
                return Ok(QueryTicket{upstream_id:id,new_upstream_query:false})
            }
            // An expired transaction is no longer a possible coalescing
            // target. Existing clients must be failed before reusing IDs;
            // the caller's coarse deadline tick owns this cleanup.
            return Err(DnsPendingError::TransactionFull)
        }
        if self.entries.len()>=self.max_concurrent{
            return Err(DnsPendingError::TransactionFull)
        }
        let mut available=None;
        for _ in 0..u16::MAX{
            let id=self.next_id;
            self.next_id=if self.next_id==u16::MAX{1}else{self.next_id+1};
            if !self.entries.contains_key(&id){available=Some(id);break}
        }
        let id=available.ok_or(DnsPendingError::TransactionFull)?;
        self.keys.insert(key.clone(),id);
        self.entries.insert(id,PendingQuery{key,waiters:vec![client],
            deadline_ms:now_ms.saturating_add(timeout_ms)});
        self.active_waiters+=1;
        Ok(QueryTicket{upstream_id:id,new_upstream_query:true})
    }
    /// Strict source4+UDP port+direction match before any answered byte is
    /// delivered. Transport owner must first validate its socket generation.
    /// Bad packets cannot steal a pending ticket or poison reply cache.
    pub fn accept(&mut self,id:u16,from4:u32,from_port:u16,
        via:ResolverLane,wire:&[u8],now_ms:u64)
        ->Result<ValidatedReply,DnsPendingError>{
        let pending=self.entries.get(&id)
            .ok_or(DnsPendingError::UnknownTransaction)?;
        if pending.deadline_ms<=now_ms{
            return Err(DnsPendingError::UnknownTransaction)
        }
        let k=&pending.key;
        if k.resolver4!=from4||k.resolver_port!=from_port||k.lane!=via{
            return Err(DnsPendingError::SourceMismatch)
        }
        let answer=extract_a(wire,id,&k.name,k.qtype)
            .map_err(|_:DnsReplyError|DnsPendingError::MalformedAnswer)?;
        if answer.status==DnsAnswerStatus::Truncated{
            // Keep the exact in-flight key, ID, waiters and expiry. Caller
            // tries DNS-over-TCP at this SAME endpoint/lane; no new query,
            // alternate NIC resolver or reverse-direction fallthrough.
            return Err(DnsPendingError::TruncatedSameEndpointTcp)
        }
        let Some(pending)=self.entries.remove(&id)else{
            return Err(DnsPendingError::UnknownTransaction)
        };
        self.keys.remove(&pending.key);
        self.active_waiters-=pending.waiters.len();
        Ok(ValidatedReply{key:pending.key,waiters:pending.waiters,answer})
    }
    /// One coarse timer/tick owned by the native scheduler, not per-Wintun
    /// packet. With max_concurrent=256, an at-most-256-entry bounded scan
    /// per coarse tick is cheaper than a per-query OS timer or thread.
    /// Returned waiters must receive deadline-scoped SERVFAIL on their
    /// ORIGINAL tuple/ID; no cross-lane or system-resolver retry.
    /// Abort only this exact physical query, returning every coalesced client.
    pub fn abort_one(&mut self,id:u16)->Option<(QueryKey,Vec<DnsClient>)>{
        let query=self.entries.remove(&id)?;
        self.keys.remove(&query.key);
        self.active_waiters-=query.waiters.len();
        Some((query.key,query.waiters))
    }
    pub fn expire(&mut self,now_ms:u64)->Vec<DnsClient>{
        let gone=self.entries.iter().filter(|(_,q)|q.deadline_ms<=now_ms)
            .map(|(&id,_)|id).collect::<Vec<_>>();
        let mut clients=Vec::new();
        for id in gone {
            if let Some(q)=self.entries.remove(&id){
                self.keys.remove(&q.key);
                self.active_waiters-=q.waiters.len();
                clients.extend(q.waiters);
            }
        }
        clients
    }
    /// Abort old generation before Stop closes Direct/ESP socket. Returned
    /// clients fail explicitly; late replies cannot resurrect an old map.
    pub fn cancel_all(&mut self)->Vec<DnsClient>{
        let mut clients=Vec::with_capacity(self.active_waiters);
        for (_,q) in self.entries.drain(){clients.extend(q.waiters)}
        self.keys.clear();
        self.active_waiters=0;
        clients
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    fn key(lane:ResolverLane,name:&str)->QueryKey{
        QueryKey{name:name.into(),qtype:1,lane,
            resolver4:u32::from_be_bytes([1,1,1,1]),
            resolver_port:53,policy_revision:1}
    }
    fn client(port:u16,id:u16)->DnsClient{
        DnsClient{src4:0x0a020304,src_port:port,
            requested_dns4:u32::from_be_bytes([8,8,8,8]),original_id:id}
    }
    fn response(id:u16,name:&str)->Vec<u8>{
        let mut d=vec![0u8;12];
        d[..2].copy_from_slice(&id.to_be_bytes());
        d[2..4].copy_from_slice(&0x8180u16.to_be_bytes());
        d[4..6].copy_from_slice(&1u16.to_be_bytes());
        d[6..8].copy_from_slice(&1u16.to_be_bytes());
        for x in name.split('.'){d.push(x.len() as u8);d.extend_from_slice(x.as_bytes())}
        d.push(0);d.extend_from_slice(&1u16.to_be_bytes());d.extend_from_slice(&1u16.to_be_bytes());
        d.extend_from_slice(&[0xc0,12]);
        d.extend_from_slice(&1u16.to_be_bytes());d.extend_from_slice(&1u16.to_be_bytes());
        d.extend_from_slice(&60u32.to_be_bytes());d.extend_from_slice(&4u16.to_be_bytes());
        d.extend_from_slice(&[198,51,100,44]);d
    }
    #[test]
    fn plan029_dns_query_coalesces_only_exact_resolver_lane_policy_and_question(){
        let mut p=DnsPending::new(2,3);
        let a=p.begin(key(ResolverLane::Tunnel,"global.example"),client(15001,7),10,5000).unwrap();
        let a2=p.begin(key(ResolverLane::Tunnel,"global.example"),client(15002,8),11,5000).unwrap();
        assert_eq!(a.upstream_id,a2.upstream_id);
        assert!(!a2.new_upstream_query);
        let b=p.begin(key(ResolverLane::Direct,"global.example"),client(15003,9),12,5000).unwrap();
        assert_ne!(a.upstream_id,b.upstream_id);
        assert_eq!(p.begin(key(ResolverLane::Direct,"other.example"),
            client(15004,10),13,5000),Err(DnsPendingError::WaitersFull));
        assert_eq!(p.counts(),(2,3));
        let reply=response(a.upstream_id,"global.example");
        assert_eq!(p.accept(a.upstream_id,0x01010101,53,ResolverLane::Direct,
            &reply,100),Err(DnsPendingError::SourceMismatch));
        assert_eq!(p.accept(a.upstream_id,0x01010102,53,ResolverLane::Tunnel,
            &reply,100),Err(DnsPendingError::SourceMismatch));
        assert_eq!(p.counts(),(2,3));
        let accepted=p.accept(a.upstream_id,0x01010101,53,ResolverLane::Tunnel,
            &reply,100).unwrap();
        assert_eq!(accepted.waiters,vec![client(15001,7),client(15002,8)]);
        assert_eq!(accepted.answer.candidates.len(),1);
        assert_eq!(p.counts(),(1,1));
    }
    #[test]
    fn plan029_dns_blackhole_only_original_waiters_fail_not_cross_direction(){
        let mut p=DnsPending::new(2,8);
        let direct=p.begin(key(ResolverLane::Direct,"cn.example"),client(1001,1),100,1000).unwrap();
        let tunnel=p.begin(key(ResolverLane::Tunnel,"intl.example"),client(1002,2),200,4000).unwrap();
        assert_ne!(direct.upstream_id,tunnel.upstream_id);
        assert_eq!(p.expire(1100),vec![client(1001,1)]);
        assert_eq!(p.counts(),(1,1));
        assert_eq!(p.accept(direct.upstream_id,0x01010101,53,
            ResolverLane::Direct,&response(direct.upstream_id,"cn.example"),1101),
            Err(DnsPendingError::UnknownTransaction));
        let good=response(tunnel.upstream_id,"intl.example");
        assert!(p.accept(tunnel.upstream_id,0x01010101,53,
            ResolverLane::Tunnel,&good,1102).is_ok());
        assert_eq!(p.counts(),(0,0));
    }
    #[test]
    fn plan029_dns_truncated_udp_only_tcp_same_endpoint_preserves_waiters(){
        let mut p=DnsPending::new(1,4);
        let q=p.begin(key(ResolverLane::Tunnel,"global.example"),client(7007,71),0,2000).unwrap();
        let mut truncated=response(q.upstream_id,"global.example");
        truncated[2..4].copy_from_slice(&0x8380u16.to_be_bytes());
        assert_eq!(p.accept(q.upstream_id,0x01010101,53,ResolverLane::Tunnel,
            &truncated,100),Err(DnsPendingError::TruncatedSameEndpointTcp));
        assert_eq!(p.counts(),(1,1));
        assert_eq!(p.accept(q.upstream_id,0x01010101,53,ResolverLane::Direct,
            &response(q.upstream_id,"global.example"),101),
            Err(DnsPendingError::SourceMismatch));
        let good=p.accept(q.upstream_id,0x01010101,53,ResolverLane::Tunnel,
            &response(q.upstream_id,"global.example"),102).unwrap();
        assert_eq!(good.waiters,vec![client(7007,71)]);
        assert_eq!(p.counts(),(0,0));
    }
    #[test]
    fn plan029_dns_no_backup_on_full_transaction_or_stop(){
        let mut p=DnsPending::new(1,4);
        let _=p.begin(key(ResolverLane::Direct,"cn.example"),client(111,3),1,5000).unwrap();
        assert_eq!(p.begin(key(ResolverLane::Tunnel,"intl.example"),
            client(222,4),2,5000),Err(DnsPendingError::TransactionFull));
        assert_eq!(p.cancel_all(),vec![client(111,3)]);
        assert_eq!(p.counts(),(0,0));
        assert!(p.cancel_all().is_empty());
    }
}
