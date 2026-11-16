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
use crate::v4_windows_native_tcp_direct::{
    NativeTcpActor,safe_synthetic,reply_qpc_now,reply_qpc_frequency,
};
use crate::v4_windows_native_dns_client_tcp::NativeTcpDnsEndpoints;
use crate::v4_client_split::FlowKey;
use crate::v4_client_startup_padding::{StartupMode,TunnelStartupPadding};

const MAX_PREFIXES:usize=32_768;
const MAX_DOMAIN_BYTES:usize=1<<20;
const MAX_DOMAIN_RULES:usize=20_000;
const DEFAULT_SOFT_FLOWS:usize=4_096;
const STEADY_TCP_DST_PORT:u16=46119;
const STEADY_INGRESS_MAX:usize=8192;
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
struct SteadyIngressRow{
    source_port:u16,seq:u32,payload_bytes:usize,
    entry_qpc:i64,class_qpc:i64,nat_queued_qpc:i64,
}
struct SteadyIngressQpc{
    frequency:i64,rows:Vec<SteadyIngressRow>,dropped:u64,
}
/// Do not equate kernel TCP segments with application messages.
/// The signed analyzer matches an exact per-flow SEQUENCE / payload range.
fn steady_payload_tcp(packet:&[u8])->Option<(u16,u32,usize)>{
    if packet.len()<40||packet[0]>>4!=4||packet[9]!=6{return None}
    let ihl=usize::from(packet[0]&15)*4;
    if ihl<20||ihl+20>packet.len(){return None}
    let total=usize::from(u16::from_be_bytes([packet[2],packet[3]]));
    if total!=packet.len(){return None}
    let port=u16::from_be_bytes([packet[ihl+2],packet[ihl+3]]);
    if port!=STEADY_TCP_DST_PORT{return None}
    let tcp=usize::from(packet[ihl+12]>>4)*4;
    if tcp<20||ihl+tcp>=total{return None}
    let src=u16::from_be_bytes([packet[ihl],packet[ihl+1]]);
    let seq=u32::from_be_bytes(packet[ihl+4..ihl+8].try_into().ok()?);
    Some((src,seq,total-ihl-tcp))
}
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
// Already-owned TCP/DNS L3 moves into the sole RX mailbox. UDP writes
// into its caller scratch and requires only one copy on successful queue.
pub(crate) enum NativeReverse{Owned(Vec<u8>),InScratch(usize)}
// Repeated TCP/DNS reverse packets must not trigger WinSock WSAPoll
// again for the SAME empty Direct UDP socket on the same native TX turn.
// The budget is the number of ACTUAL live UDP sockets, not a timer or
// global flow table scan. A real UDP packet resets the scan budget.
#[derive(Default)]
struct UdpEmptyPollTurn{checked:usize}
impl UdpEmptyPollTurn{
    fn reset(&mut self){self.checked=0}
    fn should_poll(&self,live:usize)->bool{live>0&&self.checked<live}
    fn observed(&mut self,quantum:usize,delivered:bool){
        if delivered{self.checked=0}
        else{self.checked=self.checked.saturating_add(quantum)}
    }
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
    dns_tcp_endpoints:NativeTcpDnsEndpoints,
    // Tunnel-only original M1 LINK padding; OFF is a no-parse fast branch.
    startup_padding:TunnelStartupPadding,
    padding_enabled:bool,
    next_reverse_lane:usize,
    // Same-owner ready-only negative UDP WSAPoll suppression. Scans at
    // most one full rotating socket sweep per TX turn if no UDP arrived.
    udp_empty_poll:UdpEmptyPollTurn,
    last_tick_ms:u64,
    // Signed original Windows/WSL2 probe only; no always-on tracing.
    steady_qpc:Option<SteadyIngressQpc>,
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
            let (journal,recovered)=FakeJournal::open_async(&PathBuf::from(path))
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
        let steady_signed=cfg!(feature="m0_v4_probe") &&
            std::env::var("GITHUB_ACTIONS").ok().as_deref()==Some("true") &&
            std::env::var("WBD_PLAN029_NATIVE_V3_TRIAL").ok().as_deref()==Some("1") &&
            std::env::var("WBD_PLAN029_P2_MIXED_SCENE").ok().as_deref()==Some("1") &&
            std::env::var("WBD_PLAN029_P2_STEADY_QPC_SCENE").ok().as_deref()==Some("1");
        let steady_qpc=if steady_signed{
            Some(SteadyIngressQpc{frequency:reply_qpc_frequency().ok_or(())?,
                rows:Vec::with_capacity(STEADY_INGRESS_MAX),dropped:0})
        }else{None};
        Ok(Self{ingress:PacketIngress::new(policy,Arc::new(domains),
            u32::from(lease),c.direct_hard as usize,DEFAULT_SOFT_FLOWS,1024),
            udp,fakes,fake_refs:HashMap::new(),journal,dns,tunnel_dns,tunnel_map,
            tcp:None,tcp_plan,tcp_enabled:false,
            dns_tcp_endpoints:NativeTcpDnsEndpoints{
                physical:underlay,physical_ifindex:c.physical_ifindex,
                lease,wintun_ifindex:0,direct:direct_dns,tunnel:tunnel_dns,
            },
            startup_padding:TunnelStartupPadding::new(StartupMode::Off,1),
            padding_enabled:false,
            next_reverse_lane:0,udp_empty_poll:UdpEmptyPollTurn::default(),
            last_tick_ms:0,steady_qpc})
    }
    /// Called exactly once from authenticated V3 cold attach. The
    /// generation's authenticated epoch seeds a NON-cryptographic window
    /// chooser; AEAD keys/PN ownership remain exclusively original M1.
    pub(crate) fn set_startup_padding(&mut self,mode:StartupMode,
        epoch:[u8;16]){
        let a=u64::from_be_bytes(epoch[..8].try_into().unwrap());
        let b=u64::from_be_bytes(epoch[8..].try_into().unwrap());
        self.startup_padding=TunnelStartupPadding::new(mode,a^b^0x574244_029);
        self.padding_enabled=mode!=StartupMode::Off;
    }
    pub(crate) fn startup_padding_enabled(&self)->bool{
        self.padding_enabled
    }
    pub(crate) fn startup_padding_mode_name(&self)->&'static str{
        self.startup_padding.mode_name()
    }
    /// Only the original TX stages classified Tunnel DATA, and it passes
    /// the actual M1 record_wire_mtu spare bytes; Direct never calls this.
    pub(crate) fn propose_tunnel_padding(&mut self,packet:&[u8],
        now_ms:u64,room:usize)->usize{
        if !self.padding_enabled{return 0}
        self.startup_padding.propose(packet,now_ms,room)
    }
    pub(crate) fn set_wintun_ifindex(&mut self,ifindex:u32)->Result<(),()>{
        if ifindex==0||ifindex==u32::MAX{return Err(())}
        self.dns_tcp_endpoints.wintun_ifindex=ifindex;
        Ok(())
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
    /// Only on a failed Tunnel DNS transaction rewrite. The source
    /// packet is still the original unmodified app packet; queue one
    /// SERVFAIL for its original tuple/ID through the shared Rust TX
    /// reverse mailbox. Never retry as Direct or poll a second resolver.
    pub(crate) fn reject_tunnel_dns(&mut self,packet:&[u8])->bool{
        self.dns.fail_tunnel_query(packet)
    }
    pub(crate) fn has_udp_flows(&self)->bool{
        self.udp.len()>0||self.dns.has_work()||
            self.tcp.as_ref().is_some_and(|t|t.has_work())
    }
    /// Only UDP flows above the 16-handle event budget, DNS and client
    /// DNS/TCP retain the legacy <=10ms fallback. Ordinary physical
    /// Direct UDP wakes from its own registered WinSock read event.
    /// TCP retains its existing 16 fixed event shards/deadlines.
    pub(crate) fn needs_10ms_poll(&self)->bool{
        self.udp.has_unwatched_flows()||self.dns.has_work()||
            self.tcp.as_ref().is_some_and(|t|t.has_dns_sessions())
    }
    /// Signed original TX boundary-only map; no per-packet lookup in product.
    pub(crate) fn original_tcp_source_for_proxy(&self,p:u16)->Option<u16>{
        self.tcp.as_ref()?.original_source_for_proxy(p)
    }
    pub(crate) fn tcp_socket_wait_handles(&self)->Option<&[usize]>{
        if !self.tcp_enabled{return None}
        self.tcp.as_ref().map(|tcp|tcp.socket_event_handles())
    }
    pub(crate) fn udp_socket_wait_handles(&self)->&[usize]{
        self.udp.wake_handles()
    }
    pub(crate) fn note_udp_socket_wake(&mut self,index:usize){
        self.udp.note_socket_wake(index);
    }
    pub(crate) fn note_tcp_socket_wake(&mut self,shard:usize){
        if self.tcp_enabled{
            if let Some(tcp)=self.tcp.as_mut(){tcp.note_socket_event(shard)}
        }
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
        // An internal Wintun-bound TCP socket already has its genuine
        // Winsock source port registered by the single TX owner. Its TCP
        // SYN/data goes over the authenticated Tunnel; never recursively
        // intercept it as another client DNS/TCP query.
        if self.tcp_enabled&&packet.len()>=40&&packet[0]>>4==4&&
           packet[9]==6&&packet[12..16]==self.dns_tcp_endpoints.lease.octets()&&
           packet[16..20]==self.tunnel_dns.octets(){
            let ihl=usize::from(packet[0]&15)*4;
            if ihl>=20&&ihl+4<=packet.len()&&
               u16::from_be_bytes([packet[ihl+2],packet[ihl+3]])==53&&
               self.tcp.as_ref().is_some_and(|t|
                 t.is_internal_tunnel_dns_tcp(
                   u16::from_be_bytes([packet[ihl],packet[ihl+1]]))){
                return NativeDecision::Tunnel
            }
        }
        let probe=self.steady_qpc.as_ref()
            .and_then(|_|steady_payload_tcp(packet));
        let qpc_in=if probe.is_some(){reply_qpc_now().unwrap_or(0)}else{0};
        let fakes=&self.fakes;
        let action=self.ingress.on_ipv4_with_announced_fake(packet,now_ms,
            |ip|fakes.as_ref().and_then(|pool|pool.announced_real(ip)));
        let qpc_class=if probe.is_some(){reply_qpc_now().unwrap_or(0)}else{0};
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
                    if ok{
                        if let (Some((source_port,seq,payload_bytes)),Some(s))=
                            (probe,self.steady_qpc.as_mut()){
                            let end=reply_qpc_now().unwrap_or(0);
                            if qpc_in>0&&qpc_class>=qpc_in&&end>=qpc_class{
                                if s.rows.len()<STEADY_INGRESS_MAX{
                                    s.rows.push(SteadyIngressRow{
                                        source_port,seq,payload_bytes,
                                        entry_qpc:qpc_in,class_qpc:qpc_class,
                                        nat_queued_qpc:end,
                                    });
                                }else{s.dropped+=1;}
                            }
                        }
                    }
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
                            self.fakes.as_mut(),self.journal.as_mut()){
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
            Ok(IngressAction::DnsTcpNeedsQuestion)=>{
                if self.tcp_enabled&&self.tcp.as_mut()
                    .is_some_and(|tcp|tcp.dns_ingress(packet,now_ms).is_ok()){
                    NativeDecision::DirectHandled
                }else{NativeDecision::LocalDrop}
            },
            Ok(IngressAction::DropUnknownFake)|
            Err(_)=>NativeDecision::LocalDrop,
        }
    }
    /// Restore the exact TCP NAT return already selected by this worker
    /// when its bounded cross-worker mailbox reports Full. Unlike UDP,
    /// a lost ACK/window update can trigger seconds of retransmit delay.
    /// Called exclusively on the original TX thread, before any new TCP
    /// return is popped; never moves DNS or physical Direct flow identity.
    pub(crate) fn requeue_tcp_reverse(&mut self,packet:Vec<u8>)
        ->Result<(),()>{
        self.tcp.as_mut().ok_or(())?.restore_tcp_ready_front(packet)
    }
    pub(crate) fn poll_udp_reverse(&mut self,out:&mut[u8],now_ms:u64)
        ->Option<NativeReverse>{
        // Fair 3-queue rotation prevents a busy TCP handshake burst from
        // indefinitely starving physical UDP business or DNS replies.
        for step in 0..3{
            let lane=(self.next_reverse_lane+step)%3;
            let ready=match lane{
                0=>self.tcp.as_mut().and_then(|tcp|tcp.ready_pop())
                    .and_then(|l3|if l3.len()<=out.len(){
                        Some(NativeReverse::Owned(l3))
                    }else{None}),
                // DNS I/O was polled once by tick() at the start of this
                // original TX owner turn. Reverse packet dequeue must NOT
                // re-run WSAPoll or allocate per unrelated UDP/TCP packet.
                1=>self.dns.pop().and_then(|l3|if l3.len()<=out.len(){
                    Some(NativeReverse::Owned(l3))
                }else{None}),
                _=>{
                    let live=self.udp.len();
                    if !self.udp_empty_poll.should_poll(live){None}else{
                        let quantum=self.udp.poll_work_bound();
                        let reply=self.udp.poll_reverse_ready(out,now_ms)
                            .ok().flatten();
                        // One full no-data socket sweep at most, even
                        // while 32 unrelated TCP returns are delivered.
                        // If actual UDP arrived, continue fair round-robin
                        // packet delivery within this same bounded turn.
                        self.udp_empty_poll.observed(quantum,reply.is_some());
                        reply.map(NativeReverse::InScratch)
                    }
                },
            };
            if ready.is_some(){
                self.next_reverse_lane=(lane+1)%3;
                return ready
            }
        }
        None
    }
    pub(crate) fn tick(&mut self,now_ms:u64)->bool{
        // One old native TX turn, not one packet or one flow. A newly
        // queued physical response will be checked on the next wake.
        self.udp_empty_poll.reset();
        let mut progressed=false;
        // DNS filesystem completion is a bounded, nonblocking mailbox
        // operation on this TX turn. The exact durable journal writer
        // runs on one independent blocking thread, never under M2/NPF,
        // Wintun ring borrowing or the original Tunnel send lock.
        if let (Some(pool),Some(journal))=
            (self.fakes.as_mut(),self.journal.as_mut()){
            journal.poll_completed(pool,8);
        }
        // One DNS network poll per original TX turn, independent of how
        // many Direct TCP/UDP/DNS returns the fair 32-packet RX handoff
        // drains. This removes repeated WSAPoll and Vec allocations from
        // other flows' latency path without a timer or new socket worker.
        if self.dns.needs_poll(){
            self.dns.poll(now_ms,self.fakes.as_mut(),self.journal.as_mut());
        }
        // The original Rust TX bounded scheduler already owns this call.
        // Service max 8 kernel accepts/active native TCP relays each turn,
        // while cold-only expiry remains on the existing 1-second sweep.
        if self.tcp_enabled && self.tcp.as_ref()
            .is_some_and(|tcp|tcp.needs_service(now_ms)){
         if let Some(tcp)=self.tcp.as_mut(){
            let service=tcp.tick(now_ms);
            progressed|=service.advanced;
            for key in service.retired{
                self.retire_flow(FlowKey{
                    source:key.client,destination:key.presented,
                    source_port:key.source_port,destination_port:key.target_port,
                    protocol:6,
                });
            }
         }
        }
        // DNS/TCP shares the previously authorized Windows kernel listener
        // and exact NAT reverse. It has independent 256-ticket admission.
        if self.tcp_enabled && self.tcp.as_ref()
            .is_some_and(|tcp|tcp.has_dns_sessions()){
            let ingress=&self.ingress;
            if let Some(tcp)=self.tcp.as_mut(){
                tcp.tick_dns(now_ms,self.dns_tcp_endpoints,
                    &|name|ingress.tcp_dns_egress(name),
                    self.fakes.as_mut(),self.journal.as_mut());
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
        if now_ms.saturating_sub(self.last_tick_ms)<1_000{return progressed}
        if self.padding_enabled{self.startup_padding.expire_coarse(now_ms);}
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
        // Only once per coarse expiry turn and only above the WAL
        // high-water mark. The full snapshot is prepared in cold/sparse
        // code; disk flush/atomic replacement runs on the same isolated
        // blocking writer as new DNS FakeIP allocations.
        if let (Some(pool),Some(journal))=
            (self.fakes.as_ref(),self.journal.as_mut()){
            journal.maybe_compact(pool,now_ms);
        }
        self.ingress.on_expiry_tick(now_ms);
        if let Ok(mut map)=self.tunnel_map.lock(){map.expire(now_ms)}
        // FakeIP journal and ref expiry require the separate DNS worker
        // before any synthesized mapping can be exposed.
        progressed
    }
}

impl Drop for NativeSplitWorker{
    fn drop(&mut self){
        let Some(trace)=self.steady_qpc.as_ref()else{return};
        // Original owner Stop only. Strictly <=96 records per line, no
        // app content, DNS, IPs or per-packet printf in the hot path.
        let total=trace.rows.len();
        for (index,part) in trace.rows.chunks(96).enumerate(){
            let rows=part.iter().map(|r|format!(
                "{}:{}:{}:{}:{}:{}",
                r.source_port,r.seq,r.payload_bytes,
                r.entry_qpc,r.class_qpc,r.nat_queued_qpc
            )).collect::<Vec<_>>().join(",");
            eprintln!("PLAN029_H1966_STEADY_INGRESS_QPC_FINAL frequency={} total={} dropped={} chunk={} count={} rows={} source=original_rust_wintun_tx_test_only",
                trace.frequency,total,trace.dropped,index,part.len(),rows);
        }
        if total==0{
            eprintln!("PLAN029_H1966_STEADY_INGRESS_QPC_FINAL frequency={} total=0 dropped={} chunk=0 count=0 rows= source=original_rust_wintun_tx_test_only",
                trace.frequency,trace.dropped);
        }
    }
}

#[cfg(test)]
mod tests{
    use super::*;
    #[test]
    fn plan029_h1966_steady_probe_accepts_only_genuine_tcp_payload_and_seq(){
        let mut wire=vec![0u8;40+1024];
        wire[0]=0x45;wire[9]=6;
        let total=wire.len() as u16;
        wire[2..4].copy_from_slice(&total.to_be_bytes());
        wire[20..22].copy_from_slice(&41231u16.to_be_bytes());
        wire[22..24].copy_from_slice(&STEADY_TCP_DST_PORT.to_be_bytes());
        wire[24..28].copy_from_slice(&0xfedcba98u32.to_be_bytes());
        wire[32]=0x50; // real 20-byte TCP header
        assert_eq!(steady_payload_tcp(&wire),Some((41231,0xfedcba98,1024)));
        wire[23]=0x20;
        assert_eq!(steady_payload_tcp(&wire),None); // foreign target port
        wire[23]=0x27;
        wire[32]=0x40;
        assert_eq!(steady_payload_tcp(&wire),None); // malformed TCP header
        wire[32]=0x50;
        wire[2..4].copy_from_slice(&40u16.to_be_bytes());
        assert_eq!(steady_payload_tcp(&wire),None); // forged L3 length
    }
    #[test]
    fn plan029_owned_reverse_reuses_exact_vec_allocation(){
        let packet=vec![0x45,1,2,3,4,5];let ptr=packet.as_ptr();
        match NativeReverse::Owned(packet){
            NativeReverse::Owned(moved)=>{
                assert_eq!(moved.as_ptr(),ptr);
                assert_eq!(moved[1..],[1,2,3,4,5]);
            },
            _=>panic!("owned TCP lost allocation"),
        }
    }
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
        let mut scratch=[0u8;2048];
        // A finished DNS reply already owns a Vec. Native TX passes it
        // directly into the original RX mailbox rather than re-copying it.
        let owned=match s.poll_udp_reverse(&mut scratch,2).unwrap(){
            NativeReverse::Owned(bytes)=>bytes,
            NativeReverse::InScratch(_)=>panic!("DNS reply lost owned Vec"),
        };
        assert_eq!(owned[20..22],[0,53]);
        assert_eq!(owned[31]&0xf,2); // DNS RCODE at IPv4(20)+UDP(8)+flags byte1(3)
        assert!(owned.len()>=40);
        assert!(!s.has_udp_flows());
        s.tick(1001);
    }
    #[test]
    fn plan029_ready_dns_drain_never_repolls_one_pending_socket_per_packet(){
        let mut cfg=config(&[],&[],b"");
        cfg.route_mode=0;
        let mut owner=unsafe{NativeSplitWorker::new(&cfg)}.unwrap();
        let mut dns=vec![0u8;12];
        dns[2..4].copy_from_slice(&0x0100u16.to_be_bytes());
        dns[4..6].copy_from_slice(&1u16.to_be_bytes());
        dns.extend_from_slice(b"\x02cn\x07example\x00\x00\x01\x00\x01");
        let request=packet([1,1,1,1],53,&dns);
        // Produce genuine bounded local error replies without touching a
        // physical resolver socket or a Wintun ring. These are ready-only
        // packets; repeated dequeue cannot justify another DNS WSAPoll.
        for _ in 0..8{
            assert!(owner.reject_tunnel_dns(&request));
        }
        assert_eq!(owner.dns.poll_invocations(),0);
        owner.tick(1);
        assert_eq!(owner.dns.poll_invocations(),0);
        let mut bytes=[0u8;2048];
        for _ in 0..8{
            let Some(NativeReverse::Owned(reply))=
                owner.poll_udp_reverse(&mut bytes,1)else{
                panic!("original DNS reverse packet was lost");
            };
            assert_eq!(reply[31]&15,2); // exact local SERVFAIL
        }
        assert!(owner.poll_udp_reverse(&mut bytes,1).is_none());
        assert_eq!(owner.dns.poll_invocations(),0);
        assert!(!owner.has_udp_flows());
    }
    #[test]
    fn plan029_udp_empty_socket_is_not_wsapolled_32x_for_tcp_reverse(){
        // No physical sockets or real networking required: the test
        // models one normal Direct UDP socket sharing TX with a burst of
        // unrelated Direct TCP returns, then a 33-flow rotating scan.
        let mut b=UdpEmptyPollTurn::default();
        assert!(!b.should_poll(0));
        assert!(b.should_poll(1));
        b.observed(1,false);
        for _ in 0..32{
            assert!(!b.should_poll(1)); // no redundant WinSock calls
        }
        b.reset();
        assert!(b.should_poll(1)); // the next native TX turn wakes
        b.observed(1,true); // an actually delivered UDP response
        assert!(b.should_poll(1)); // can drain further ready UDP
        b.reset();
        for _ in 0..3{
            assert!(b.should_poll(33));
            b.observed(16,false);
        }
        assert!(!b.should_poll(33)); // ceil(33/16) bounded fair sweep
        b.reset();
        assert!(b.should_poll(33));
        // No TCP/Tunnel timer, no synthetic response receipt, no new
        // resource cap: every socket gets a chance before idle suppression.
    }
    #[test]
    fn plan029_all_tunnel_reverse_idle_skips_only_empty_real_work(){
        let mut cfg=config(&[],&[],b"");
        cfg.route_mode=0;
        let mut owner=unsafe{NativeSplitWorker::new(&cfg)}.unwrap();
        // No outgoing Direct sockets or unanswered DNS means the TX
        // worker's 32-quantum reverse attempt would be pure overhead.
        assert!(!owner.has_udp_flows());
        assert_eq!(owner.on_packet(&packet([8,8,8,8],443,b"hello"),1),
            NativeDecision::Tunnel);
        assert!(!owner.has_udp_flows());
        // An honest forced-Tunnel DNS admission failure is STILL real
        // local work. It must be delivered via the same Wintun return
        // mailbox even if the whole route mode is All.
        let mut dns=vec![0u8;12];
        dns[2..4].copy_from_slice(&0x0100u16.to_be_bytes());
        dns[4..6].copy_from_slice(&1u16.to_be_bytes());
        dns.extend_from_slice(&[3,119,119,119,7,101,120,97,109,112,108,101,0]);
        dns.extend_from_slice(&1u16.to_be_bytes());
        dns.extend_from_slice(&1u16.to_be_bytes());
        let query=packet([1,1,1,1],53,&dns);
        assert!(matches!(owner.on_packet(&query,2),NativeDecision::TunnelDns));
        assert!(!owner.has_udp_flows());
        assert!(owner.reject_tunnel_dns(&query));
        assert!(owner.has_udp_flows());
        let mut out=[0u8;2048];
        assert!(owner.poll_udp_reverse(&mut out,3).is_some());
        assert!(!owner.has_udp_flows());
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
    fn plan029_native_cold_startup_padding_off_and_generation_seed_no_direct_side_effect(){
        let mut c=config(&[],&[],b"cn.example\n");
        c.route_mode=2;
        let mut s=unsafe{NativeSplitWorker::new(&c)}.unwrap();
        assert!(!s.startup_padding_enabled());
        let probe=packet([203,0,113,77],443,&[7u8;128]);
        assert_eq!(s.propose_tunnel_padding(&probe,10,256),0);
        s.set_startup_padding(StartupMode::Flows,[2u8;16]);
        assert!(s.startup_padding_enabled());
        let mut total=0;
        for _ in 0..256{total+=s.propose_tunnel_padding(&probe,11,256)}
        assert!(total>2048,"old per-flow quota must not suppress valid records");
        s.set_startup_padding(StartupMode::Off,[3u8;16]);
        assert_eq!(s.propose_tunnel_padding(&probe,12,256),0);
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
