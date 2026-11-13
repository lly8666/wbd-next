//! PLAN029 selected Direct branch in the ORIGINAL authenticated Rust
//! Wintun TX worker. This is NOT a separate Wintun RX or Go packet pump.
//! The versioned cold attach is probe-scoped until TCP, both DNS exits,
//! durable FakeIP publication, owned Defender/route and recovery are wired.
//! Unsupported Direct TCP / DNS cannot silently leak as Tunnel traffic.
//! Every physical socket is opened lazily and bound to source+ifindex.
use std::net::Ipv4Addr;
use std::sync::Arc;
use crate::v4_client_split::{Ipv4Cidr,Ranges,Mode,SplitPolicy,
    DomainIndex,DomainRuleType};
use crate::v4_client_split_wire::{PacketIngress,IngressAction};
use crate::v4_client_direct_udp_actor::{DirectUdpActor,NativeUdpBudget,NativeUdpFault};
use crate::v4_client_fake_pool::FakeAllocator;
use crate::v4_client_fake_journal::FakeJournal;
use crate::v4_windows_native_dns_direct::DirectDns;
use std::path::PathBuf;
use std::sync::Mutex;
use crate::v4_windows_native_dns_tunnel::TunnelDnsMap;

const MAX_PREFIXES:usize=32_768;
const MAX_DOMAIN_BYTES:usize=1<<20;
const MAX_DOMAIN_RULES:usize=20_000;
const DEFAULT_SOFT_FLOWS:usize=4_096;
const MAX_HARD_FLOWS:usize=16_384;
// Independent from live Direct flow hard cap. No eager socket or table slab.
const MAX_FAKE_IDENTITIES:usize=60_000;
const MAX_FAKE_BYTES:usize=16*1024*1024;

#[repr(C)]
#[derive(Clone,Copy)]
pub(crate) struct ColdCidrV1 {
    pub network:[u8;4],
    pub bits:u8,
    pub reserved:[u8;3],
}
#[repr(C)]
#[derive(Clone,Copy)]
pub(crate) struct ColdSplitSourceV1 {
    pub version:u32,pub size:u32,
    pub route_mode:u32,  // 0 all, 1 bypass-lan, 2 bypass-lan-cn
    pub physical_ifindex:u32,
    pub physical_source:[u8;4],pub lease4:[u8;4],
    pub direct_dns:[u8;4],pub tunnel_dns:[u8;4],
    pub fake_start:[u8;4],pub fake_end:[u8;4],
    pub inner_mtu:u32,pub direct_hard:u32,
    pub cn_count:u32,pub lan_count:u32,pub direct_count:u32,
    pub cn:*const ColdCidrV1,pub lan:*const ColdCidrV1,
    pub direct:*const ColdCidrV1,
    pub domains_length:u32,pub domains:*const u8,
    pub journal_length:u32,pub journal_path:*const u8,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) enum NativeDecision {
    Tunnel,
    TunnelDns,
    DirectHandled,
    LocalDrop,
}
pub(crate) struct NativeSplitWorker {
    ingress:PacketIngress,
    udp:DirectUdpActor,
    fakes:Option<FakeAllocator>,
    journal:Option<FakeJournal>,
    dns:DirectDns,
    tunnel_dns:Ipv4Addr,
    tunnel_map:Arc<Mutex<TunnelDnsMap>>,
    last_tick_ms:u64,
}
unsafe fn compiled_cidrs(ptr:*const ColdCidrV1,n:u32)
    ->Result<(Vec<Ipv4Cidr>,Ranges),()>{
    let n=n as usize;
    if n>MAX_PREFIXES||(n>0&&ptr.is_null()){return Err(())}
    let rows=if n==0{&[][..]}else{
        // This pointer is cold, temporary, and only read synchronously
        // while the original authenticated owner starts. No worker ever
        // retains Go or FFI memory beyond this copy.
        unsafe{std::slice::from_raw_parts(ptr,n)}
    };
    let mut cidrs=Vec::with_capacity(n);
    for row in rows{
        if row.bits>32||row.reserved!=[0;3]{return Err(())}
        cidrs.push(Ipv4Cidr{network:u32::from_be_bytes(row.network),
            bits:row.bits});
    }
    let ranges=Ranges::compile(&cidrs).map_err(|_|())?;
    Ok((cidrs,ranges))
}
impl NativeSplitWorker {
    /// SAFETY: the original owner must keep these cold pointers alive only
    /// for this synchronous call. This does not acquire any Wintun ring.
    pub(crate) unsafe fn new(c:&ColdSplitSourceV1)->Result<Self,()>{
        if c.version!=1 || c.size as usize!=
            std::mem::size_of::<ColdSplitSourceV1>() ||
           c.physical_ifindex==0 || c.direct_hard==0 ||
           c.direct_hard as usize>MAX_HARD_FLOWS ||
           !(576..=1500).contains(&c.inner_mtu) ||
           c.domains_length as usize>MAX_DOMAIN_BYTES ||
           (c.domains_length>0 && c.domains.is_null()) ||
           c.journal_length>4096 ||
           (c.journal_length>0 && c.journal_path.is_null()){
            return Err(())
        }
        let mode=match c.route_mode{
            0=>Mode::All,1=>Mode::BypassLan,2=>Mode::BypassLanCn,
            _=>return Err(())
        };
        let underlay=Ipv4Addr::from(c.physical_source);
        let lease=Ipv4Addr::from(c.lease4);
        let direct_dns=Ipv4Addr::from(c.direct_dns);
        let tunnel_dns=Ipv4Addr::from(c.tunnel_dns);
        let start=u32::from_be_bytes(c.fake_start);
        let end=u32::from_be_bytes(c.fake_end);
        if underlay.is_unspecified()||underlay.is_loopback()||
           underlay.is_multicast()||underlay.is_broadcast()||
           lease.is_unspecified()||lease.is_loopback()||
           lease==underlay||direct_dns.is_unspecified()||
           tunnel_dns.is_unspecified()||direct_dns.is_multicast()||
           tunnel_dns.is_multicast() ||
           start>=end || (start..=end).contains(&u32::from(lease)) ||
           (start..=end).contains(&u32::from(underlay)){
            return Err(())
        }
        let (cn_raw,cn)=unsafe{compiled_cidrs(c.cn,c.cn_count)}?;
        let (lan_raw,lan)=unsafe{compiled_cidrs(c.lan,c.lan_count)}?;
        let (direct_raw,direct)=unsafe{compiled_cidrs(c.direct,c.direct_count)}?;
        // Owned FakeIP addresses must be disjoint from every CIDR used to
        // force Direct; a user /0 direct4 cannot absorb synthetic identities.
        for cidr in cn_raw.iter().chain(lan_raw.iter()).chain(direct_raw.iter()){
            let mask=if cidr.bits==0{0}else{u32::MAX<<(32-cidr.bits)};
            let first=cidr.network&mask;let last=first|!mask;
            if first<=end && last>=start{return Err(())}
        }
        // The owned candidate pool may be any exact contiguous advanced
        // range. Never approximate it using just its two endpoint /32s.
        let fake_range=Ranges::interval(start,end).map_err(|_|())?;
        let mut domains=DomainIndex::default();
        if mode==Mode::BypassLanCn && c.domains_length>0{
            let raw=unsafe{std::slice::from_raw_parts(
                c.domains,c.domains_length as usize)};
            let text=std::str::from_utf8(raw).map_err(|_|())?;
            let mut rule_count=0usize;
            for line in text.split('\n').filter(|s|!s.is_empty()){
                rule_count+=1;
                if rule_count>MAX_DOMAIN_RULES{return Err(())}
                let (rule,kind)=if let Some(exact)=line.strip_prefix('='){
                    (exact,DomainRuleType::Exact)
                }else{(line,DomainRuleType::Suffix)};
                domains.insert(rule,kind).map_err(|_|())?;
            }
        }
        let policy=Arc::new(SplitPolicy::new(mode,lan,cn,direct,fake_range));
        let budget=NativeUdpBudget{hard_flows:c.direct_hard as usize,
            rx_quantum:16,ttl_ms:120_000,inner_mtu:c.inner_mtu as usize};
        let udp=DirectUdpActor::new(underlay,c.physical_ifindex,lease,
            (start,end),budget).map_err(|_|())?;
        let fakes=if mode==Mode::BypassLanCn{
            // An advanced smaller FakeIP pool is legitimate. Limit the
            // independent identity table by its exact inclusive width,
            // NOT the unrelated Direct socket/flow hard cap.
            let pool_width=u64::from(end)-u64::from(start)+1;
            let max_identities=MAX_FAKE_IDENTITIES.min(pool_width as usize);
            Some(FakeAllocator::new(start,end,
                &[(u32::from(lease),u32::from(lease)),
                  (u32::from(underlay),u32::from(underlay))],
                max_identities,MAX_FAKE_BYTES)
                .map_err(|_|())?)
        }else{None};
        let (journal,fakes)=if mode==Mode::BypassLanCn &&
            c.journal_length>0 {
            let raw=unsafe{std::slice::from_raw_parts(
                c.journal_path,c.journal_length as usize)};
            let path=std::str::from_utf8(raw).map_err(|_|())?;
            if path.contains('\0'){return Err(())}
            let (journal,recovered)=FakeJournal::open(&PathBuf::from(path))
                .map_err(|_|())?;
            let mut pool=fakes.ok_or(())?;
            let now=std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH).map_err(|_|())?
                .as_millis();
            pool.restore(&recovered,u64::try_from(now).map_err(|_|())?)
                .map_err(|_|())?;
            (Some(journal),Some(pool))
        }else{(None,fakes)};
        let dns=DirectDns::new(underlay,c.physical_ifindex,lease,
            direct_dns,c.inner_mtu as usize);
        let tunnel_map=Arc::new(Mutex::new(TunnelDnsMap::new(
            u32::from(lease),u32::from(tunnel_dns))));
        Ok(Self{ingress:PacketIngress::new(policy,Arc::new(domains),
            u32::from(lease),c.direct_hard as usize,DEFAULT_SOFT_FLOWS,1024),
            udp,fakes,journal,dns,tunnel_dns,tunnel_map,last_tick_ms:0})
    }
    pub(crate) fn tunnel_map(&self)->Arc<Mutex<TunnelDnsMap>>{
        Arc::clone(&self.tunnel_map)
    }
    /// In-place destination NAT happens on the already copied Wintun
    /// source slot BEFORE the original Rust AEAD seal. Only DNS UDP53,
    /// never ordinary Tunnel DATA, allocates one map entry.
    pub(crate) fn rewrite_tunnel_dns(&mut self,packet:&mut[u8],
        now_ms:u64)->bool{
        match self.tunnel_map.lock(){
            Ok(mut map)=>map.rewrite_query(packet,now_ms).is_ok(),
            Err(_)=>false,
        }
    }
    pub(crate) fn has_udp_flows(&self)->bool{
        self.udp.len()>0||self.dns.has_work()
    }
    pub(crate) fn on_packet(&mut self,packet:&[u8],now_ms:u64)
        ->NativeDecision{
        let fakes=&self.fakes;
        let action=self.ingress.on_ipv4_with_announced_fake(packet,now_ms,
            |ip|fakes.as_ref().and_then(|pool|pool.announced_real(ip)));
        match action{
            Ok(IngressAction::Tunnel)=>NativeDecision::Tunnel,
            Ok(IngressAction::Direct{real_dst,presented_dst})=>{
                // Only source-locked physical UDP is currently connected.
                // TCP must wait for one owned Windows kernel listener + NAT
                // and exact Defender/route resources. No Tunnel fallback.
                if packet.get(9)!=Some(&17){
                    self.ingress.rollback_unserved_direct(packet);
                    return NativeDecision::LocalDrop
                }
                let result=self.udp.send_direct_datagram(packet,
                    Ipv4Addr::from(presented_dst),
                    Ipv4Addr::from(real_dst),now_ms);
                match result{
                    Ok(())=>NativeDecision::DirectHandled,
                    Err(NativeUdpFault::Capacity|
                        NativeUdpFault::Socket(_)|
                        NativeUdpFault::InvalidOriginal|
                        NativeUdpFault::DatagramTooLarge|
                        NativeUdpFault::BadUnderlay)=>{
                        self.ingress.rollback_unserved_direct(packet);
                        NativeDecision::LocalDrop
                    },
                    // A locally congested existing socket gets only a
                    // datagram drop; never forcibly move the pinned flow.
                    Err(_)=>NativeDecision::LocalDrop,
                }
            }
            Ok(IngressAction::DnsUdp{egress,name,qtype,id,..})=>{
                match egress{
                    crate::v4_client_split::DnsEgress::Direct=>{
                        if self.dns.submit(packet,name,qtype,id,now_ms,
                            self.journal.is_some()){
                            NativeDecision::DirectHandled
                        }else{NativeDecision::LocalDrop}
                    },
                    crate::v4_client_split::DnsEgress::Tunnel=>{
                        // Caller changes only this DNS request's destination
                        // to the unique Tunnel resolver and seals it through
                        // the ORIGINAL authenticated M3/AEAD/FEC path.
                        NativeDecision::TunnelDns
                    },
                }
            },
            Ok(IngressAction::DnsTcpNeedsQuestion|
               IngressAction::DropUnknownFake)|
            Err(_)=>NativeDecision::LocalDrop,
        }
    }
    pub(crate) fn poll_udp_reverse(&mut self,out:&mut[u8],now_ms:u64)
        ->Option<usize>{
        if self.dns.has_work(){
            self.dns.poll(now_ms,self.fakes.as_mut(),self.journal.as_mut());
            if let Some(data)=self.dns.pop(){
                if data.len()<=out.len(){
                    out[..data.len()].copy_from_slice(&data);
                    return Some(data.len())
                }
            }
        }
        self.udp.poll_reverse_ready(out,now_ms).ok().flatten()
    }
    pub(crate) fn tick(&mut self,now_ms:u64){
        if now_ms.saturating_sub(self.last_tick_ms)<1_000{return}
        self.last_tick_ms=now_ms;
        self.udp.expire_some(now_ms,64);
        self.ingress.on_expiry_tick(now_ms);
        if let Ok(mut map)=self.tunnel_map.lock(){map.expire(now_ms)}
        // FakeIP journal and ref expiry require the separate DNS worker
        // before any synthesized mapping can be exposed.
    }
}

#[cfg(test)]
mod tests{
    use super::*;
    fn cidr(a:[u8;4],bits:u8)->ColdCidrV1{
        ColdCidrV1{network:a,bits,reserved:[0;3]}
    }
    fn config<'a>(cn:&'a [ColdCidrV1],lan:&'a [ColdCidrV1],
        domains:&'a [u8])->ColdSplitSourceV1{
        ColdSplitSourceV1{
            version:1,size:std::mem::size_of::<ColdSplitSourceV1>() as u32,
            route_mode:2,physical_ifindex:14,
            physical_source:[10,1,0,7],lease4:[10,234,12,34],
            direct_dns:[223,5,5,5],tunnel_dns:[1,1,1,1],
            fake_start:[198,18,0,1],fake_end:[198,18,255,254],
            inner_mtu:1280,direct_hard:16,
            cn_count:cn.len() as u32,lan_count:lan.len() as u32,
            direct_count:0,cn:cn.as_ptr(),lan:lan.as_ptr(),
            direct:std::ptr::null(),domains_length:domains.len() as u32,
            domains:domains.as_ptr(),
            journal_length:0,journal_path:std::ptr::null(),
        }
    }
    fn packet(dst:[u8;4],port:u16,body:&[u8])->Vec<u8>{
        let mut out=vec![0u8;28+body.len()];
        let len=out.len() as u16;
        out[0]=0x45;out[2..4].copy_from_slice(&len.to_be_bytes());
        out[8]=64;out[9]=17;
        out[12..16].copy_from_slice(&[10,234,12,34]);
        out[16..20].copy_from_slice(&dst);
        out[20..22].copy_from_slice(&32100u16.to_be_bytes());
        out[22..24].copy_from_slice(&port.to_be_bytes());
        out[24..26].copy_from_slice(&(8+body.len() as u16).to_be_bytes());
        out[28..].copy_from_slice(body);out
    }
    #[test]
    fn plan029_native_rust_owner_single_wintun_ingress_separates_tunnel_and_nonleaking_dns(){
        let cn=[cidr([203,0,113,0],24)];
        let lan=[cidr([192,168,0,0],16)];
        let domains=b"cn.example\n";
        let mut s=unsafe{NativeSplitWorker::new(&config(&cn,&lan,domains))}.unwrap();
        assert_eq!(s.on_packet(&packet([8,8,8,8],443,b"p"),1),
            NativeDecision::Tunnel);
        // DNS QNAME is not physically delivered to a wrong resolver or
        // silently packed as ordinary Tunnel just because its dst is 8.8.
        let mut dns=vec![0u8;12];
        dns[2..4].copy_from_slice(&0x0100u16.to_be_bytes());
        dns[4..6].copy_from_slice(&1u16.to_be_bytes());
        dns.extend_from_slice(b"\x02cn\x07example\0");
        dns.extend_from_slice(&1u16.to_be_bytes());
        dns.extend_from_slice(&1u16.to_be_bytes());
        assert_eq!(s.on_packet(&packet([8,8,8,8],53,&dns),2),
            NativeDecision::DirectHandled);
        // Without a cold durable journal: one local SERVFAIL, no physical
        // socket and no real overseas CDN A response.
        assert_eq!(s.dns.counts(),(0,0,1));
        let mut reply=[0u8;2048];
        let n=s.poll_udp_reverse(&mut reply,2).unwrap();
        assert_eq!(reply[20..22],[0,53]);
        assert_eq!(reply[31]&0xf,2); // DNS RCODE at IPv4(20)+UDP(8)+flags byte1(3)
        assert!(n>=40);
        assert!(!s.has_udp_flows());
        s.tick(1001);
    }
    #[test]
    fn plan029_native_fakeip_quota_not_tied_to_direct_flow_quota(){
        use crate::v4_client_fake_pool::FakeKey;
        let mut c=config(&[],&[],b"cn.example\n");
        c.direct_hard=1;
        let mut native=unsafe{NativeSplitWorker::new(&c)}.unwrap();
        let fake=native.fakes.as_mut().unwrap();
        for n in 0..17u32{
            let slot=fake.prepare(FakeKey{
                qname:format!("cn{n}.example"),
                canonical:"edge.example".into(),
                real4:0xcb007109,policy_rev:1,resolver_rev:1,
            },30,1000).unwrap();
            // A reservation is NEVER a client-published FakeIP before
            // the separate real durable DNS journal acknowledges it.
            assert_eq!(fake.announced_real(slot.fake4),None);
        }
        assert_eq!(fake.counts().0,17);
        assert_eq!(native.udp.max_flows(),1);
    }
    #[test]
    fn plan029_native_same_dns_ip_is_two_explicit_directions_not_a_rejection(){
        let mut c=config(&[],&[],b"");
        c.tunnel_dns=c.direct_dns;
        let owner=unsafe{NativeSplitWorker::new(&c)}.unwrap();
        assert!(!owner.has_udp_flows());
        c.route_mode=0; // 'all': no domain tracking or FakeIP allocator.
        let all=unsafe{NativeSplitWorker::new(&c)}.unwrap();
        assert!(all.fakes.is_none());
    }
    #[test]
    fn plan029_native_cold_policy_rejects_fake_range_overlap_or_wrong_dns(){
        let bad=[cidr([0,0,0,0],0)];
        let c=config(&bad,&[],b"cn.example");
        assert!(unsafe{NativeSplitWorker::new(&c)}.is_err());
        let mut c=config(&[],&[],b"cn.example");
        c.fake_start=[198,18,1,4];
        c.fake_end=[198,18,1,44];
        let mut small=unsafe{NativeSplitWorker::new(&c)}.unwrap();
        // Exactly 41 addresses; the independent 60k upper ceiling must
        // not reject this valid advanced pool or steal a live mapping.
        use crate::v4_client_fake_pool::{FakeKey,FakeError};
        let fakes=small.fakes.as_mut().unwrap();
        for n in 0..41u32{
            fakes.prepare(FakeKey{
                qname:format!("pool{n}.example"),
                canonical:"edge.example".into(),
                real4:0xcb007109,policy_rev:1,resolver_rev:1,
            },30,1_000).unwrap();
        }
        assert_eq!(fakes.counts().0,41);
        assert_eq!(fakes.prepare(FakeKey{
            qname:"beyond.example".into(),canonical:"edge.example".into(),
            real4:0xcb007109,policy_rev:1,resolver_rev:1,
        },30,1_000),Err(FakeError::PoolCapacity));
        let mut c=config(&[],&[],b"cn.example");
        c.direct_hard=16_385;
        assert!(unsafe{NativeSplitWorker::new(&c)}.is_err());
    }
}
