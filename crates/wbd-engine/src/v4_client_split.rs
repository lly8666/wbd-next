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
    pub fn dns_egress(&self,purpose:DnsUse)->DnsEgress{
        match purpose {
            DnsUse::ServerBootstrap|DnsUse::InternalDirect=>DnsEgress::Direct,
            DnsUse::InternalTunnel=>DnsEgress::Tunnel,
            DnsUse::Ordinary{china_domain:true} if self.mode==Mode::BypassLanCn=>DnsEgress::Direct,
            DnsUse::Ordinary{..}=>DnsEgress::Tunnel,
        }
    }
    pub fn remember_announced_fake(&mut self,fake:u32,real:u32)->Result<(),SplitError>{
        if !self.fake_pool.contains(fake)||self.fake_pool.contains(real) {
            return Err(SplitError::FakeIPConflict);
        }
        if let Some(old)=self.fake_to_real.get(&fake) {
            if *old!=real{return Err(SplitError::FakeIPConflict)}
            return Ok(());
        }
        self.fake_to_real.insert(fake,real);
        Ok(())
    }
    #[inline]
    pub fn destination(&self,ip:u32)->Egress{
        if self.fake_pool.contains(ip){
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
pub(crate) struct FlowPin {
    bound:HashMap<FlowKey,Egress>,
    max:usize,
}
impl FlowPin{
    pub fn new(max:usize)->Self{Self{bound:HashMap::new(),max}}
    pub fn get(&self,k:&FlowKey)->Option<Egress>{self.bound.get(k).copied()}
    pub fn first(&mut self,key:FlowKey,d:Egress)->Option<Egress>{
        if let Some(old)=self.bound.get(&key){return Some(*old)}
        if self.bound.len()>=self.max{return None}
        self.bound.insert(key,d);Some(d)
    }
    pub fn end(&mut self,key:&FlowKey){self.bound.remove(key);}
    pub fn len(&self)->usize{self.bound.len()}
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
        let mut cache=FlowPin::new(1);
        let key=FlowKey{source:1,destination:2,source_port:50,destination_port:80,protocol:6};
        let other=FlowKey{source:1,destination:3,source_port:51,destination_port:80,protocol:17};
        assert_eq!(cache.first(key,Egress::Tunnel),Some(Egress::Tunnel));
        assert_eq!(cache.first(key,Egress::Direct{real_dst:2,presented_dst:2}),Some(Egress::Tunnel));
        assert_eq!(cache.first(other,Egress::Tunnel),None);
        cache.end(&key);
        assert_eq!(cache.first(other,Egress::Tunnel),Some(Egress::Tunnel));
    }
}
