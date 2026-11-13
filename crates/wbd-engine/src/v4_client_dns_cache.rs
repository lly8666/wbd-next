//! PLAN029 single-generation DNS-only cache. A miss NEVER blocks a new
//! query because this cache is full; DnsPending owns the separate 256-ticket
//! limit. QNAME/endpoint/direction/policy pin all identities independently.
//! There is no per-packet timer, real-IP reverse-domain learning, socket,
//! fallback resolver, or fake-IP ownership in this component.
use std::collections::{BTreeMap,HashMap};
use std::mem::size_of;
use crate::v4_client_dns_pending::QueryKey;
use crate::v4_client_dns_answer::{DnsAResolution,DnsAnswerStatus,ResolvedA};

const DEFAULT_ENTRIES:usize=4096;
const DEFAULT_BYTES:usize=8*1024*1024;
const MAX_POSITIVE_TTL_S:u32=300;

struct Item {
    answer:DnsAResolution,
    inserted_ms:u64,
    expires_ms:u64,
    charged:usize,
    age:u64,
}
pub(crate) struct DnsAnswerCache {
    entries:HashMap<QueryKey,Item>,
    by_age:BTreeMap<u64,QueryKey>,
    max_entries:usize,
    max_bytes:usize,
    allocated_bytes:usize,
    next_age:u64,
}
impl DnsAnswerCache {
    pub fn production()->Self{Self::new(DEFAULT_ENTRIES,DEFAULT_BYTES)}
    /// Small quotas are deliberately allowed in D3/P2 focused capacity
    /// fixtures. No production socket or physical memory allocation here.
    pub fn new(max_entries:usize,max_bytes:usize)->Self{
        Self{entries:HashMap::new(),by_age:BTreeMap::new(),
            max_entries:max_entries.clamp(1,DEFAULT_ENTRIES),
            max_bytes:max_bytes.clamp(256,DEFAULT_BYTES),
            allocated_bytes:0,next_age:1}
    }
    pub fn counts(&self)->(usize,usize){(self.entries.len(),self.allocated_bytes)}
    fn cost(key:&QueryKey,a:&DnsAResolution)->usize{
        size_of::<QueryKey>()+size_of::<Item>()+
            size_of::<DnsAResolution>()+key.name.len()+a.canonical.len()+
            a.cname_chain.iter().map(|x|x.len()+size_of::<String>()).sum::<usize>()+
            a.candidates.len()*size_of::<ResolvedA>()+128
    }
    fn remove(&mut self,key:&QueryKey)->bool{
        let Some(item)=self.entries.remove(key)else{return false};
        self.allocated_bytes-=item.charged;
        self.by_age.remove(&item.age);
        true
    }
    fn stamp(&mut self)->Option<u64>{
        let age=self.next_age;
        self.next_age=self.next_age.checked_add(1)?;
        Some(age)
    }
    /// Returns None on a true miss or expired record, not an error to the
    /// resolver. TTL is strictly reduced (rounded UP elapsed seconds);
    /// a cache HIT never renews expiry, FakeIP lease or upstream transport.
    pub fn get(&mut self,key:&QueryKey,now_ms:u64)->Option<DnsAResolution>{
        let old=self.entries.get(key)?;
        if now_ms>=old.expires_ms{
            self.remove(key);
            return None
        }
        let elapsed=now_ms.saturating_sub(old.inserted_ms)
            .saturating_add(999)/1000;
        let elapsed=u32::try_from(elapsed).unwrap_or(u32::MAX);
        let mut answer=old.answer.clone();
        for candidate in &mut answer.candidates{
            candidate.ttl=candidate.ttl.saturating_sub(elapsed);
        }
        let prior_age=old.age;
        if let Some(next)=self.stamp(){
            self.by_age.remove(&prior_age);
            if let Some(old)=self.entries.get_mut(key){old.age=next}
            self.by_age.insert(next,key.clone());
        }
        Some(answer)
    }
    /// Only a VALIDATED upstream answer is eligible. The cache is not the
    /// source of truth for DNS negative TTL (authority SOA not retained by
    /// DnsAResolution), so NXDOMAIN/NoData/Truncated are deliberately not
    /// cached. A positive TTL0 is also never memoized.
    /// False means 'skip caching', NEVER 'fail or fallback DNS query'.
    pub fn insert(&mut self,key:QueryKey,answer:DnsAResolution,now_ms:u64)->bool{
        if !key.validate()||answer.status!=DnsAnswerStatus::Answered||
           answer.candidates.is_empty()||answer.candidates.len()>16{
            return false
        }
        let ttl=answer.candidates.iter().map(|c|c.ttl)
            .min().unwrap_or(0).min(MAX_POSITIVE_TTL_S);
        if ttl==0{return false}
        let charged=Self::cost(&key,&answer);
        if charged>self.max_bytes{return false}
        let age=match self.stamp(){Some(a)=>a,None=>return false};
        self.remove(&key);
        // DNS cold path only, at most the existing bounded cache length.
        // Eviction targets the old LRU; expired entries need no separate
        // scanning loop. Active FakeIP associations live in another table.
        while self.entries.len()>=self.max_entries ||
              self.allocated_bytes>self.max_bytes.saturating_sub(charged){
            let Some((_,old))=self.by_age.first_key_value()else{
                return false
            };
            let victim=old.clone();
            self.remove(&victim);
        }
        let expires_ms=now_ms.saturating_add(u64::from(ttl)*1000);
        self.by_age.insert(age,key.clone());
        self.entries.insert(key,Item{answer,inserted_ms:now_ms,
            expires_ms,charged,age});
        self.allocated_bytes+=charged;
        true
    }
    pub fn clear(&mut self){
        self.entries.clear();self.by_age.clear();
        self.allocated_bytes=0;self.next_age=1;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::v4_client_dns_pending::ResolverLane;
    fn key(lane:ResolverLane,name:&str,policy_revision:u64)->QueryKey{
        QueryKey{name:name.into(),qtype:1,lane,resolver4:0x01010101,
            resolver_port:53,policy_revision}
    }
    fn answer(real4:u32,ttl:u32)->DnsAResolution{
        DnsAResolution{status:DnsAnswerStatus::Answered,
            canonical:"edge.cdn.example".into(),
            cname_chain:vec!["cn.example".into()],
            candidates:vec![ResolvedA{address:real4,ttl}]}
    }
    #[test]
    fn plan029_dns_cache_per_endpoint_lane_policy_and_shared_cdn_isolation(){
        let direct=key(ResolverLane::Direct,"cn.example",1);
        let mut tunnel=key(ResolverLane::Tunnel,"cn.example",1);
        let same_cdn=0xc633644d;
        let mut c=DnsAnswerCache::new(4,4096);
        assert!(c.insert(direct.clone(),answer(same_cdn,60),1000));
        assert_eq!(c.get(&tunnel,1100),None);
        tunnel.lane=ResolverLane::Direct;tunnel.resolver4=0x08080808;
        assert_eq!(c.get(&tunnel,1100),None);
        assert_eq!(c.get(&key(ResolverLane::Direct,"cn.example",2),1100),None);
        assert_eq!(c.get(&key(ResolverLane::Direct,"noncn.example",1),1100),None);
        assert_eq!(c.get(&direct,1100).unwrap().candidates[0].address,same_cdn);
        assert_eq!(c.counts().0,1);
    }
    #[test]
    fn plan029_dns_cache_hit_reduces_ttl_never_renews_lifetime(){
        let k=key(ResolverLane::Direct,"cn.example",1);
        let mut c=DnsAnswerCache::new(2,4096);
        assert!(c.insert(k.clone(),answer(0xcb007101,2),100));
        assert_eq!(c.get(&k,101).unwrap().candidates[0].ttl,1);
        assert_eq!(c.get(&k,1099).unwrap().candidates[0].ttl,1);
        assert_eq!(c.get(&k,2100),None);
        assert_eq!(c.counts(),(0,0));
        assert!(!c.insert(k,answer(0xcb007101,0),2100));
    }
    #[test]
    fn plan029_dns_cache_lru_and_bytes_pressure_never_block_query(){
        let mut c=DnsAnswerCache::new(2,1024);
        let a=key(ResolverLane::Direct,"a.cn.example",1);
        let b=key(ResolverLane::Direct,"b.cn.example",1);
        let d=key(ResolverLane::Direct,"d.cn.example",1);
        assert!(c.insert(a.clone(),answer(1,10),0));
        assert!(c.insert(b.clone(),answer(2,10),0));
        c.get(&a,1);
        assert!(c.insert(d.clone(),answer(4,10),2));
        assert_eq!(c.get(&b,3),None);
        assert_eq!(c.get(&a,3).unwrap().candidates[0].address,1);
        assert_eq!(c.get(&d,3).unwrap().candidates[0].address,4);
        assert!(c.counts().1<=1024);
        // This is a cache skip, not a resolver failure/secret retry.
        let giant=key(ResolverLane::Tunnel,&"x".repeat(3000),1);
        assert!(!c.insert(giant,answer(8,30),10));
        assert!(c.get(&a,10).is_some());
        c.clear();
        assert_eq!(c.counts(),(0,0));
    }
    #[test]
    fn plan029_dns_cache_nxdomain_truncated_error_are_not_cached(){
        let mut c=DnsAnswerCache::production();
        let k=key(ResolverLane::Tunnel,"noncn.example",1);
        for kind in [DnsAnswerStatus::NoData,DnsAnswerStatus::NxDomain,
                     DnsAnswerStatus::Truncated,DnsAnswerStatus::UpstreamError]{
            let mut a=answer(1,99);a.status=kind;
            assert!(!c.insert(k.clone(),a,1));
            assert_eq!(c.get(&k,2),None);
        }
        assert_eq!(c.counts(),(0,0));
    }
}
