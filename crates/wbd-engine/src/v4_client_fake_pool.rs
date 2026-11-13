//! PLAN029 CN-DNS selective FakeIP leases (query-level only).
//! One current-generation Rust ingress owner mutates this table on a DNS
//! reply/new-flow/FIN/timer tick. DATA uses an integer fake→real lookup,
//! never a real-CDN-IP→domain inverse, per-flow thread, file syscall or
//! global mutex. Publishing a newly assigned fake requires a durable
//! portable snapshot receipt BEFORE synthesizing the DNS answer.
use std::collections::{BTreeMap,BTreeSet,HashMap};
use std::mem::size_of;

const QUARANTINE_MS:u64=600_000;
const SYNTHETIC_MAX_TTL:u32=60;

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) enum FakeError {
    InvalidPool,PoolConflict,InvalidAnswer,
    PoolCapacity,MemoryBudget,NotFound,NotDurable,
    InvalidSnapshot,RefOverflow,
}
#[derive(Clone,Debug,Eq,PartialEq,Hash)]
pub(crate) struct FakeKey {
    pub qname:String,
    pub canonical:String,
    pub real4:u32,
    pub policy_rev:u64,
    pub resolver_rev:u64,
}
impl FakeKey {
    fn valid(&self)->bool{
        fn valid_dns_name(s:&str)->bool{
            !s.is_empty()&&s.len()<=253&&s.split('.').all(|label|
                !label.is_empty()&&label.len()<=63&&
                !label.starts_with('-')&&!label.ends_with('-')&&
                label.bytes().all(|c|c.is_ascii_lowercase()||
                    c.is_ascii_digit()||c==b'-'))
        }
        valid_dns_name(&self.qname)&&valid_dns_name(&self.canonical)&&
            self.real4!=0&&self.real4!=u32::MAX
    }
}
#[derive(Clone,Debug,Eq,PartialEq)]
pub(crate) struct FakeSnapshotEntry {
    pub fake4:u32,
    pub key:FakeKey,
    pub issued_until_ms:u64,
    pub quarantine_until_ms:u64,
}
#[derive(Clone,Debug)]
struct FakeEntry{
    key:FakeKey,
    issued_until_ms:u64,
    quarantine_until_ms:u64,
    flow_refs:u32,
    announced:bool,
    needs_durable_write:bool,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) struct FakeProposal{
    pub fake4:u32,
    pub advertised_ttl:u32,
    /// Always write the portable snapshot atomically before publishing
    /// a new DNS answer. A previously issued fake may remain usable for
    /// existing pinned flows while its renewed TTL is being persisted.
    pub persist_before_reply:bool,
}
pub(crate) struct FakeAllocator{
    start4:u32,end4:u32,next4:u32,
    max_entries:usize,max_accounted_bytes:usize,
    bytes_used:usize,
    fake_to_entry:HashMap<u32,FakeEntry>,
    key_to_fake:HashMap<FakeKey,u32>,
    // One scheduler coarse timer, never a per-DATA full-table scan.
    reap_due:BTreeMap<u64,BTreeSet<u32>>,
}
impl FakeAllocator{
    /// Caller must supply all current Windows physical/LAN, lease,
    /// server and user-direct ranges. Conflict fails BEFORE any fake
    /// address appears in an answer; this does not mutate OS routes.
    pub fn new(start4:u32,end4:u32,forbidden:&[(u32,u32)],
        max_entries:usize,max_bytes:usize)->Result<Self,FakeError>{
        let width=u64::from(end4).saturating_sub(u64::from(start4))+1;
        if start4==0||start4>=end4||width>65_536||
            max_entries==0||max_entries>60_000||
            max_entries as u64>width||max_bytes<1024||
            max_bytes>16*1024*1024{
            return Err(FakeError::InvalidPool)
        }
        if forbidden.iter().any(|&(a,b)|a>b||a<=end4&&b>=start4){
            return Err(FakeError::PoolConflict)
        }
        Ok(Self{start4,end4,next4:start4,max_entries,
            max_accounted_bytes:max_bytes,bytes_used:0,
            fake_to_entry:HashMap::new(),key_to_fake:HashMap::new(),
            reap_due:BTreeMap::new()})
    }
    fn accounted(key:&FakeKey)->usize{
        // Conservative entry budget includes both HashMap keys and one
        // BTree expiry node. This is an accounting ceiling, not an observed
        // allocator RSS claim; RSS must be measured at D3/P2.
        size_of::<FakeEntry>()+size_of::<FakeKey>()+
            2*(key.qname.len()+key.canonical.len())+160
    }
    fn remove_due(&mut self,due:u64,ip:u32){
        let mut empty=false;
        if let Some(bucket)=self.reap_due.get_mut(&due){
            bucket.remove(&ip);
            empty=bucket.is_empty();
        }
        if empty{self.reap_due.remove(&due);}
    }
    fn insert_due(&mut self,due:u64,ip:u32){
        self.reap_due.entry(due).or_default().insert(ip);
    }
    /// Only a successfully resolved CN QNAME/A may call this; overseas
    /// CN-CDN addresses get DISTINCT fakes from unrelated overseas domains.
    /// TTL0 still reserves an identity for at least 10 min quarantine.
    pub fn prepare(&mut self,key:FakeKey,upstream_min_ttl:u32,
        now_ms:u64)->Result<FakeProposal,FakeError>{
        if !key.valid(){return Err(FakeError::InvalidAnswer)}
        let ttl=upstream_min_ttl.min(SYNTHETIC_MAX_TTL);
        let issue_until=now_ms.saturating_add(u64::from(ttl)*1000);
        let quarantine_until=issue_until.saturating_add(QUARANTINE_MS);
        if let Some(&ip)=self.key_to_fake.get(&key){
            let Some(old)=self.fake_to_entry.get(&ip)else{
                return Err(FakeError::InvalidSnapshot)
            };
            let prev_due=old.quarantine_until_ms;
            let new_due=prev_due.max(quarantine_until);
            if new_due!=prev_due{
                self.remove_due(prev_due,ip);
                self.insert_due(new_due,ip);
            }
            let e=self.fake_to_entry.get_mut(&ip).ok_or(FakeError::InvalidSnapshot)?;
            if issue_until>e.issued_until_ms{
                e.issued_until_ms=issue_until;
                e.quarantine_until_ms=new_due;
                e.needs_durable_write=true;
            }
            return Ok(FakeProposal{fake4:ip,advertised_ttl:ttl,
                persist_before_reply:e.needs_durable_write})
        }
        let charged=Self::accounted(&key);
        if self.fake_to_entry.len()>=self.max_entries ||
           charged>self.max_accounted_bytes.saturating_sub(self.bytes_used){
            // Only on pressure: bounded due-wheel reclaim, never an
            // all-table scan in the ordinary DNS path. A live reference
            // or a still-quarantined identity is never stolen to make room.
            self.reap_due(now_ms,64);
        }
        if self.fake_to_entry.len()>=self.max_entries{
            return Err(FakeError::PoolCapacity)
        }
        if charged>self.max_accounted_bytes.saturating_sub(self.bytes_used){
            return Err(FakeError::MemoryBudget)
        }
        let mut selected=None;
        for _ in self.start4..=self.end4{
            let ip=self.next4;
            self.next4=if ip==self.end4{self.start4}else{ip+1};
            if !self.fake_to_entry.contains_key(&ip){selected=Some(ip);break}
        }
        let ip=selected.ok_or(FakeError::PoolCapacity)?;
        let old=self.key_to_fake.insert(key.clone(),ip);
        if old.is_some(){return Err(FakeError::InvalidSnapshot)}
        self.fake_to_entry.insert(ip,FakeEntry{
            key,issued_until_ms:issue_until,
            quarantine_until_ms:quarantine_until,flow_refs:0,
            announced:false,needs_durable_write:true,
        });
        self.insert_due(quarantine_until,ip);
        self.bytes_used+=charged;
        Ok(FakeProposal{fake4:ip,advertised_ttl:ttl,persist_before_reply:true})
    }
    /// Cold/sparse write preparation. The owner must atomically replace its
    /// portable snapshot + fsync policy before calling acknowledge_durable;
    /// no DNS answer may contain a fake while persist_before_reply=true.
    /// Pending records are included so a crash after rename but before
    /// publish only over-reserves an unused fake (never misroutes).
    /// One journal-writer batch looks up only the pending fake identities
    /// by integer key. Avoids copying an entire 60k DNS mapping snapshot
    /// or touching filesystem state for each sparse DNS answer.
    pub fn pending_snapshot(&self,ip:u32)->Option<FakeSnapshotEntry>{
        let e=self.fake_to_entry.get(&ip)?;
        e.needs_durable_write.then(||FakeSnapshotEntry{
            fake4:ip,key:e.key.clone(),issued_until_ms:e.issued_until_ms,
            quarantine_until_ms:e.quarantine_until_ms,
        })
    }
    pub fn durable_candidate(&self)->Vec<FakeSnapshotEntry>{
        let mut result=self.fake_to_entry.iter().map(|(&ip,e)|FakeSnapshotEntry{
            fake4:ip,key:e.key.clone(),issued_until_ms:e.issued_until_ms,
            quarantine_until_ms:e.quarantine_until_ms,
        }).collect::<Vec<_>>();
        result.sort_by_key(|e|e.fake4);
        result
    }
    /// Only after real durable file receipt, not a no-op guard.
    pub fn acknowledge_durable(&mut self,ip:u32)->Result<(),FakeError>{
        let e=self.fake_to_entry.get_mut(&ip).ok_or(FakeError::NotFound)?;
        e.needs_durable_write=false;e.announced=true;Ok(())
    }
    /// Called at the actual first business flow, not for every TCP DATA.
    /// Old mapping remains available beyond DNS TTL during quarantine.
    pub fn pin_first_flow(&mut self,ip:u32)->Result<u32,FakeError>{
        let e=self.fake_to_entry.get_mut(&ip).ok_or(FakeError::NotFound)?;
        if !e.announced{return Err(FakeError::NotDurable)}
        e.flow_refs=e.flow_refs.checked_add(1).ok_or(FakeError::RefOverflow)?;
        Ok(e.key.real4)
    }
    /// DATA hot path only uses the immutable original flow's pinned real4.
    /// This method is for first-flow classification and diagnostics only.
    pub fn announced_real(&self,ip:u32)->Option<u32>{
        self.fake_to_entry.get(&ip).and_then(|e|e.announced.then_some(e.key.real4))
    }
    /// Only the DNS answer writer calls this after real portable snapshot
    /// persistence. It requires the EXACT original hostname + canonical
    /// chain + A candidate + policy/resolver revision, not an IP reverse
    /// association. Expired announced TTL may retain its quarantine identity
    /// for existing flows, but cannot be republished in a fresh DNS reply.
    pub fn issued_for(&self,key:&FakeKey,now_unix_ms:u64)->Option<u32>{
        let fake=*self.key_to_fake.get(key)?;
        let e=self.fake_to_entry.get(&fake)?;
        (e.announced&&!e.needs_durable_write&&e.key==*key&&
            e.issued_until_ms>=now_unix_ms).then_some(fake)
    }
    pub fn release_flow(&mut self,ip:u32,_now_ms:u64)->Result<(),FakeError>{
        let e=self.fake_to_entry.get_mut(&ip).ok_or(FakeError::NotFound)?;
        if e.flow_refs==0{return Err(FakeError::InvalidSnapshot)}
        e.flow_refs-=1;
        // Reuse the existing single scheduled quarantine/wheel entry.
        // Do not push a second due event for the same fake: duplicate
        // entries otherwise survive indefinitely after reap.
        Ok(())
    }
    /// At most 'budget' due entries each coarse worker tick, never a
    /// full 60k scan. A held ref survives TTL and the 10-minute quarantine.
    pub fn reap_due(&mut self,now_ms:u64,budget:usize)->usize{
        let mut removed=0usize;
        let mut handled=0usize;
        while handled<budget {
            let Some((&due,_))=self.reap_due.iter().next()else{break};
            if due>now_ms{break}
            let ip=*self.reap_due.get(&due).unwrap().iter().next().unwrap();
            self.remove_due(due,ip);
            handled+=1;
            let Some(entry)=self.fake_to_entry.get(&ip)else{continue};
            if entry.quarantine_until_ms>now_ms{
                self.insert_due(entry.quarantine_until_ms,ip);
                continue
            }
            if entry.flow_refs>0{
                self.insert_due(now_ms.saturating_add(60_000),ip);
                continue
            }
            let entry=self.fake_to_entry.remove(&ip).unwrap();
            self.key_to_fake.remove(&entry.key);
            self.bytes_used-=Self::accounted(&entry.key);
            removed+=1;
        }
        removed
    }
    /// Crash/restart restoration. The caller reads the prior atomically
    /// persisted owned snapshot (not a foreign guessed real-CDN table),
    /// validates the same pool/conflict policy, and keeps still quarantined
    /// issued addresses to protect stale application DNS caches.
    pub fn restore(&mut self,entries:&[FakeSnapshotEntry],
        now_ms:u64)->Result<(),FakeError>{
        if !self.fake_to_entry.is_empty()||!self.key_to_fake.is_empty(){
            return Err(FakeError::InvalidSnapshot)
        }
        if entries.len()>self.max_entries{return Err(FakeError::PoolCapacity)}
        let mut staged=Vec::new();
        let mut total=0usize;
        let mut used=BTreeSet::new();
        let mut keys=std::collections::HashSet::new();
        for e in entries{
            if e.fake4<self.start4||e.fake4>self.end4||!e.key.valid()||
                e.quarantine_until_ms<e.issued_until_ms||
                e.quarantine_until_ms-e.issued_until_ms<QUARANTINE_MS||
                !used.insert(e.fake4)||!keys.insert(e.key.clone()){
                return Err(FakeError::InvalidSnapshot)
            }
            if e.quarantine_until_ms<=now_ms{continue}
            let charge=Self::accounted(&e.key);
            total=total.checked_add(charge).ok_or(FakeError::MemoryBudget)?;
            if total>self.max_accounted_bytes{return Err(FakeError::MemoryBudget)}
            staged.push(e.clone());
        }
        for e in staged{
            self.key_to_fake.insert(e.key.clone(),e.fake4);
            self.insert_due(e.quarantine_until_ms,e.fake4);
            self.fake_to_entry.insert(e.fake4,FakeEntry{
                key:e.key,issued_until_ms:e.issued_until_ms,
                quarantine_until_ms:e.quarantine_until_ms,flow_refs:0,
                announced:true,needs_durable_write:false,
            });
        }
        self.bytes_used=total;Ok(())
    }
    pub fn counts(&self)->(usize,usize){(self.fake_to_entry.len(),self.bytes_used)}
}

#[cfg(test)]
mod tests{
    use super::*;
    fn ip(a:u8,b:u8,c:u8,d:u8)->u32{u32::from_be_bytes([a,b,c,d])}
    fn pool(cap:usize)->FakeAllocator{
        FakeAllocator::new(ip(198,18,0,1),ip(198,18,0,200),
            &[(ip(192,168,0,0),ip(192,168,255,255))],cap,1024*1024).unwrap()
    }
    fn key(name:&str,real:u32,rev:u64)->FakeKey{
        FakeKey{qname:name.to_string(),canonical:"cdn.example".to_string(),
            real4:real,policy_rev:rev,resolver_rev:1}
    }
    #[test]
    fn plan029_cn_fakeip_cdn_shared_real_without_noncn_leak_and_persist_before_answer(){
        let real=ip(198,51,100,77);
        let mut p=pool(8);
        let cn=p.prepare(key("www.cn.example",real,1),120,100).unwrap();
        assert_eq!(cn.advertised_ttl,60);
        assert!(cn.persist_before_reply);
        assert_eq!(p.announced_real(cn.fake4),None);
        assert_eq!(p.pin_first_flow(cn.fake4),Err(FakeError::NotDurable));
        let snapshot=p.durable_candidate();
        assert_eq!(snapshot.len(),1);
        p.acknowledge_durable(cn.fake4).unwrap();
        assert_eq!(p.pin_first_flow(cn.fake4),Ok(real));
        assert_eq!(p.announced_real(real),None); // no shared CDN reverse key
        let cn2=p.prepare(key("another.cn.example",real,1),30,120).unwrap();
        assert_ne!(cn.fake4,cn2.fake4);
        p.acknowledge_durable(cn2.fake4).unwrap();
        assert_eq!(p.announced_real(cn2.fake4),Some(real));
        p.release_flow(cn.fake4,200).unwrap();
    }
    #[test]
    fn plan029_cn_fakeip_ttl_zero_quarantine_ref_and_same_identity_restart(){
        let real=ip(203,0,113,44);
        let mut p=pool(2);
        let key=key("china.example",real,7);
        let first=p.prepare(key.clone(),0,1000).unwrap();
        assert_eq!(first.advertised_ttl,0);
        p.acknowledge_durable(first.fake4).unwrap();
        assert_eq!(p.pin_first_flow(first.fake4),Ok(real));
        assert_eq!(p.reap_due(601000,8),0); // live flow must not rebind
        let restored=p.durable_candidate();
        p.release_flow(first.fake4,601100).unwrap();
        assert_eq!(p.reap_due(601100,8),0); // held flow scheduled later
        assert_eq!(p.reap_due(661100,8),1);
        let mut cold=pool(2);
        cold.restore(&restored,2000).unwrap();
        assert_eq!(cold.announced_real(first.fake4),Some(real));
        let again=cold.prepare(key,20,2100).unwrap();
        assert_eq!(again.fake4,first.fake4); // no new alias for a cached name
    }
    #[test]
    fn plan029_cn_fakeip_hard_full_fails_without_evicting_active_or_wrong_side(){
        let mut p=pool(1);
        let first=p.prepare(key("cn-a.example",ip(8,8,8,8),1),10,100).unwrap();
        p.acknowledge_durable(first.fake4).unwrap();
        assert_eq!(p.prepare(key("cn-b.example",ip(8,8,4,4),1),10,200),
            Err(FakeError::PoolCapacity));
        assert_eq!(p.announced_real(first.fake4),Some(ip(8,8,8,8)));
        assert_eq!(p.counts().0,1);
        assert!(matches!(FakeAllocator::new(ip(198,18,0,1),
            ip(198,18,0,200),&[(ip(198,18,0,50),ip(198,18,0,55))],
            8,4096),Err(FakeError::PoolConflict)));
    }
    #[test]
    fn plan029_fake_pool_pressure_reclaims_only_safe_expired_slot_before_refusing(){
        let mut p=pool(1);
        let first=p.prepare(key("one.cn.example",ip(198,51,100,2),1),0,100).unwrap();
        p.acknowledge_durable(first.fake4).unwrap();
        // Deadline 600100, but the previous coarse tick may not have run.
        // The next DNS query must perform a bounded safe reclaim.
        assert_eq!(p.prepare(key("two.cn.example",ip(198,51,100,3),1),1,600099),
            Err(FakeError::PoolCapacity));
        let second=p.prepare(key("two.cn.example",ip(198,51,100,3),1),1,600101).unwrap();
        // The pool advances to a fresh free slot; reaping only guarantees
        // that the old key/identity is no longer active, NOT that the
        // next allocation must reuse its exact numerical IPv4 address.
        assert_ne!(second.fake4,first.fake4);
        assert!(second.persist_before_reply);
        assert_eq!(p.announced_real(first.fake4),None);
        p.acknowledge_durable(second.fake4).unwrap();
        assert_eq!(p.announced_real(second.fake4),Some(ip(198,51,100,3)));

        let mut held=pool(1);
        let live=held.prepare(key("held.cn.example",ip(203,0,113,7),1),0,100).unwrap();
        held.acknowledge_durable(live.fake4).unwrap();
        held.pin_first_flow(live.fake4).unwrap();
        assert_eq!(held.prepare(key("new.cn.example",ip(203,0,113,8),1),1,600101),
            Err(FakeError::PoolCapacity));
        assert_eq!(held.announced_real(live.fake4),Some(ip(203,0,113,7)));
        held.release_flow(live.fake4,600102).unwrap();
        assert!(held.prepare(key("new.cn.example",ip(203,0,113,8),1),1,660102).is_ok());
    }
    #[test]
    fn plan029_cn_fakeip_corrupt_snapshot_rejected_not_rebound(){
        let mut p=pool(3);
        let f=p.prepare(key("cn.example",ip(8,8,8,8),1),1,1000).unwrap();
        let mut s=p.durable_candidate();
        s[0].key.real4=0;
        let mut cold=pool(3);
        assert_eq!(cold.restore(&s,2000),Err(FakeError::InvalidSnapshot));
        assert_eq!(cold.counts().0,0);
        assert_eq!(p.pin_first_flow(f.fake4),Err(FakeError::NotDurable));
    }
}
