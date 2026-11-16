//! Android Root split policy, deliberately NOT Windows selective FakeIP.
//! DNS direction is chosen by QNAME, but the *actual resolved IP* controls
//! split-mode data egress. No real-IP->domain reverse cache/CDN pollution.
//! This is a cold policy + kernel-route rehearsal, NOT the production WBD
//! Android owner or an authorization to mutate Android netd/main namespace.
use serde_json::{json,Value};
use std::collections::{BTreeMap,HashMap};
use std::net::Ipv4Addr;
use std::str::FromStr;

#[derive(Clone,Copy,Debug,PartialEq,Eq)]
enum Mode { Split, Global }
impl Mode {
    fn parse(s:&str)->Result<Self,String>{
        match s { "split"=>Ok(Self::Split),"global"=>Ok(Self::Global),
            _=>Err(format!("invalid mode={s}, must be split/global")) }
    }
    fn name(self)->&'static str{match self{Self::Split=>"split",Self::Global=>"global"}}
}
#[derive(Debug,Clone)]
struct Ranges(Vec<(u32,u32)>);
impl Ranges {
    fn compile(data:&[String])->Result<Self,String>{
        if data.len()>32768{return Err("too many cidrs (32768 hard limit)".into())}
        let mut out=Vec::with_capacity(data.len());
        for v in data{
            let (addr,nbits)=v.split_once('/').ok_or_else(||format!("CIDR lacks /: {v}"))?;
            let ip=u32::from(Ipv4Addr::from_str(addr).map_err(|_|format!("invalid IPv4 in {v}"))?);
            let bits=nbits.parse::<u8>().map_err(|_|format!("invalid CIDR bits in {v}"))?;
            if bits>32{return Err(format!("CIDR bits >32 in {v}"))}
            let mask=if bits==0{0}else{u32::MAX<<(32-bits)};
            out.push((ip&mask,(ip&mask)|!mask));
        }
        out.sort_unstable();
        let mut merged:Vec<(u32,u32)>=Vec::with_capacity(out.len());
        for (start,end) in out{
            if let Some(last)=merged.last_mut(){
                if start<=last.1.saturating_add(1){
                    last.1=last.1.max(end);continue;
                }
            }
            merged.push((start,end));
        }
        Ok(Self(merged))
    }
    #[inline]fn has(&self,ip:u32)->bool{
        let pos=self.0.partition_point(|(start,_)|*start<=ip);
        pos>0&&ip<=self.0[pos-1].1
    }
    fn len(&self)->usize{self.0.len()}
}
/// Cold-compiled exact/suffix hash index. Query cost is bounded by number of
/// labels, never by CN list length. Only consulted at DNS admission, not DATA.
#[derive(Clone,Debug,Default)]
struct Domains{suffixes:std::collections::HashSet<String>,exact:std::collections::HashSet<String>}
fn labels(name:&str)->Result<Vec<String>,String>{
    let name=name.strip_suffix('.').unwrap_or(name);
    if name.is_empty()||name.len()>253||!name.is_ascii(){
        return Err(format!("invalid ASCII/IDNA domain: {name}"))
    }
    let x=name.split('.').map(|s|s.to_ascii_lowercase()).collect::<Vec<_>>();
    if x.iter().any(|s|s.is_empty()||s.len()>63||s.starts_with('-')||
       s.ends_with('-')||!s.bytes().all(|c|c.is_ascii_alphanumeric()||c==b'-')){
        return Err(format!("invalid DNS label: {name}"))
    }
    Ok(x)
}
impl Domains {
    fn compile(inputs:&[String])->Result<Self,String>{
        if inputs.len()>20000{return Err("too many CN domain rules".into())}
        let mut d=Self::default();
        // A baseline, NOT a substitute for Windows full geolocation-cn data.
        d.suffixes.insert("cn".into());
        for text in inputs {
            let (exact,raw)=if let Some(n)=text.strip_prefix('='){(true,n)}else{(false,text.as_str())};
            if raw.starts_with("keyword:")||raw.starts_with("regex:"){
                return Err("unsupported keyword/regex; never silently downgrade".into())
            }
            let normalized=labels(raw)?.join(".");
            if exact{d.exact.insert(normalized);}else{d.suffixes.insert(normalized);}
        }
        Ok(d)
    }
    fn has(&self,domain:&str)->Result<bool,String>{
        let ls=labels(domain)?;
        let full=ls.join(".");
        if self.exact.contains(&full){return Ok(true)}
        // Try labels only: example.cn matches sub.example.cn but not xexample.cn.
        for i in 0..ls.len(){
            if self.suffixes.contains(&ls[i..].join(".")){return Ok(true)}
        }
        Ok(false)
    }
    fn len(&self)->usize{self.suffixes.len()+self.exact.len()}
}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
enum Egress { Direct,Tunnel }
impl Egress {fn name(self)->&'static str{match self{Self::Direct=>"direct",Self::Tunnel=>"tunnel"}}}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
enum DnsUse { Bootstrap,OwnedDirect,OwnedTunnel,Ordinary }
#[derive(Debug)]
struct Policy {
    base:Mode,
    overrides:BTreeMap<u32,Mode>,
    cn:Ranges,
    lan:Ranges,
    explicit:Ranges,
    domains:Domains,
    geosite:Option<crate::cn_geosite::Index>,
}
fn str_vec(obj:&Value,name:&str)->Result<Vec<String>,String>{
    let Some(xs)=obj.get(name).and_then(Value::as_array) else{
        return Err(format!("missing {name} array, refusing unknown CN ranges"))
    };
    if xs.len()>32768{return Err(format!("{name} exceeds limit"))}
    xs.iter().map(|x|x.as_str().map(str::to_owned).ok_or_else(||format!("{name} contains non-string"))).collect()
}
impl Policy {
    fn compile(json:&Value)->Result<Self,String>{
        if json.get("schema").and_then(Value::as_str)!=Some("wbd-android-split/v1"){
            return Err("invalid/missing wbd-android-split/v1 config schema".into())
        }
        let base=Mode::parse(json.get("default_mode").and_then(Value::as_str).unwrap_or(""))?;
        let cn=Ranges::compile(&str_vec(json,"cn_ipv4")?)?;
        if cn.0.is_empty()&&base==Mode::Split{
            return Err("CN IPv4 dataset EMPTY: refuse calling split-mode ready".into())
        }
        let lan=Ranges::compile(&[
            "10.0.0.0/8","172.16.0.0/12","192.168.0.0/16",
            "169.254.0.0/16","127.0.0.0/8"
        ].iter().map(|s|s.to_string()).collect::<Vec<_>>())?;
        let explicit=Ranges::compile(&str_vec(json,"direct_ipv4")?)?;
        let domains=Domains::compile(&str_vec(json,"cn_domains")?)?;
        let mut overrides=BTreeMap::new();
        let apps=json.get("apps").and_then(Value::as_array).ok_or("missing apps array")?;
        if apps.len()>1024{return Err("too many per-app overrides".into())}
        for app in apps{
            let uid=app.get("uid").and_then(Value::as_u64).ok_or("app.uid must be integer")?;
            if !(10000..=9999999).contains(&uid){return Err("app UID outside permitted range".into())}
            let mode=Mode::parse(app.get("mode").and_then(Value::as_str).unwrap_or(""))?;
            if overrides.insert(uid as u32,mode).is_some(){return Err("duplicate app UID".into())}
        }
        if cn.0.is_empty() && overrides.values().any(|m|*m==Mode::Split){
            return Err("CN IPv4 dataset EMPTY: a per-app split override is not ready".into())
        }
        Ok(Self{base,overrides,cn,lan,explicit,domains,geosite:None})
    }
    fn mode(&self,uid:u32)->Mode{self.overrides.get(&uid).copied().unwrap_or(self.base)}
    /// Control socket and resolver purposes are unforgeable internal metadata,
    /// not an exemption for regular apps visiting the same resolver/server IP.
    fn dns(&self,uid:u32,qname:&str,use_kind:DnsUse)->Result<Egress,String>{
        // Purpose is an internal caller-owned enum, not a user-supplied QNAME.
        // Imported geosite rules are only consulted for an ordinary Split
        // DNS question; NEVER for data-plane real-IP routing or bootstrap.
        let cn=if use_kind==DnsUse::Ordinary && self.mode(uid)==Mode::Split{
            self.domains.has(qname)? ||
              self.geosite.as_ref().map(|g|g.has(qname)).transpose()?.unwrap_or(false)
        }else{false};
        Ok(match use_kind{
            DnsUse::Bootstrap|DnsUse::OwnedDirect=>Egress::Direct,
            DnsUse::OwnedTunnel=>Egress::Tunnel,
            DnsUse::Ordinary if cn=>Egress::Direct,
            DnsUse::Ordinary=>Egress::Tunnel
        })
    }
    /// Called once at flow admission; DNS QNAME does NOT override actual A.
    #[inline]fn data(&self,uid:u32,real:u32)->Egress{
        if self.mode(uid)==Mode::Split &&(self.lan.has(real)||self.cn.has(real)||self.explicit.has(real)){
            Egress::Direct
        }else{Egress::Tunnel}
    }
}
#[derive(Clone,Copy,PartialEq,Eq,Hash)]
struct FlowKey{uid:u32,src:u32,dst:u32,sport:u16,dport:u16,proto:u8}
struct FlowPin{pinned:HashMap<FlowKey,Egress>,limit:usize}
impl FlowPin{
 fn decide(&mut self,p:&Policy,k:FlowKey)->Result<Egress,String>{
   if let Some(d)=self.pinned.get(&k){return Ok(*d)}
   if self.pinned.len()>=self.limit{return Err("flow-pin capacity; never silently redirect".into())}
   let e=p.data(k.uid,k.dst);self.pinned.insert(k,e);Ok(e)
 }
 fn release(&mut self,k:&FlowKey){self.pinned.remove(k);}
}
fn fixture()->Value{
 json!({"schema":"wbd-android-split/v1","default_mode":"split",
    "cn_ipv4":["203.0.113.0/24","203.0.113.128/25","203.0.112.0/24"],
    "direct_ipv4":["198.51.100.240/28"],
    "cn_domains":["example.cn","=cn-trusted.test"],
    "apps":[{"uid":10501,"mode":"split"},{"uid":10502,"mode":"global"}]})
}
pub fn pure()->Value{
 let j=fixture();
 let policy=match Policy::compile(&j){
   Ok(p)=>p,Err(e)=>return json!({"status":"FAIL","reason":e})
 };
 let cn=u32::from(Ipv4Addr::new(203,0,113,7));
 let foreign=u32::from(Ipv4Addr::new(8,8,8,8));
 let shared_cdn=u32::from(Ipv4Addr::new(198,51,100,77));
 let tests=[
  ("split_cn_ip",policy.data(10501,cn)==Egress::Direct),
  ("split_foreign_ip",policy.data(10501,foreign)==Egress::Tunnel),
  ("global_cn_ip",policy.data(10502,cn)==Egress::Tunnel),
  ("global_foreign_ip",policy.data(10502,foreign)==Egress::Tunnel),
  ("default_split_cn",policy.data(11000,cn)==Egress::Direct),
  ("CN_domain_foreign_A_tunnel",policy.data(10501,shared_cdn)==Egress::Tunnel),
  ("CN_domain_dns_direct",policy.dns(10501,"foo.example.CN",DnsUse::Ordinary)==Ok(Egress::Direct)),
  ("CN_domain_in_global_uses_tunnel_dns",policy.dns(10502,"foo.example.cn",DnsUse::Ordinary)==Ok(Egress::Tunnel)),
  ("foreign_domain_dns_tunnel",policy.dns(10501,"overseas.test",DnsUse::Ordinary)==Ok(Egress::Tunnel)),
  ("server_bootstrap_dns_direct_in_global",policy.dns(10502,"wbd.example.net",DnsUse::Bootstrap)==Ok(Egress::Direct)),
  ("server_bootstrap_dns_direct_in_split",policy.dns(10501,"wbd.example.net",DnsUse::Bootstrap)==Ok(Egress::Direct)),
  ("internal_tunnel_dns_never_by_ip",policy.dns(10501,"example.cn",DnsUse::OwnedTunnel)==Ok(Egress::Tunnel)),
  ("internal_direct_dns_never_by_ip",policy.dns(10502,"external.test",DnsUse::OwnedDirect)==Ok(Egress::Direct)),
  ("suffix_boundary",policy.domains.has("evil-example.cn")==Ok(true)&&
    policy.domains.has("evil-example.com")==Ok(false)),
  ("unsupported_regex_reject",Domains::compile(&["regex:x".into()]).is_err()),
  ("unknown_empty_cn_fail_closed",Policy::compile(&json!({
      "schema":"wbd-android-split/v1","default_mode":"split","cn_ipv4":[],
      "direct_ipv4":[],"cn_domains":[],"apps":[] })).is_err()),
  ("no_fakeip",!serde_json::to_string(&j).unwrap_or_default().contains("fakeip")),
 ];
 let mut flow=FlowPin{pinned:HashMap::new(),limit:2};
 let k=FlowKey{uid:10501,src:1,dst:cn,sport:48000,dport:443,proto:6};
 let f=flow.decide(&policy,k).ok();
 let changed=json!({"schema":"wbd-android-split/v1","default_mode":"global",
    "cn_ipv4":["203.0.113.0/24"],"direct_ipv4":[],"cn_domains":[],"apps":[]});
 let other=Policy::compile(&changed).unwrap();
 let pinned=f==Some(Egress::Direct)&&flow.decide(&other,k).ok()==Some(Egress::Direct);
 flow.release(&k);
 let mut rows=tests.iter().map(|(name,ok)|json!({"check":name,"pass":ok})).collect::<Vec<_>>();
 rows.push(json!({"check":"active_flow_pinned_across_mode_change","pass":pinned}));
 let passed=rows.iter().all(|x|x["pass"]==true);
 json!({"status":if passed{"SUPPORTED_IN_SCOPE"}else{"FAIL"},"checks":rows,
     "check_count":rows.len(),"merged_cn_ranges":policy.cn.len(),
     "domain_rules":policy.domains.len(),
     "per_uid_override_count":policy.overrides.len(),
     "fakeip_enabled":false,
     "status_scope":"offline policy only, synthetic RFC5737 CIDRs, not actual CN coverage or Android netd",
     "production_WBD_routing":"NOT_RUN"})
}
#[cfg(test)]mod tests{
 use super::*;
 #[test]fn pure_policy_fixture_all_pass(){let x=pure();assert_eq!(x["status"],"SUPPORTED_IN_SCOPE","{x}");}
 #[test]fn boundary_and_dedup(){
  let r=Ranges::compile(&["203.0.113.0/24".into(),"203.0.113.128/25".into()]).unwrap();
  assert_eq!(r.len(),1);assert!(r.has(u32::from(Ipv4Addr::new(203,0,113,255))));
  assert!(!r.has(u32::from(Ipv4Addr::new(203,0,114,0))));
  assert!(Ranges::compile(&["0.0.0.0/33".into()]).is_err());
 }
 #[test]fn per_app_override_and_mode(){
  let p=Policy::compile(&fixture()).unwrap();
  assert_eq!(p.mode(10502).name(),"global");
  assert_eq!(p.mode(10501).name(),"split");
  assert!(Policy::compile(&json!({"schema":"wbd-android-split/v1",
    "default_mode":"split","cn_ipv4":["1.2.3.4/32"],"direct_ipv4":[],
    "cn_domains":[],"apps":[{"uid":0,"mode":"global"}]})).is_err());
 }
}


/// Validates a user-selected Android App policy file. Does not install routes,
/// alter netd, resolve domains, emit DNS packets, or start a VPN. The owner
/// must re-check package->UID bindings after package/user changes.
pub fn validate_file(path:&str)->Value{
 use std::fs;
 if path.len()>600 || !path.ends_with("/wbd-split-settings.json") ||
    !(path.starts_with("/data/user/")||path.starts_with("/data/data/")){
     return json!({"status":"FAIL","reason":"unexpected config path; must be an app-private wbd-split-settings.json","installed":false});
 }
 let metadata=match fs::metadata(path){
  Ok(m)=>m,Err(e)=>return json!({"status":"UNAVAILABLE","reason":e.to_string(),
      "errno":e.raw_os_error(),"installed":false})
 };
 if metadata.len()>2*1024*1024{
    return json!({"status":"FAIL","reason":"config exceeds 2MiB","installed":false})
 }
 let text=match fs::read_to_string(path){
  Ok(s)=>s,Err(e)=>return json!({"status":"UNAVAILABLE","reason":e.to_string(),
    "errno":e.raw_os_error(),"installed":false})
 };
 let config:Value=match serde_json::from_str(&text){
  Ok(x)=>x,Err(e)=>return json!({"status":"FAIL","reason":format!("malformed JSON: {e}"),"installed":false})
 };
 let mut policy=match Policy::compile(&config){
  Ok(p)=>p,Err(e)=>return json!({"status":"FAIL","reason":e,"installed":false})
 };
 let direct_dns=config.get("direct_dns").and_then(Value::as_str).unwrap_or("");
 let tunnel_dns=config.get("tunnel_dns").and_then(Value::as_str).unwrap_or("");
 for (kind,txt) in [("direct_dns",direct_dns),("tunnel_dns",tunnel_dns)]{
   if txt.parse::<Ipv4Addr>().is_err(){
    return json!({"status":"FAIL","reason":format!("{kind} must be ONE IPv4 resolver, no fallback"),
      "installed":false})
   }
 }
 let sha=config.get("geosite_sha256").and_then(Value::as_str).unwrap_or("");
 let filename=std::path::Path::new(path).with_file_name("wbd-cn-geosite.txt");
 let geosite=match crate::cn_geosite::Index::load(&filename,sha){
     Ok(v)=>v,Err(e)=>return json!({"status":"FAIL",
       "reason":format!("CN full geosite snapshot: {e}"),"installed":false})
 };
 let geosite_evidence=geosite.evidence();
 // Representative .com mainland domains must classify as CN DNS queries.
 // No hostname->IP routing inference: overseas real A still goes TUN.
 let sanity=["baidu.com","www.baidu.com","qq.com","www.qq.com"];
 for domain in sanity{
    if geosite.has(domain)!=Ok(true){
        return json!({"status":"FAIL","reason":format!("CN geosite missing {domain}"),
           "geosite":geosite_evidence,"installed":false})
    }
 }
 let foreign_real=u32::from(Ipv4Addr::new(8,8,8,8));
 let splitter=policy.overrides.iter().find(|(_,m)|**m==Mode::Split)
     .map(|(uid,_)|*uid).unwrap_or(0);
 let split_mode_exists=policy.mode(splitter)==Mode::Split;
 policy.geosite=Some(geosite);
 if split_mode_exists{
    if policy.dns(splitter,"www.baidu.com",DnsUse::Ordinary)!=Ok(Egress::Direct) ||
       policy.data(splitter,foreign_real)!=Egress::Tunnel{
        return json!({"status":"FAIL","reason":"CN .com DNS direct / overseas A data-tunnel fixture mismatch",
           "geosite":geosite_evidence,"installed":false})
    }
 }
 let wbd_bootstrap=policy.dns(0,"wbd.example.net",DnsUse::Bootstrap)==Ok(Egress::Direct);
 if !wbd_bootstrap{
  return json!({"status":"FAIL","reason":"bootstrap must always be direct","installed":false})
 }
 let rows=policy.overrides.iter().map(|(&uid,mode)|json!({"uid":uid,"mode":mode.name()}))
     .collect::<Vec<_>>();
 json!({"status":"SUPPORTED_IN_SCOPE","schema":"wbd-android-split-validation/v1",
   "default_mode":policy.base.name(),"per_app_modes":rows,
   "compiled_cn_ipv4_intervals":policy.cn.len(),
   "compiled_lan_ipv4_intervals":policy.lan.len(),
   "compiled_direct_ipv4_intervals":policy.explicit.len(),
   "domain_rules_including_cn_suffix":policy.domains.len(),
   "dns_direct":direct_dns,"dns_tunnel":tunnel_dns,
   "server_bootstrap_dns":"DIRECT_IN_ALL_MODES",
   "cn_domain_overseas_result":"TUNNEL_BY_ACTUAL_IP",
   "fakeip":false,"installed":false,
   "geosite":geosite_evidence,
   "geosite_cn_com_direct_dns_verified":split_mode_exists,
   "reason":"Policy parsed/validated only. No real Android netd routing, DNS dispatcher or production WBD tunnel activated."})
}
