//! PLAN029 H1713: one signed current-owner Wintun → Rust purpose-first
//! CN DNS53 → independently networked Linux UDP authoritative fixture
//! → durable fake journal → actual Windows app DNS answer → fake→real
//! business UDP → independent Linux guest → original Windows app return.
//! Explicit m0_v4_probe test ABI ONLY; this is not an authenticated
//! Normal/Game4 product worker or forced Tunnel DNS qualification.
#![cfg(all(target_os="windows",feature="m0_v4_probe"))]
use std::ffi::c_void;
use std::io::ErrorKind;
use std::net::{Ipv4Addr,SocketAddrV4};
use std::path::PathBuf;
use std::time::{Duration,Instant,SystemTime,UNIX_EPOCH};
use std::{thread,sync::Arc};
use wbd_platform::windows_native_io::{
    split_borrowed_wintun,wait_ready,WintunFns,ReadResult,WaitResult,
};
use wbd_platform::windows_direct_udp::{
    PhysicalUdpSocket,parse_owned_ipv4_udp,encode_reverse_ipv4_udp,
};
use crate::v4_client_split::{
    DnsEgress,Mode,Ranges,Ipv4Cidr,DomainIndex,DomainRuleType,
    SplitPolicy,DnsUse,Egress,
};
use crate::v4_client_split_wire::{PacketIngress,IngressAction};
use crate::v4_client_dns_pending::{DnsPending,QueryKey,DnsClient,ResolverLane};
use crate::v4_client_fake_pool::{FakeAllocator,FakeKey};
use crate::v4_client_fake_journal::FakeJournal;
use crate::v4_client_dns_wire::synthesize_cn_a;

const DNS_REMOTE_PORT:u16=46098;
const BIZ_REMOTE_PORT:u16=46111;
const DNS_NAME:&str="www.cn.example";
const BIZ_BYTES:&[u8]=b"p029-real-cn-fake-business";
const MAX_L3:usize=2048;
#[repr(C)]
#[derive(Clone,Copy)]
pub struct WbdP029OwnedDnsBusinessV1{
    pub version:u32,pub size:u32,
    pub session:usize,pub read_event:usize,
    pub receive:usize,pub release:usize,
    pub allocate:usize,pub send:usize,
    pub client:[u8;4],pub presented:[u8;4],
    pub remote:[u8;4],pub physical_source:[u8;4],
    pub ifindex:u32,pub client_dns_port:u16,
    pub inner_mtu:u32,pub deadline_ms:u32,
    pub current_luid:u64,pub current_wintun_index:u32,
    pub generation:[u8;16],
}
fn now_unix_ms()->Result<u64,i32>{
    let t=SystemTime::now().duration_since(UNIX_EPOCH).map_err(|_|20)?;
    u64::try_from(t.as_millis()).map_err(|_|20)
}
fn wait_for_udp<'a>(
    rx:&mut wbd_platform::windows_native_io::WintunRx,
    incoming:&'a mut [u8;MAX_L3],
    expected_src:Ipv4Addr,
    expected_dest:Ipv4Addr,
    deadline:Instant,
    port:u16,
)->Result<(usize,wbd_platform::windows_direct_udp::DirectUdpTuple),i32>{
    while Instant::now()<deadline{
        match rx.read(incoming){
            Ok(ReadResult::Frame(n))=>{
                if let Ok(pkt)=parse_owned_ipv4_udp(&incoming[..n],expected_src,expected_dest){
                    if pkt.tuple.target_port==port{
                        return Ok((n,pkt.tuple))
                    }
                }
            }
            Ok(ReadResult::Skipped|ReadResult::NoPacket|ReadResult::EndOfStream)=>{
                match wait_ready(&[rx.event()],10){
                    Ok(WaitResult::Timeout|WaitResult::Ready(_))=>{}
                    Err(e)=>{eprintln!("PLAN029_H1713_FIRST_ERROR stage=wintun_wait {e:?}");return Err(3)}
                }
            }
            Err(e)=>{eprintln!("PLAN029_H1713_FIRST_ERROR stage=wintun_read {e:?}");return Err(4)}
        }
    }
    Err(5)
}
fn send_udp(socket:&PhysicalUdpSocket,packet:&[u8],deadline:Instant)->Result<(),i32>{
    while Instant::now()<deadline{
        match socket.send_ready(packet){
            Ok(n) if n==packet.len()=>return Ok(()),
            Err(e) if e.kind()==ErrorKind::WouldBlock=>{
                thread::sleep(Duration::from_millis(4))
            }
            e=>{eprintln!("PLAN029_H1713_FIRST_ERROR stage=physical_send {e:?}");return Err(8)}
        }
    }
    Err(9)
}
fn recv_udp(socket:&PhysicalUdpSocket,out:&mut [u8],deadline:Instant)->Result<usize,i32>{
    while Instant::now()<deadline{
        match socket.receive_ready(out){
            Ok(n) if n>0=>return Ok(n),
            Err(e) if e.kind()==ErrorKind::WouldBlock=>{
                thread::sleep(Duration::from_millis(4))
            }
            e=>{eprintln!("PLAN029_H1713_FIRST_ERROR stage=physical_recv {e:?}");return Err(10)}
        }
    }
    Err(11)
}
fn exec(c:&WbdP029OwnedDnsBusinessV1)->i32{
    if c.version!=1||c.size as usize!=std::mem::size_of::<WbdP029OwnedDnsBusinessV1>()||
       c.session==0||c.read_event==0||c.receive==0||c.release==0||
       c.allocate==0||c.send==0||c.ifindex==0||c.client_dns_port==0||
       c.current_luid==0||c.current_wintun_index==0||
       c.generation==[0;16]||!(500..=20000).contains(&c.deadline_ms)||
       !(576..=1500).contains(&c.inner_mtu){return 1}
    let client=Ipv4Addr::from(c.client);
    let dns_visible=Ipv4Addr::from(c.presented);
    let guest=Ipv4Addr::from(c.remote);
    let source=Ipv4Addr::from(c.physical_source);
    if client==dns_visible||guest==client||guest==source||
       guest.is_loopback()||source.is_loopback()||
       guest.is_unspecified()||source.is_unspecified(){return 2}
    let funcs=unsafe{WintunFns{
        receive:std::mem::transmute::<usize,unsafe extern "system" fn(*mut c_void,*mut u32)->*const u8>(c.receive),
        release:std::mem::transmute::<usize,unsafe extern "system" fn(*mut c_void,*const u8)>(c.release),
        allocate:std::mem::transmute::<usize,unsafe extern "system" fn(*mut c_void,u32)->*mut u8>(c.allocate),
        send:std::mem::transmute::<usize,unsafe extern "system" fn(*mut c_void,*mut u8)>(c.send),
    }};
    let (mut rx,mut tx)=match unsafe{split_borrowed_wintun(c.session,c.read_event,funcs)}{
        Ok(pair)=>pair,Err(e)=>{eprintln!("PLAN029_H1713_FIRST_ERROR stage=borrow {e:?}");return 3}
    };
    let end=Instant::now()+Duration::from_millis(c.deadline_ms as u64);
    let mut incoming=[0u8;MAX_L3];
    let mut reply=[0u8;MAX_L3];
    let mut output=[0u8;MAX_L3];
    let empty=Ranges::compile(&[]).unwrap();
    let lan=Ranges::compile(&[
        Ipv4Cidr{network:u32::from_be_bytes([10,0,0,0]),bits:8},
        Ipv4Cidr{network:u32::from_be_bytes([172,16,0,0]),bits:12},
        Ipv4Cidr{network:u32::from_be_bytes([192,168,0,0]),bits:16},
    ]).unwrap();
    let pool_range=Ranges::compile(&[Ipv4Cidr{
        network:u32::from_be_bytes([198,18,0,0]),bits:24}]).unwrap();
    let mut domains=DomainIndex::default();
    domains.insert("cn.example",DomainRuleType::Suffix).unwrap();
    let domains=Arc::new(domains);
    let base=SplitPolicy::new(Mode::BypassLanCn,lan.clone(),empty.clone(),
        empty.clone(),pool_range.clone());
    let mut ingress=PacketIngress::new(Arc::new(base),Arc::clone(&domains),
        u32::from(client),64,64,64);
    let (n,dns_tuple)=match wait_for_udp(&mut rx,&mut incoming,client,dns_visible,
        end,53){
        Ok(v)=>v,Err(e)=>{eprintln!("PLAN029_H1713_FIRST_ERROR stage=real_windows_dns53_not_captured");return e}
    };
    if dns_tuple.client_port!=c.client_dns_port{
        eprintln!("PLAN029_H1713_FIRST_ERROR stage=original_dns_source_port_mismatch");
        return 6
    }
    let (name,qtype,original_id)=match ingress.on_ipv4(&incoming[..n],1){
        Ok(IngressAction::DnsUdp{egress:DnsEgress::Direct,
            name,qtype,id,fake_eligible:true})=>(name,qtype,id),
        other=>{eprintln!("PLAN029_H1713_FIRST_ERROR stage=DNS_QNAME_PURPOSE_CLASSIFIER {other:?}");return 7}
    };
    if name!=DNS_NAME||qtype!=1{return 7}
    // In the separate guest test the physical resolver IPv4 IS the guest
    // NIC, not a public DNS. Exactly one Direct endpoint; no backup.
    let mut pending=DnsPending::new(256,1024);
    let query_key=QueryKey{
        name:name.clone(),qtype,lane:ResolverLane::Direct,
        resolver4:u32::from(guest),resolver_port:DNS_REMOTE_PORT,
        policy_revision:1,
    };
    let ticket=match pending.begin(query_key,DnsClient{
        src4:u32::from(client),src_port:c.client_dns_port,
        requested_dns4:u32::from(dns_visible),original_id},0,5_000){
        Ok(t)=>t,Err(e)=>{eprintln!("PLAN029_H1713_FIRST_ERROR stage=dns_ticket {e:?}");return 8}
    };
    let pkt=parse_owned_ipv4_udp(&incoming[..n],client,dns_visible).unwrap();
    let mut dns_query=pkt.data.to_vec();
    if dns_query.len()<12{return 8}
    dns_query[..2].copy_from_slice(&ticket.upstream_id.to_be_bytes());
    let socket=match PhysicalUdpSocket::open(source,c.ifindex,
        SocketAddrV4::new(guest,DNS_REMOTE_PORT)){
        Ok(s)=>s,
        Err(e)=>{eprintln!("PLAN029_H1713_FIRST_ERROR stage=physical_DNS_socket {e:?}");return 9}
    };
    if let Err(e)=send_udp(&socket,&dns_query,end){return e}
    eprintln!("PLAN029_H1713_GENUINE_WINTUN_CN_QNAME_DIRECT_DNS_PHYSICAL_SENT name={} guest={} ifindex={}",
        name,guest,c.ifindex);
    let bytes=match recv_udp(&socket,&mut reply,end){
        Ok(n)=>n,Err(e)=>return e
    };
    let validated=match pending.accept(ticket.upstream_id,
        u32::from(guest),DNS_REMOTE_PORT,ResolverLane::Direct,
        &reply[..bytes],1){
        Ok(r)=>r,Err(e)=>{eprintln!("PLAN029_H1713_FIRST_ERROR stage=direct_dns_answer_validate {e:?}");return 11}
    };
    if validated.answer.candidates.len()!=1||
        validated.answer.candidates[0].address!=u32::from(guest) {
        eprintln!("PLAN029_H1713_FIRST_ERROR stage=guest_dns_A_not_real_guest");
        return 12
    }
    // Non-CN DNS MUST keep Tunnel purpose even if the resolver IP is
    // an actual on-link/LAN guest. A raw WSL guest IP here follows LAN
    // Direct policy: this controlled in-host guest is NOT an overseas
    // CDN D2 counterexample and must never be promoted as such.
    let cold=SplitPolicy::new(Mode::BypassLanCn,lan.clone(),
        empty.clone(),empty.clone(),pool_range.clone());
    if !matches!(cold.destination(u32::from(guest)),Egress::Direct{..})||
       cold.dns_egress(DnsUse::Ordinary{china_domain:false})!=DnsEgress::Tunnel{
        return 13
    }
    let path=match std::env::var_os("WBD_P029_H1713_FAKE_JOURNAL"){
        Some(p)=>PathBuf::from(p),None=>return 14
    };
    let (mut journal,recovered)=match FakeJournal::open(&path){
        Ok(r)=>r,Err(e)=>{eprintln!("PLAN029_H1713_FIRST_ERROR stage=portable_journal_open {e:?}");return 15}
    };
    let mut allocator=FakeAllocator::new(
        u32::from_be_bytes([198,18,0,1]),u32::from_be_bytes([198,18,0,127]),
        &[(u32::from(client),u32::from(client)),
          (u32::from(dns_visible),u32::from(dns_visible))],
        64,1024*1024).unwrap();
    let now=match now_unix_ms(){Ok(t)=>t,Err(e)=>return e};
    if allocator.restore(&recovered,now).is_err(){return 16}
    let real=u32::from(guest);
    let candidate=validated.answer.candidates[0].clone();
    let key=FakeKey{qname:name.clone(),
        canonical:validated.answer.canonical.clone(),real4:real,
        policy_rev:1,resolver_rev:1};
    let prepared=match allocator.prepare(key,candidate.ttl,now){
        Ok(p)=>p,Err(e)=>{eprintln!("PLAN029_H1713_FIRST_ERROR stage=fake_allocate {e:?}");return 17}
    };
    if let Err(e)=journal.persist_batch(&mut allocator,&[prepared.fake4]){
        eprintln!("PLAN029_H1713_FIRST_ERROR stage=durable_real_file_sync {e:?}");
        return 18
    }
    let fake_reply=match synthesize_cn_a(original_id,&name,
        &validated.answer,&allocator,1,1,now){
        Ok(w)=>w,Err(e)=>{eprintln!("PLAN029_H1713_FIRST_ERROR stage=DNS_fake_wire {e:?}");return 19}
    };
    let len=match encode_reverse_ipv4_udp(dns_tuple,
        &fake_reply.packet,55,c.inner_mtu as usize,&mut output){
        Ok(n)=>n,Err(e)=>{eprintln!("PLAN029_H1713_FIRST_ERROR stage=Wintun_DNS_build {e:?}");return 20}
    };
    if let Err(e)=tx.deliver_native_direct_response(&output[..len]){
        eprintln!("PLAN029_H1713_FIRST_ERROR stage=Wintun_DNS_reverse_send {e:?}");return 21
    }
    let fake=Ipv4Addr::from(prepared.fake4);
    eprintln!("PLAN029_H1713_REAL_DNS_FAKE_DURABLE_WINTUN_REPLY_PASS qname={} real={} fake={} ttl={} journal_bytes={}",
        name,guest,fake,prepared.advertised_ttl,journal.written_bytes());
    // FakeIP announced only to the Windows application: physical guest
    // observes its own real IPv4 as destination, never this local 198.18 IP.
    let mut after=SplitPolicy::new(Mode::BypassLanCn,lan,
        empty.clone(),empty.clone(),pool_range);
    after.remember_announced_fake(prepared.fake4,real).unwrap();
    let mut business=PacketIngress::new(Arc::new(after),
        domains,u32::from(client),64,64,64);
    let (biz_n,biz_tuple)=match wait_for_udp(&mut rx,&mut incoming,
        client,fake,end,BIZ_REMOTE_PORT){
        Ok(v)=>v,Err(e)=>{eprintln!("PLAN029_H1713_FIRST_ERROR stage=real_client_fake_business_not_captured");return e}
    };
    match business.on_ipv4(&incoming[..biz_n],2){
        Ok(IngressAction::Direct{real_dst,presented_dst})
            if real_dst==real&&presented_dst==prepared.fake4=>{},
        other=>{eprintln!("PLAN029_H1713_FIRST_ERROR stage=CN_fake_business_not_Direct {other:?}");return 22}
    }
    let biz=parse_owned_ipv4_udp(&incoming[..biz_n],client,fake).unwrap();
    if biz.data!=BIZ_BYTES{return 23}
    let biz_socket=match PhysicalUdpSocket::open(source,c.ifindex,
        SocketAddrV4::new(guest,BIZ_REMOTE_PORT)){
        Ok(s)=>s,Err(e)=>{eprintln!("PLAN029_H1713_FIRST_ERROR stage=biz_physical_bind {e:?}");return 24}
    };
    if let Err(e)=send_udp(&biz_socket,BIZ_BYTES,end){return e}
    let n=match recv_udp(&biz_socket,&mut reply,end){
        Ok(n)=>n,Err(e)=>return e
    };
    let mut expected=BIZ_BYTES.to_vec();
    expected.extend_from_slice(b"-reply");
    if reply[..n]!=expected{
        eprintln!("PLAN029_H1713_FIRST_ERROR stage=Linux_business_wrong_bytes");
        return 25
    }
    let n=match encode_reverse_ipv4_udp(biz_tuple,&reply[..n],56,
        c.inner_mtu as usize,&mut output){
        Ok(n)=>n,Err(e)=>{eprintln!("PLAN029_H1713_FIRST_ERROR stage=biz_reverse_build {e:?}");return 26}
    };
    if let Err(e)=tx.deliver_native_direct_response(&output[..n]){
        eprintln!("PLAN029_H1713_FIRST_ERROR stage=biz_Wintun_reverse {e:?}");return 27
    }
    eprintln!("PLAN029_H1713_REAL_CN_DOMAIN_LAN_GUEST_A_DNS_AND_DIRECT_UDP_RETURN_PASS fake={} real={} source_bound={} ifindex={} owned_stop=caller_joins",
        fake,guest,source,c.ifindex);
    0
}
/// # Safety
/// The original signed Go N4 owner pins Wintun DLL/driver/lease and keeps
/// this pinned ABI valid until this synchronous Rust diagnostic joins.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_plan029_owned_dns_business_trial_v1(
    cfg:*const WbdP029OwnedDnsBusinessV1,
)->i32{
    if cfg.is_null(){return 1}
    let cfg=unsafe{*cfg};
    std::panic::catch_unwind(||exec(&cfg)).unwrap_or(99)
}
