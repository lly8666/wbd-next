//! PLAN029 selected Direct branch in the ORIGINAL authenticated Rust
//! Wintun TX worker. This is NOT a separate Wintun RX or Go packet pump.
//! The versioned cold attach is probe-scoped until TCP, both DNS exits,
//! durable FakeIP publication, owned Defender/route and recovery are wired.
//! Unsupported Direct TCP / DNS cannot silently leak as Tunnel traffic.
//! Every physical socket is opened lazily and bound to source+ifindex.
use std::net::Ipv4Addr;
use std::collections::HashMap;
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
use crate::v4_windows_native_tcp_direct::{NativeTcpActor,safe_synthetic};
use crate::v4_client_split::FlowKey;

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
    pub tcp_synthetic4:[u8;4],pub tcp_owned:u32,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) enum NativeDecision {
    Tunnel,
    TunnelDns,
    DirectHandled,
    LocalDrop,
}
#[derive(Clone,Copy)]
struct PendingKernelTcp {
    lease:Ipv4Addr,synthetic:Ipv4Addr,
    physical:Ipv4Addr,ifindex:u32,hard:usize,
    fake_range:(u32,u32),
}
pub(crate) struct NativeSplitWorker {
    ingress:PacketIngress,
    udp:DirectUdpActor,
    fakes:Option<FakeAllocator>,
    // Exactly one generation-owned FakeIP reference per active actual
    // Direct 5tuple (TCP/UDP), independently of DNS TTL and DNS cache.
    fake_refs:HashMap<FlowKey,u32>,
    journal:Option<FakeJournal>,
    dns:DirectDns,
    tunnel_dns:Ipv4Addr,
    tunnel_map:Arc<Mutex<TunnelDnsMap>>,
    tcp:Option<NativeTcpActor>,
    tcp_plan:Option<PendingKernelTcp>,
    tcp_enabled:bool,
    next_reverse_lane:usize,
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
           c.tcp_owned!=0 || c.journal_length>4096 ||
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
        // Never bind the kernel TCP listener while the original Go owner
        // has not yet executed the four-stage no-WFP OS Apply. A live
        // private V3 session may be constructed before lease/route exist.
        // A later authenticated FFI command must PREPARE this plan on
        // the same Rust TX thread, return the REAL kernel-chosen port,
        // and then wait for exact owned Defender receipt before ENABLE.
        let tcp_plan=if c.tcp_synthetic4==[0;4]{None}else{
            let synthetic=Ipv4Addr::from(c.tcp_synthetic4);
            if c.tcp_synthetic4[0..2]!=[198,19]||
               !safe_synthetic(u32::from(lease),u32::from(underlay),
                   u32::from(synthetic),(start,end)){
                return Err(())
            }
            Some(PendingKernelTcp{lease,synthetic,physical:underlay,
                ifindex:c.physical_ifindex,hard:c.direct_hard as usize,
                fake_range:(start,end)})
        };
        Ok(Self{ingress:PacketIngress::new(policy,Arc::new(domains),
            u32::from(lease),c.direct_hard as usize,DEFAULT_SOFT_FLOWS,1024),
            udp,fakes,fake_refs:HashMap::new(),journal,dns,tunnel_dns,tunnel_map,
            tcp:None,tcp_plan,tcp_enabled:false,
            next_reverse_lane:0,last_tick_ms:0})
    }
    pub(crate) fn has_deferred_tcp(&self)->bool{self.tcp_plan.is_some()}
    /// Only the already-authenticated original Rust TX worker may call
    /// this after Go's actual four-stage OS Apply, with the leased /32
    /// demonstrably assigned. No real driver/ring/Go callbacks inside.
    pub(crate) fn prepare_tcp_after_apply(&mut self)->Result<u16,()>{
        if self.tcp_enabled||self.tcp.is_some(){return Err(())}
        let plan=self.tcp_plan.ok_or(())?;
        let actor=NativeTcpActor::new(plan.lease,plan.synthetic,
            plan.physical,plan.ifindex,plan.hard,plan.fake_range)?;
        let port=actor.listener_port()?;
        if port==0{return Err(())}
        self.tcp=Some(actor);
        Ok(port)
    }
    /// The same Go generation must install and read back an exact
    /// source-synthetic/32 -> local-lease/32, TCP local-port Defender
    /// Allow before invoking this cold authenticated arm command.
    /// An API call alone is not a firewall receipt or public Ready.
    pub(crate) fn enable_tcp_after_defender(&mut self,port:u16)
        ->Result<(),()>{
        if self.tcp_enabled||port==0{return Err(())}
        let actor=self.tcp.as_ref().ok_or(())?;
        if actor.listener_port()?!=port{return Err(())}
        self.tcp_enabled=true;
        Ok(())
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
        self.udp.len()>0||self.dns.has_work()||
            self.tcp.as_ref().is_some_and(|t|t.has_work())
    }
    // A finished kernel Direct TCP relay leaves only an exact NAT reverse
    // tuple until ACK/retransmit close grace expires. One existing owner
    // timer wake at the oldest deadline reclaims it, not 10ms WSAPoll.
    pub(crate) fn next_tcp_cleanup_due_ms(&self)->Option<u64>{
        self.tcp.as_ref().and_then(|t|t.next_close_due_ms())
    }
    /// Obtain one identity for the first announced FakeIP BUSINESS flow.
    /// The ordinary real-IP/Tunnel hot path has no FakeIP hash lookup.
    /// This happens only after PacketIngress made the first policy pin.
    fn hold_fake_first_flow(&mut self,packet:&[u8],presented:u32,
        real:u32)->Result<Option<FlowKey>,()>{
        if presented==real{return Ok(None)}
        let key=Self::flow_key(packet).ok_or(())?;
        if let Some(&existing)=self.fake_refs.get(&key){
            return if existing==presented{Ok(None)}else{Err(())}
        }
        let pool=self.fakes.as_mut().ok_or(())?;
        if pool.announced_real(presented)!=Some(real){return Err(())}
        let pinned=pool.pin_first_flow(presented).map_err(|_|())?;
        if pinned!=real{
            let _=pool.release_flow(presented,0);
            return Err(())
        }
        self.fake_refs.insert(key,presented);
        Ok(Some(key))
    }
    fn flow_key(packet:&[u8])->Option<FlowKey>{
        if packet.len()<28||packet[0]>>4!=4{return None}
        let ihl=usize::from(packet[0]&15)*4;
        if ihl<20||ihl+4>packet.len(){return None}
        let protocol=packet[9];
        if protocol!=6&&protocol!=17{return None}
        Some(FlowKey{
            source:u32::from_be_bytes(packet[12..16].try_into().ok()?),
            destination:u32::from_be_bytes(packet[16..20].try_into().ok()?),
            source_port:u16::from_be_bytes(packet[ihl..ihl+2].try_into().ok()?),
            destination_port:u16::from_be_bytes(packet[ihl+2..ihl+4].try_into().ok()?),
            protocol,
        })
    }
    fn retire_flow(&mut self,key:FlowKey){
        if let Some(fake)=self.fake_refs.remove(&key){
            if let Some(pool)=self.fakes.as_mut(){
                let _=pool.release_flow(fake,0);
            }
        }
        self.ingress.end_flow(&key);
    }
    pub(crate) fn on_packet(&mut self,packet:&[u8],now_ms:u64)
        ->NativeDecision{
        // Kernel SYN-ACK/ACK/FIN from the ONE owned synthetic /32 are
        // exclusively inverse-translated. Never forward them through
        // ordinary Tunnel or recursively to the physical Direct leg.
        if let Some(tcp)=self.tcp.as_mut(){
            if let Some(result)=tcp.kernel_return(packet){
                return if self.tcp_enabled&&result.is_ok(){
                    NativeDecision::DirectHandled
                }else{NativeDecision::LocalDrop}
            }
        }
        // A synthetic peer /32 belongs solely to this TCP owner, even
        // while its Defender grant is NOT yet active. Its unassociated
        // kernel TCP reply MUST NOT be mistakenly classified as Tunnel.
        if let Some(plan)=self.tcp_plan{
            if packet.len()>=20&&packet[0]>>4==4&&packet[9]==6&&
               packet[12..16]==plan.lease.octets()&&
               packet[16..20]==plan.synthetic.octets(){
                return NativeDecision::LocalDrop
            }
        }
        let fakes=&self.fakes;
        let action=self.ingress.on_ipv4_with_announced_fake(packet,now_ms,
            |ip|fakes.as_ref().and_then(|pool|pool.announced_real(ip)));
        match action{
            Ok(IngressAction::Tunnel)=>NativeDecision::Tunnel,
            Ok(IngressAction::Direct{real_dst,presented_dst})=>{
                // The DNS journal must have acknowledged this exact
                // FakeIP->real candidate. Pin it independently of DNS TTL
                // before attempting either physical TCP or UDP backend.
                let newly_held=match self.hold_fake_first_flow(
                    packet,presented_dst,real_dst){
                    Ok(key)=>key,
                    Err(())=>{
                        self.ingress.rollback_unserved_direct(packet);
                        return NativeDecision::LocalDrop
                    }
                };
                // TCP uses native Windows kernel's OWN retransmission,
                // handshake and FIN. The selected actor exists only
                // AFTER the original Go owner has an exact current
                // generation synthetic route plus Defender Allow receipt.
                if packet.get(9)==Some(&6){
                    let ok=self.tcp_enabled&&self.tcp.as_mut()
                        .is_some_and(|tcp|tcp.direct(packet,real_dst,now_ms).is_ok());
                    if !ok{
                        if let Some(key)=newly_held{self.retire_flow(key);}
                        else if presented_dst==real_dst{
                            self.ingress.rollback_unserved_direct(packet);
                        }
                        // An existing fake-backed NAT flow retains its
                        // original identity until the actual kernel relay
                        // retires; backend pressure never rebases its exit.
                    }
                    return if ok{NativeDecision::DirectHandled}
                        else{NativeDecision::LocalDrop}
                }
                if packet.get(9)!=Some(&17){
                    if let Some(key)=newly_held{self.retire_flow(key);}
                    else if presented_dst==real_dst{
                        self.ingress.rollback_unserved_direct(packet);
                    }
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
                        if let Some(key)=newly_held{self.retire_flow(key);}
                        else if presented_dst==real_dst{
                            self.ingress.rollback_unserved_direct(packet);
                        }
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
        // Fair 3-queue rotation prevents a busy TCP handshake burst from
        // indefinitely starving physical UDP business or DNS replies.
        for step in 0..3{
            let lane=(self.next_reverse_lane+step)%3;
            let ready=match lane{
                0=>self.tcp.as_mut().and_then(|tcp|tcp.ready_pop())
                    .and_then(|l3|if l3.len()<=out.len(){
                        out[..l3.len()].copy_from_slice(&l3);Some(l3.len())
                    }else{None}),
                1=>{
                    if !self.dns.has_work(){None}else{
                        self.dns.poll(now_ms,self.fakes.as_mut(),self.journal.as_mut());
                        self.dns.pop().and_then(|l3|if l3.len()<=out.len(){
                            out[..l3.len()].copy_from_slice(&l3);Some(l3.len())
                        }else{None})
                    }
                },
                _=>self.udp.poll_reverse_ready(out,now_ms).ok().flatten(),
            };
            if ready.is_some(){
                self.next_reverse_lane=(lane+1)%3;
                return ready
            }
        }
        None
    }
    pub(crate) fn tick(&mut self,now_ms:u64){
        // The original Rust TX bounded scheduler already owns this call.
        // Service max 8 kernel accepts/active native TCP relays each turn,
        // while cold-only expiry remains on the existing 1-second sweep.
        if self.tcp_enabled{
         if let Some(tcp)=self.tcp.as_mut(){
            for key in tcp.tick(now_ms){
                self.retire_flow(FlowKey{
                    source:key.client,destination:key.presented,
                    source_port:key.source_port,destination_port:key.target_port,
                    protocol:6,
                });
            }
         }
        }
        // Per-owner retirement backlog is drained each bounded TX turn,
        // rather than accumulating 1s of high-rate short-lived UDP flows.
        // No Vec allocation on the ordinary Tunnel DATA path.
        for _ in 0..64{
            let Some(tuple)=self.udp.pop_retired()else{break};
            self.retire_flow(FlowKey{
                source:u32::from(tuple.client_ip),
                destination:u32::from(tuple.presented_ip),
                source_port:tuple.client_port,
                destination_port:tuple.target_port,protocol:17,
            });
        }
        if now_ms.saturating_sub(self.last_tick_ms)<1_000{return}
        self.last_tick_ms=now_ms;
        self.udp.expire_some(now_ms,64);
        // FakeIP quarantine and address reuse use UNIX epoch ms, NOT
        // the monotonic Rust TLS health clock. Only this coarse tick
        // touches the bounded expiry wheel; never DATA or socket IO.
        if self.journal.is_some(){
            if let (Some(pool),Ok(elapsed))=(self.fakes.as_mut(),
                std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)){
                if let Ok(wall)=u64::try_from(elapsed.as_millis()){
                    pool.reap_due(wall,64);
                }
            }
        }
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
            tcp_synthetic4:[0;4],tcp_owned:0,
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
    fn plan029_native_kernel_tcp_cold_refuses_pre_apply_listener_and_unowned_synthetic_reply(){
        let mut cold=config(&[],&[],b"");
        cold.tcp_synthetic4=[198,19,87,99];
        let mut owner=unsafe{NativeSplitWorker::new(&cold)}.unwrap();
        assert!(owner.has_deferred_tcp());
        assert!(owner.tcp.is_none()); // no OS lease yet, no listener!
        assert!(!owner.tcp_enabled);
        assert_eq!(owner.enable_tcp_after_defender(45902),Err(()));
        let mut response=packet([198,19,87,99],45902,b"x");
        response[9]=6;
        assert_eq!(owner.on_packet(&response,1),NativeDecision::LocalDrop);
        // A cold caller claiming the port was already owned is rejected,
        // not a way to bind before the original no-WFP OS Apply.
        cold.tcp_owned=1;
        assert!(unsafe{NativeSplitWorker::new(&cold)}.is_err());
        cold.tcp_owned=0;cold.tcp_synthetic4=[198,18,87,99];
        assert!(unsafe{NativeSplitWorker::new(&cold)}.is_err());
    }
    #[test]
    fn plan029_native_fakeip_real_business_ref_survives_ttl_and_retires_exactly_once(){
        use crate::v4_client_fake_pool::FakeKey;
        let mut native=unsafe{NativeSplitWorker::new(
            &config(&[],&[],b"cn.example\n"))}.unwrap();
        let real=0xc633644d; // overseas CDN, must remain Tunnel as real IP
        let now=1000u64;
        let proposal=native.fakes.as_mut().unwrap().prepare(FakeKey{
            qname:"cn.example".into(),canonical:"edge.example".into(),
            real4:real,policy_rev:1,resolver_rev:1,
        },1,now).unwrap();
        // Test only: simulate a completed durable journal ACK; actual
        // production may only call this inside FakeJournal::persist_batch.
        native.fakes.as_mut().unwrap()
            .acknowledge_durable(proposal.fake4).unwrap();
        let fake=proposal.fake4;
        let frame=packet(fake.to_be_bytes(),443,b"payload");
        let key=NativeSplitWorker::flow_key(&frame).unwrap();
        assert_eq!(native.hold_fake_first_flow(&frame,fake,real),Ok(Some(key)));
        assert_eq!(native.hold_fake_first_flow(&frame,fake,real),Ok(None));
        assert_eq!(native.fake_refs.len(),1);
        // TTL1 + 10-minute quarantine: even after both expire, the actual
        // active Direct flow reference MUST prevent address reissue.
        assert_eq!(native.fakes.as_mut().unwrap().reap_due(602_100,64),0);
        assert_eq!(native.fakes.as_ref().unwrap().announced_real(fake),Some(real));
        native.retire_flow(key);
        assert!(native.fake_refs.is_empty());
        native.retire_flow(key); // late duplicate Stop/UDP retirement no underflow
        // The first held-flow expiry rescheduled this exact identity for
        // 602100+60000=662100, not the original DNS TTL/quarantine date.
        assert_eq!(native.fakes.as_mut().unwrap().reap_due(662_099,64),0);
        assert_eq!(native.fakes.as_mut().unwrap().reap_due(662_101,64),1);
        assert_eq!(native.fakes.as_ref().unwrap().announced_real(fake),None);
        assert_eq!(native.hold_fake_first_flow(&frame,fake,real),Err(()));
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
