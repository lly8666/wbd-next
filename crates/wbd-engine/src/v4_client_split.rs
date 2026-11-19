//! PLAN029 Windows client split decision core: one cold immutable policy for
//! Normal/Game ingress. No socket, Wintun, Go per-packet callback or TLS/SNI
//! parsing here. This module MUST NOT grant Direct product readiness alone.
//! Raw observed IPs and selective FakeIP are distinct: never infer domain
//! identity from a shared real CDN address.
use std::collections::HashMap;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Ipv4Cidr {
    pub network: u32, // big-endian host numeric value
    pub bits: u8,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum SplitError {
    InvalidCidr,
    InvalidDomain,
    UnsupportedDomainRule,
    FakeIPConflict,
}
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub(crate) struct Ranges(Vec<(u32,u32)>);
impl Ranges {
    pub fn compile(cidrs: &[Ipv4Cidr]) -> Result<Self, SplitError> {
        let mut spans=Vec::with_capacity(cidrs.len());
        for c in cidrs {
            if c.bits>32 {return Err(SplitError::InvalidCidr);}
            let mask=if c.bits==0 {0}else{u32::MAX << (32-c.bits)};
            let start=c.network&mask;
            spans.push((start,start|!mask));
        }
        spans.sort_unstable();
        let mut merged:Vec<(u32,u32)>=Vec::with_capacity(spans.len());
        for (start,end) in spans {
            if let Some(last)=merged.last_mut() {
                if start<=last.1.saturating_add(1) {
                    last.1=last.1.max(end);
                    continue;
                }
            }
            merged.push((start,end));
        }
        Ok(Self(merged))
    }
    #[inline]
    pub fn contains(&self,ip:u32)->bool {
        let end=self.0.partition_point(|(start,_)| *start<=ip);
        end>0&&ip<=self.0[end-1].1
    }
    /// Exact exclusive synthetic interval. Advanced FakeIP pool may be
    /// narrower than a CIDR; representing only endpoints is unsafe.
    pub fn interval(first:u32,last:u32)->Result<Self,SplitError>{
        if first>last{return Err(SplitError::InvalidCidr)}
        Ok(Self(vec![(first,last)]))
    }
    pub fn interval_count(&self)->usize{self.0.len()}
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum Mode {All, BypassLan, BypassLanCn}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum Egress {
    Tunnel,
    Direct {real_dst:u32, presented_dst:u32},
    RejectUnknownFakeIP,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum DnsUse {
    ServerBootstrap, // ONE dns.direct, always physical even under All
    InternalDirect,  // never reclassified by destination IPv4
    InternalTunnel,  // never reclassified by CN/LAN IP of upstream
    Ordinary {china_domain:bool},
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum DnsEgress {Direct, Tunnel}

#[derive(Debug)]
pub(crate) struct SplitPolicy {
    mode:Mode,
    lan:Ranges,
    cn:Ranges,
    direct4:Ranges,
    fake_pool:Ranges,
    // Cold-issued, persisted before DNS reply. No DATA-time DNS string
    // parsing; these are finite integer lookups. Missing FakeIP rejects.
    fake_to_real:HashMap<u32,u32>,
}
impl SplitPolicy {
    pub fn new(mode:Mode,lan:Ranges,cn:Ranges,direct4:Ranges,fake_pool:Ranges)->Self{
        Self{mode,lan,cn,direct4,fake_pool,fake_to_real:HashMap::new()}
    }
    /// Only CN union mode may turn an announced FakeIP into a Direct
    /// business target. The DNS worker must have durable-journaled the
    /// mapping before passing it to this cold/first-flow admission method.
    /// Never infer hostname from the real shared CDN address.
    pub fn announced_fake_target(&self,fake:u32,real:u32)->Option<Egress>{
        if self.mode!=Mode::BypassLanCn || !self.fake_pool.contains(fake) ||
           real==0 || real==u32::MAX || self.fake_pool.contains(real){
            return None
        }
        Some(Egress::Direct{real_dst:real,presented_dst:fake})
    }
    pub fn dns_egress(&self,purpose:DnsUse)->DnsEgress{
        match purpose {
            DnsUse::ServerBootstrap|DnsUse::InternalDirect=>DnsEgress::Direct,
            DnsUse::InternalTunnel=>DnsEgress::Tunnel,
            DnsUse::Ordinary{china_domain:true} if self.mode==Mode::BypassLanCn=>DnsEgress::Direct,
            DnsUse::Ordinary{..}=>DnsEgress::Tunnel,
        }
    }
    pub fn remember_announced_fake(&mut self,fake:u32,real:u32)->Result<(),SplitError>{
        // The cold restore of a durable DNS A must enforce the SAME
        // admission bounds as a newly issued synthetic DNS response:
        // never resurrect zero/broadcast/another FakeIP as physical Direct.
        if self.announced_fake_target(fake,real).is_none(){
            return Err(SplitError::FakeIPConflict);
        }
        if let Some(old)=self.fake_to_real.get(&fake) {
            if *old!=real{return Err(SplitError::FakeIPConflict)}
            return Ok(());
        }
        self.fake_to_real.insert(fake,real);
        Ok(())
    }
    /// Exact cold all-mode fast admission for a complete, non-DNS IPv4
    /// datagram. Never bypass reject-unknown-FakeIP even in Tunnel-only
    /// mode. No shared-CDN reverse inference or mutable flow-pin lookup.
    #[inline]
    pub(crate) fn plain_all_tunnel(&self,dst:u32)->bool{
        self.mode==Mode::All && !self.fake_pool.contains(dst)
    }
    #[inline]
    pub fn destination(&self,ip:u32)->Egress{
        if self.fake_pool.contains(ip){
            if self.mode!=Mode::BypassLanCn{return Egress::RejectUnknownFakeIP}
            return match self.fake_to_real.get(&ip){
                Some(&real)=>Egress::Direct{real_dst:real,presented_dst:ip},
                None=>Egress::RejectUnknownFakeIP,
            };
        }
        if self.mode!=Mode::All &&
            (self.lan.contains(ip)||self.direct4.contains(ip)||
             (self.mode==Mode::BypassLanCn&&self.cn.contains(ip))) {
            return Egress::Direct{real_dst:ip,presented_dst:ip};
        }
        Egress::Tunnel
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum DomainRuleType {Exact,Suffix,Keyword,Regex}
#[derive(Default)]
struct DomainNode {
    exact:bool,
    suffix:bool,
    children:HashMap<String,DomainNode>,
}
#[derive(Default)]
pub(crate) struct DomainIndex {
    root:DomainNode,
    // Keyword/regex are intentionally not silently downgraded to suffix.
    // A full v2fly regex matcher must be installed before those rules enter
    // a production snapshot. This builder rejects unsupported imports.
    rule_count:usize,
}
fn domain_labels(input:&str)->Result<Vec<&str>,SplitError>{
    let text=input.strip_suffix('.').unwrap_or(input);
    if text.is_empty()||text.len()>253||!text.is_ascii(){return Err(SplitError::InvalidDomain)}
    let labels=text.split('.').collect::<Vec<_>>();
    if labels.iter().any(|part|{
        part.is_empty()||part.len()>63||part.starts_with('-')||part.ends_with('-')||
        !part.bytes().all(|b|b.is_ascii_alphanumeric()||b==b'-')
    }){return Err(SplitError::InvalidDomain);}
    Ok(labels)
}
impl DomainIndex {
    pub fn insert(&mut self,domain:&str,kind:DomainRuleType)->Result<(),SplitError>{
        match kind {
            DomainRuleType::Keyword|DomainRuleType::Regex=>{
                return Err(SplitError::UnsupportedDomainRule)
            }
            _=>{}
        }
        let labels=domain_labels(domain)?;
        let mut node=&mut self.root;
        for label in labels.iter().rev(){
            node=node.children.entry(label.to_ascii_lowercase()).or_default();
        }
        match kind{DomainRuleType::Exact=>node.exact=true,DomainRuleType::Suffix=>node.suffix=true,_=>unreachable!()}
        self.rule_count+=1;
        Ok(())
    }
    pub fn contains(&self,domain:&str)->Result<bool,SplitError>{
        let labels=domain_labels(domain)?;
        let mut node=&self.root;
        for (i,label) in labels.iter().rev().enumerate(){
            let lower=label.to_ascii_lowercase();
            let Some(child)=node.children.get(&lower) else{return Ok(false)};
            node=child;
            if node.suffix{return Ok(true);}
            if i+1==labels.len()&&node.exact{return Ok(true);}
        }
        Ok(false)
    }
    pub fn len(&self)->usize{self.rule_count}
}
/// Already-classified active TCP/UDP flows never switch exit during a DNS
/// TTL refresh, lane rotation, or a new cold CIDR/domain snapshot. The caller
/// retires flows at its actual FIN/RST/UDP-idle owner lifecycle (not every
/// 30s to restart startup padding). No per-flow thread or clock.
#[derive(Clone,Copy,Debug,Eq,PartialEq,Hash)]
pub(crate) struct FlowKey{
    pub source:u32,pub destination:u32,
    pub source_port:u16,pub destination_port:u16,pub protocol:u8,
}
/// Compact pin state is separate from the socket/buffer/transaction quotas.
/// Direct-only pressure must NEVER suppress a new ordinary Tunnel frame:
/// Tunnel's existing Rust owner retains its own independent admission gate.
/// A full opportunistic Tunnel pin cache simply uses the current immutable
/// policy for that packet; no global flow queue or per-packet timer is added.
pub(crate) struct FlowPin {
    bound:HashMap<FlowKey,Egress>,
    direct_hard:usize,
    tunnel_pin_soft:usize,
    direct_pins:usize,
    tunnel_pins:usize,
}
impl FlowPin{
    pub fn new(direct_hard:usize)->Self{
        Self::with_limits(direct_hard,direct_hard)
    }
    pub fn with_limits(direct_hard:usize,tunnel_pin_soft:usize)->Self{
        Self{bound:HashMap::new(),direct_hard,tunnel_pin_soft,
            direct_pins:0,tunnel_pins:0}
    }
    #[inline]
    pub fn get(&self,k:&FlowKey)->Option<Egress>{self.bound.get(k).copied()}
    pub fn first(&mut self,key:FlowKey,d:Egress)->Option<Egress>{
        if let Some(old)=self.bound.get(&key){return Some(*old)}
        match d {
            Egress::Direct{..}=>{
                if self.direct_pins>=self.direct_hard{return None}
                self.direct_pins+=1;
            }
            Egress::Tunnel=>{
                // A full pin *cache* does not deny Tunnel admission. The
                // immutable generation policy remains the source of truth
                // until reconnect; the original tunnel worker applies its
                // own independent capacity and backpressure policy.
                if self.tunnel_pins>=self.tunnel_pin_soft{return Some(d)}
                self.tunnel_pins+=1;
            }
            Egress::RejectUnknownFakeIP=>return Some(d),
        }
        self.bound.insert(key,d);
        Some(d)
    }
    pub fn end(&mut self,key:&FlowKey){
        match self.bound.remove(key){
            Some(Egress::Direct{..})=>self.direct_pins-=1,
            Some(Egress::Tunnel)=>self.tunnel_pins-=1,
            _=>{}
        }
    }
    pub fn len(&self)->usize{self.bound.len()}
    pub fn direct_len(&self)->usize{self.direct_pins}
    pub fn tunnel_len(&self)->usize{self.tunnel_pins}
}
#[cfg(test)]
mod tests {
    use super::*;
    fn ip(a:u8,b:u8,c:u8,d:u8)->u32{u32::from_be_bytes([a,b,c,d])}
    fn cidr(n:u32,bits:u8)->Ipv4Cidr{Ipv4Cidr{network:n,bits}}
    fn ranges(a:&[Ipv4Cidr])->Ranges{Ranges::compile(a).unwrap()}
    fn make(mode:Mode)->SplitPolicy{
        SplitPolicy::new(mode,
            ranges(&[cidr(ip(192,168,0,0),16),cidr(ip(10,0,0,0),8)]),
            ranges(&[cidr(ip(203,0,113,0),24)]),
            ranges(&[cidr(ip(172,16,0,0),12)]),
            ranges(&[cidr(ip(198,18,0,0),16)]))
    }
    #[test]
    fn plan029_split_cidr_merge_and_binary_search_not_os_route_explosion(){
        let r=ranges(&[
            cidr(ip(10,0,0,0),24),cidr(ip(10,0,1,0),24),
            cidr(ip(10,0,0,0),25),cidr(ip(0,0,0,0),32)
        ]);
        assert_eq!(r.interval_count(),2);
        assert!(r.contains(ip(10,0,1,250)));
        assert!(!r.contains(ip(10,0,2,1)));
        assert!(!r.contains(ip(0,0,0,1)));
        assert_eq!(Ranges::compile(&[cidr(0,33)]),Err(SplitError::InvalidCidr));
    }
    #[test]
    fn plan029_fake_advanced_pool_interval_covers_every_owned_address(){
        let range=Ranges::interval(
            u32::from_be_bytes([198,18,1,9]),
            u32::from_be_bytes([198,18,1,44])).unwrap();
        assert!(!range.contains(u32::from_be_bytes([198,18,1,8])));
        assert!(range.contains(u32::from_be_bytes([198,18,1,30])));
        assert!(!range.contains(u32::from_be_bytes([198,18,1,45])));
        assert_eq!(Ranges::interval(10,9),Err(SplitError::InvalidCidr));
    }
    #[test]
    fn plan029_split_three_modes_and_internal_dns_direction_wins_over_ip(){
        let cn=ip(203,0,113,8);let lan=ip(10,5,5,5);
        let overseas=ip(198,51,100,9);
        let all=make(Mode::All);
        assert_eq!(all.destination(cn),Egress::Tunnel);
        assert_eq!(all.destination(lan),Egress::Tunnel);
        let only_lan=make(Mode::BypassLan);
        assert_eq!(only_lan.destination(cn),Egress::Tunnel);
        assert_eq!(only_lan.destination(lan),Egress::Direct{real_dst:lan,presented_dst:lan});
        let split=make(Mode::BypassLanCn);
        assert_eq!(split.destination(cn),Egress::Direct{real_dst:cn,presented_dst:cn});
        assert_eq!(split.destination(overseas),Egress::Tunnel);
        assert_eq!(split.dns_egress(DnsUse::InternalTunnel),DnsEgress::Tunnel);
        assert_eq!(split.dns_egress(DnsUse::InternalDirect),DnsEgress::Direct);
        assert_eq!(all.dns_egress(DnsUse::ServerBootstrap),DnsEgress::Direct);
        assert_eq!(split.dns_egress(DnsUse::Ordinary{china_domain:true}),DnsEgress::Direct);
        assert_eq!(only_lan.dns_egress(DnsUse::Ordinary{china_domain:true}),DnsEgress::Tunnel);
    }
    #[test]
    fn plan029_split_selective_fake_cdn_isolation_and_unknown_fake_drop(){
        let real_cdn=ip(198,51,100,77);
        let fake=ip(198,18,2,5);
        let mut split=make(Mode::BypassLanCn);
        assert_eq!(split.destination(real_cdn),Egress::Tunnel);
        assert_eq!(split.destination(fake),Egress::RejectUnknownFakeIP);
        split.remember_announced_fake(fake,real_cdn).unwrap();
        assert_eq!(split.destination(fake),Egress::Direct{real_dst:real_cdn,presented_dst:fake});
        assert_eq!(split.destination(real_cdn),Egress::Tunnel); // shared CDN non-CN unaffected
        assert_eq!(split.remember_announced_fake(fake,ip(203,0,113,12)),Err(SplitError::FakeIPConflict));
        assert_eq!(split.remember_announced_fake(real_cdn,real_cdn),Err(SplitError::FakeIPConflict));
    }
    #[test]
    fn plan029_h1959_fake_restored_zero_broadcast_cannot_be_direct(){
        let fake=ip(198,18,12,27);
        let valid=ip(198,51,100,77);
        let mut policy=make(Mode::BypassLanCn);
        for bad in [0,u32::MAX,ip(198,18,20,1)]{
            assert_eq!(policy.announced_fake_target(fake,bad),None);
            assert_eq!(policy.remember_announced_fake(fake,bad),
                Err(SplitError::FakeIPConflict));
            assert_eq!(policy.destination(fake),Egress::RejectUnknownFakeIP);
        }
        // A corrupt historical target cannot poison a valid new binding.
        assert_eq!(policy.remember_announced_fake(fake,valid),Ok(()));
        assert_eq!(policy.destination(fake),Egress::Direct{
            real_dst:valid,presented_dst:fake});
        for bad in [0,u32::MAX,ip(198,18,20,1)]{
            assert_eq!(policy.remember_announced_fake(fake,bad),
                Err(SplitError::FakeIPConflict));
            assert_eq!(policy.destination(fake),Egress::Direct{
                real_dst:valid,presented_dst:fake});
        }
    }
    #[test]
    fn plan029_split_fake_never_activates_in_other_modes(){
        for mode in [Mode::All,Mode::BypassLan]{
            let mut policy=make(mode);
            assert_eq!(policy.remember_announced_fake(ip(198,18,1,9),ip(198,51,100,77)),
                Err(SplitError::FakeIPConflict));
            assert_eq!(policy.destination(ip(198,18,1,9)),
                Egress::RejectUnknownFakeIP);
        }
    }
    #[test]
    fn plan029b_b4_fresh_generations_drop_stale_fake_even_when_all_tunnels(){
        // Simulate three independent Rust policy generations. The first
        // advanced CN table may have published a FakeIP for an overseas A.
        let fake=ip(198,18,7,9);
        let overseas=ip(198,51,100,77);
        let cn=ip(203,0,113,8);
        let mut advanced=make(Mode::BypassLanCn);
        advanced.remember_announced_fake(fake,overseas).unwrap();
        assert_eq!(advanced.destination(fake),Egress::Direct{
            real_dst:overseas,presented_dst:fake});
        assert_eq!(advanced.destination(overseas),Egress::Tunnel);
        // A reconnect always constructs a new generation: ordinary CN
        // still sends CN-domain DNS direct, but no old FakeIP lookup survives.
        let ordinary=make(Mode::BypassLanCn);
        assert_eq!(ordinary.dns_egress(DnsUse::Ordinary{china_domain:true}),
            DnsEgress::Direct);
        assert_eq!(ordinary.destination(fake),Egress::RejectUnknownFakeIP);
        assert_eq!(ordinary.destination(overseas),Egress::Tunnel);
        assert_eq!(ordinary.destination(cn),Egress::Direct{
            real_dst:cn,presented_dst:cn});
        drop(advanced);
        // Split-off/All keeps the Rust data-plane/Tunnel, but must reject
        // 198.18/16 even in its fast all-tunnel branch, never leak it.
        let all=make(Mode::All);
        assert!(all.plain_all_tunnel(overseas));
        assert!(!all.plain_all_tunnel(fake));
        assert_eq!(all.destination(fake),Egress::RejectUnknownFakeIP);
        assert_eq!(all.destination(overseas),Egress::Tunnel);
        assert_eq!(all.destination(cn),Egress::Tunnel);
    }
    #[test]
    fn plan029_split_domain_trie_exact_and_boundary_no_guess_sni(){
        let mut rules=DomainIndex::default();
        rules.insert("EXAMPLE.CN.",DomainRuleType::Suffix).unwrap();
        rules.insert("one.other",DomainRuleType::Exact).unwrap();
        assert_eq!(rules.len(),2);
        assert!(rules.contains("x.example.cn.").unwrap());
        assert!(rules.contains("Example.CN").unwrap());
        assert!(!rules.contains("evil-example.cn").unwrap());
        assert!(!rules.contains("two.other").unwrap());
        assert!(rules.contains("ONE.OTHER").unwrap());
        assert_eq!(rules.insert("a",DomainRuleType::Regex),Err(SplitError::UnsupportedDomainRule));
        assert_eq!(rules.insert("a",DomainRuleType::Keyword),Err(SplitError::UnsupportedDomainRule));
        assert_eq!(rules.contains("exa..mple.cn"),Err(SplitError::InvalidDomain));
    }
    #[test]
    fn plan029_split_flow_pinned_for_relay_until_owned_stop_not_rotation(){
        let mut cache=FlowPin::with_limits(1,1);
        let key=FlowKey{source:1,destination:2,source_port:50,destination_port:80,protocol:6};
        let other=FlowKey{source:1,destination:3,source_port:51,destination_port:80,protocol:17};
        assert_eq!(cache.first(key,Egress::Tunnel),Some(Egress::Tunnel));
        assert_eq!(cache.first(key,Egress::Direct{real_dst:2,presented_dst:2}),Some(Egress::Tunnel));
        // Only the opportunistic Tunnel pin cache is full, not the
        // product tunnel's original admission queue.
        assert_eq!(cache.first(other,Egress::Tunnel),Some(Egress::Tunnel));
        assert_eq!(cache.tunnel_len(),1);
        assert_eq!(cache.get(&other),None);
        cache.end(&key);
        assert_eq!(cache.first(other,Egress::Tunnel),Some(Egress::Tunnel));
        assert_eq!(cache.get(&other),Some(Egress::Tunnel));
    }
    #[test]
    fn plan029_direct_hard_full_never_consumes_tunnel_capacity(){
        let mut cache=FlowPin::with_limits(1,1);
        let mk=|dst,port|FlowKey{
            source:7,destination:dst,source_port:port,destination_port:443,protocol:6,
        };
        let d1=mk(2,401);let d2=mk(3,402);
        let t1=mk(4,403);let t2=mk(5,404);
        let direct=|real|Egress::Direct{real_dst:real,presented_dst:real};
        assert_eq!(cache.first(d1,direct(2)),Some(direct(2)));
        assert_eq!(cache.first(d2,direct(3)),None);
        assert_eq!(cache.direct_len(),1);
        assert_eq!(cache.first(t1,Egress::Tunnel),Some(Egress::Tunnel));
        assert_eq!(cache.first(t2,Egress::Tunnel),Some(Egress::Tunnel));
        assert_eq!(cache.direct_len(),1);
        assert_eq!(cache.tunnel_len(),1);
        assert_eq!(cache.len(),2); // bounded cache, no eager per-flow slab
        assert_eq!(cache.first(d1,Egress::Tunnel),Some(direct(2)));
        assert_eq!(cache.first(t1,direct(4)),Some(Egress::Tunnel));
        assert_eq!(cache.first(mk(99,409),Egress::RejectUnknownFakeIP),
            Some(Egress::RejectUnknownFakeIP));
        assert_eq!(cache.len(),2); // never pin an invalid fake address
        cache.end(&d1);cache.end(&d1); // repeated FIN/Stop is harmless
        assert_eq!(cache.direct_len(),0);
        assert_eq!(cache.first(d2,direct(3)),Some(direct(3)));
        cache.end(&t1);cache.end(&t2);
        assert_eq!(cache.tunnel_len(),0);
        assert_eq!(cache.direct_len(),1);
    }

    /// Five quota classes are independent. This is a bounded pure component
    /// oracle, not a claim about real Windows Wintun/WSL2 scheduling or RSS.
    /// The kernel TCP buffer class has its own Windows socket test.
    #[test]
    fn plan029_h2051_small_classified_quotas_old_direct_tunnel_advance_and_recover(){
        use crate::v4_client_dns_pending::{
            DnsPending,DnsPendingError,DnsClient,QueryKey,ResolverLane
        };
        use crate::v4_client_dns_cache::DnsAnswerCache;
        use crate::v4_client_dns_answer::{DnsAResolution,DnsAnswerStatus,ResolvedA};
        use crate::v4_client_fake_pool::{FakeAllocator,FakeError,FakeKey};
        // Direct flow hard=1 cannot steal the one Tunnel pin, and a
        // saturated Tunnel pin *cache* still forwards by generation policy.
        let mut flows=FlowPin::with_limits(1,1);
        let f=|dest,port|FlowKey{source:7,destination:dest,
            source_port:port,destination_port:443,protocol:6};
        let d=f(ip(203,0,113,8),45001);
        let overflow=f(ip(203,0,113,9),45002);
        let t=f(ip(198,51,100,8),45003);
        let second_t=f(ip(198,51,100,9),45004);
        let direct=Egress::Direct{real_dst:ip(203,0,113,8),
            presented_dst:ip(203,0,113,8)};
        assert_eq!(flows.first(d,direct),Some(direct));
        assert_eq!(flows.first(overflow,direct),None);
        assert_eq!(flows.first(t,Egress::Tunnel),Some(Egress::Tunnel));
        assert_eq!(flows.first(second_t,Egress::Tunnel),Some(Egress::Tunnel));
        assert_eq!(flows.first(d,Egress::Tunnel),Some(direct));
        // One DNS pending admission each direction. Third newcomer fails,
        // but its absence must not cancel either original key; on freeing
        // one exact waiter, a new same-lane query can continue.
        let k=|name:&str,lane| QueryKey{
            name:name.into(),qtype:1,lane,resolver4:ip(1,1,1,1),
            resolver_port:53,policy_revision:1};
        let client=|port,id|DnsClient{src4:ip(10,66,0,2),
            src_port:port,requested_dns4:ip(1,1,1,1),original_id:id};
        let mut p=DnsPending::new(2,2);
        let pd=p.begin(k("cn.example",ResolverLane::Direct),
            client(22001,1),100,1000).unwrap();
        let pt=p.begin(k("outside.example",ResolverLane::Tunnel),
            client(22002,2),100,1000).unwrap();
        assert_eq!(p.begin(k("new.cn.example",ResolverLane::Direct),
            client(22003,3),101,1000),Err(DnsPendingError::WaitersFull));
        assert_eq!(p.counts(),(2,2));
        assert_eq!(p.abort_one(pd.upstream_id).unwrap().1,
            vec![client(22001,1)]);
        assert_eq!(p.counts(),(1,1));
        assert!(p.begin(k("new.cn.example",ResolverLane::Direct),
            client(22003,3),102,1000).is_ok());
        assert_eq!(p.abort_one(pt.upstream_id).unwrap().1,
            vec![client(22002,2)]);
        assert_eq!(p.cancel_all(),vec![client(22003,3)]);
        // A distinct transaction-count quota also refuses only the new
        // key and preserves the existing Tunnel key for expiry/abort.
        let mut ticket_cap=DnsPending::new(1,3);
        let held=ticket_cap.begin(k("live.example",ResolverLane::Tunnel),
            client(23001,4),100,1000).unwrap();
        assert_eq!(ticket_cap.begin(k("new.example",ResolverLane::Direct),
            client(23002,5),101,1000),Err(DnsPendingError::TransactionFull));
        assert_eq!(ticket_cap.abort_one(held.upstream_id).unwrap().1,
            vec![client(23001,4)]);
        assert!(ticket_cap.begin(k("new.example",ResolverLane::Direct),
            client(23002,5),102,1000).is_ok());
        // DNS cache max_entries=1 is an LRU bypass/eviction, not a DNS
        // transport admission wait or cross-direction answer leak.
        let mut cache=DnsAnswerCache::new(1,4096);
        let response=|value|DnsAResolution{
            status:DnsAnswerStatus::Answered,canonical:"cdn.example".into(),
            cname_chain:vec![],candidates:vec![ResolvedA{address:value,ttl:10}]};
        let cd=k("one.cn.example",ResolverLane::Direct);
        let ct=k("outside.example",ResolverLane::Tunnel);
        assert!(cache.insert(cd.clone(),response(7),100));
        assert!(cache.insert(ct.clone(),response(8),101));
        assert_eq!(cache.get(&cd,102),None);
        assert_eq!(cache.get(&ct,102).unwrap().candidates[0].address,8);
        assert_eq!(flows.first(d,Egress::Tunnel),Some(direct));
        assert_eq!(flows.first(t,Egress::Direct{real_dst:9,presented_dst:9}),
            Some(Egress::Tunnel));
        cache.clear();
        assert!(cache.insert(cd.clone(),response(9),103));
        assert_eq!(cache.get(&cd,104).unwrap().candidates[0].address,9);
        // FakeIP hard=1 protects the existing durable pinned Direct map:
        // refuse a second CN answer rather than hijack existing identity.
        let mut fake=FakeAllocator::new(ip(198,18,1,1),ip(198,18,1,4),
            &[],1,4096).unwrap();
        let fk=|name:&str,value|FakeKey{qname:name.into(),
            canonical:"cdn.example".into(),real4:value,
            policy_rev:1,resolver_rev:1};
        let old=fake.prepare(fk("one.cn.example",ip(198,51,100,7)),0,100).unwrap();
        fake.acknowledge_durable(old.fake4).unwrap();
        assert_eq!(fake.pin_first_flow(old.fake4),Ok(ip(198,51,100,7)));
        assert_eq!(fake.prepare(fk("new.cn.example",ip(198,51,100,8)),10,101),
            Err(FakeError::PoolCapacity));
        assert_eq!(fake.announced_real(old.fake4),Some(ip(198,51,100,7)));
        assert_eq!(flows.first(d,Egress::Tunnel),Some(direct));
        assert_eq!(flows.first(t,Egress::Tunnel),Some(Egress::Tunnel));
        fake.release_flow(old.fake4,600_101).unwrap();
        assert_eq!(fake.reap_due(660_102,8),1);
        let fresh=fake.prepare(fk("new.cn.example",ip(198,51,100,8)),
            10,660_103).unwrap();
        assert_eq!(fake.announced_real(fresh.fake4),None);
        fake.acknowledge_durable(fresh.fake4).unwrap();
        assert_eq!(fake.announced_real(fresh.fake4),Some(ip(198,51,100,8)));
        // Direct cap recovery is independent of all DNS/FakeIP operations.
        flows.end(&d);
        assert!(flows.first(overflow,Egress::Direct{
            real_dst:ip(203,0,113,9),
            presented_dst:ip(203,0,113,9)}).is_some());
        assert_eq!(flows.first(t,Egress::Tunnel),Some(Egress::Tunnel));
    }
}
