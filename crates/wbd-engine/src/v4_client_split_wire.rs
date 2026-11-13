//! PLAN029 packet decision at the ONE original Rust Wintun ingress.
//! All mutations are generation-owned and live on its TX worker: no Go packet
//! pump, no asynchronous Wintun receive loan, no per-flow thread or system
//! time call on ordinary DATA. This is a policy/wire fixture until the native
//! Direct/DNS workers are installed, NOT an alternate product packet backend.
use std::collections::HashMap;
use std::sync::Arc;

use crate::v4_client_split::{
    DnsEgress,DnsUse,DomainIndex,Egress,FlowKey,FlowPin,SplitError,SplitPolicy,
};

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) enum IngressWireError{
    MalformedIpv4,
    MalformedTransport,
    MalformedDns,
    InvalidDomain,
    NoDirectFlowCapacity,
    UnassociatedFragment,
    FragmentCapacity,
    FragmentedDnsNeedsReassembly,
    UnsupportedDirectProtocol,
}

#[derive(Clone,Debug,Eq,PartialEq)]
pub(crate) enum IngressAction {
    Tunnel,
    Direct { real_dst:u32, presented_dst:u32 },
    DropUnknownFake,
    /// Ordinary captured UDP/53: upstream chosen from QNAME, not resolver IP.
    /// The resolver worker owns all actual async upstream traffic and FakeIP
    /// synthesis; returning this never writes a DNS response or sends a socket.
    DnsUdp {
        egress:DnsEgress,
        name:String,
        qtype:u16,
        id:u16,
        fake_eligible:bool,
    },
    /// A TCP/53 stream must first reconstruct length-prefixed DNS questions.
    /// Its physical/tunnel resolver direction is not guessed from dst IPv4.
    DnsTcpNeedsQuestion,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq,Hash)]
struct FragmentKey{
    src:u32,dst:u32,ip_id:u16,proto:u8,
}
#[derive(Clone,Copy,Debug)]
struct FragmentPin{decision:Egress,expires_at_ms:u64}
#[derive(Clone,Copy,Debug)]
struct PacketView<'a>{
    src:u32,dst:u32,proto:u8,ip_id:u16,
    fragment_offset:u16,more_fragments:bool,
    transport:&'a [u8],
}
fn parse_ipv4(packet:&[u8])->Result<PacketView<'_>,IngressWireError>{
    if packet.len()<20 || packet.len()>u16::MAX as usize ||
       packet[0]>>4!=4{return Err(IngressWireError::MalformedIpv4)}
    let ihl=usize::from(packet[0]&15)*4;
    let total=u16::from_be_bytes([packet[2],packet[3]]) as usize;
    if ihl<20 || ihl>packet.len() || total!=packet.len() ||
       total<ihl{return Err(IngressWireError::MalformedIpv4)}
    let flags=u16::from_be_bytes([packet[6],packet[7]]);
    // Only the DF/MF flags are defined. Reject reserved bits and avoid
    // pretending non-initial fragments have TCP/UDP ports.
    if flags&0x8000!=0{return Err(IngressWireError::MalformedIpv4)}
    Ok(PacketView{
        src:u32::from_be_bytes(packet[12..16].try_into().unwrap()),
        dst:u32::from_be_bytes(packet[16..20].try_into().unwrap()),
        proto:packet[9],
        ip_id:u16::from_be_bytes([packet[4],packet[5]]),
        fragment_offset:flags&0x1fff,
        more_fragments:flags&0x2000!=0,
        transport:&packet[ihl..],
    })
}
fn read_ports(data:&[u8])->Result<(u16,u16),IngressWireError>{
    if data.len()<4{return Err(IngressWireError::MalformedTransport)}
    Ok((u16::from_be_bytes([data[0],data[1]]),
        u16::from_be_bytes([data[2],data[3]])))
}
fn dns_question(data:&[u8])->Result<(u16,String,u16),IngressWireError>{
    if data.len()<17{return Err(IngressWireError::MalformedDns)}
    let flags=u16::from_be_bytes([data[2],data[3]]);
    let qd=u16::from_be_bytes([data[4],data[5]]);
    // Response and unusual opcodes are not ordinary client DNS requests.
    if flags&0x8000!=0 || flags&0x7800!=0 || qd!=1 {
        return Err(IngressWireError::MalformedDns);
    }
    let id=u16::from_be_bytes([data[0],data[1]]);
    let mut cursor=12usize;
    let mut name=String::new();
    let mut labels=0usize;
    loop{
        let Some(&size)=data.get(cursor) else{return Err(IngressWireError::MalformedDns)};
        cursor+=1;
        // A request's compressed pointer is not blindly dereferenced:
        // the real DNS async worker must first normalize uncommon queries.
        if size&0xc0!=0{return Err(IngressWireError::MalformedDns)}
        if size==0{break}
        let size=size as usize;
        if size>63 || cursor+size>data.len() || labels>=127{
            return Err(IngressWireError::MalformedDns)
        }
        if !name.is_empty(){name.push('.')}
        let label=&data[cursor..cursor+size];
        if !label.iter().all(|b|b.is_ascii_alphanumeric()||*b==b'-'){
            return Err(IngressWireError::MalformedDns)
        }
        for b in label{name.push((*b as char).to_ascii_lowercase())}
        cursor+=size;labels+=1;
        if name.len()>253{return Err(IngressWireError::MalformedDns)}
    }
    if name.is_empty()||data.len().saturating_sub(cursor)<4{
        return Err(IngressWireError::MalformedDns)
    }
    let qtype=u16::from_be_bytes([data[cursor],data[cursor+1]]);
    let qclass=u16::from_be_bytes([data[cursor+2],data[cursor+3]]);
    if qclass!=1{return Err(IngressWireError::MalformedDns)}
    Ok((id,name,qtype))
}
pub(crate) struct PacketIngress {
    policy:Arc<SplitPolicy>,
    domains:Arc<DomainIndex>,
    lease4:u32,
    pins:FlowPin,
    fragment_pins:HashMap<FragmentKey,FragmentPin>,
    max_fragments:usize,
}
impl PacketIngress{
    pub fn new(policy:Arc<SplitPolicy>,domains:Arc<DomainIndex>,lease4:u32,
               direct_hard:usize,tunnel_pin_soft:usize,max_fragments:usize)->Self{
        Self{policy,domains,lease4,pins:FlowPin::with_limits(direct_hard,tunnel_pin_soft),
            fragment_pins:HashMap::new(),max_fragments}
    }
    /// Called by the already-owned worker's coarse timer, NOT per packet.
    pub fn on_expiry_tick(&mut self,now_ms:u64){
        self.fragment_pins.retain(|_,v|v.expires_at_ms>now_ms);
    }
    pub fn end_flow(&mut self,key:&FlowKey){self.pins.end(key)}
    pub fn flow_count(&self)->usize{self.pins.len()}
    pub fn fragment_count(&self)->usize{self.fragment_pins.len()}
    pub fn on_ipv4(&mut self,packet:&[u8],now_ms:u64)
        ->Result<IngressAction,IngressWireError>{
        let view=parse_ipv4(packet)?;
        // The current Rust owner still performs its authenticated IPv4
        // source lease check. Here additionally reject foreign Wintun
        // sources before any new Direct or ordinary DNS work.
        if view.src!=self.lease4{return Err(IngressWireError::MalformedIpv4)}
        let fragment_key=FragmentKey{
            src:view.src,dst:view.dst,proto:view.proto,ip_id:view.ip_id,
        };
        if view.fragment_offset!=0{
            let pin=self.fragment_pins.get(&fragment_key)
                .ok_or(IngressWireError::UnassociatedFragment)?;
            return Ok(egress_action(pin.decision))
        }
        if view.proto!=6&&view.proto!=17{
            return match self.policy.destination(view.dst){
                Egress::Tunnel=>Ok(IngressAction::Tunnel),
                Egress::Direct{..}=>Err(IngressWireError::UnsupportedDirectProtocol),
                Egress::RejectUnknownFakeIP=>Ok(IngressAction::DropUnknownFake),
            }
        }
        let (src_port,dst_port)=read_ports(view.transport)?;
        // DNS is a PURPOSE before any CN/LAN classification of the
        // requested DNS server IP. This branch must not borrow ring slots
        // across an async query, so the return is only a decision.
        if dst_port==53 {
            if view.more_fragments {
                return Err(IngressWireError::FragmentedDnsNeedsReassembly)
            }
            if view.proto==6{return Ok(IngressAction::DnsTcpNeedsQuestion)}
            if view.transport.len()<8{return Err(IngressWireError::MalformedTransport)}
            let udp_len=u16::from_be_bytes([view.transport[4],view.transport[5]]) as usize;
            if udp_len<8||udp_len!=view.transport.len(){
                return Err(IngressWireError::MalformedTransport)
            }
            let (id,name,qtype)=dns_question(&view.transport[8..])?;
            let china=self.domains.contains(&name)
                .map_err(|_:SplitError|IngressWireError::InvalidDomain)?;
            let egress=self.policy.dns_egress(DnsUse::Ordinary{china_domain:china});
            return Ok(IngressAction::DnsUdp{
                egress,name,qtype,id,
                fake_eligible:china&&egress==DnsEgress::Direct&&qtype==1,
            })
        }
        let key=FlowKey{
            source:view.src,destination:view.dst,
            source_port:src_port,destination_port:dst_port,protocol:view.proto,
        };
        let decision=if let Some(old)=self.pins.get(&key){old}else{
            let dest=self.policy.destination(view.dst);
            self.pins.first(key,dest).ok_or(IngressWireError::NoDirectFlowCapacity)?
        };
        if view.more_fragments && decision!=Egress::RejectUnknownFakeIP{
            if !self.fragment_pins.contains_key(&fragment_key)
                && self.fragment_pins.len()>=self.max_fragments{
                return Err(IngressWireError::FragmentCapacity)
            }
            self.fragment_pins.insert(fragment_key,FragmentPin{
                decision,expires_at_ms:now_ms.saturating_add(2000),
            });
        }
        Ok(egress_action(decision))
    }
}
fn egress_action(decision:Egress)->IngressAction{
    match decision{
        Egress::Tunnel=>IngressAction::Tunnel,
        Egress::Direct{real_dst,presented_dst}=>{
            IngressAction::Direct{real_dst,presented_dst}
        },
        Egress::RejectUnknownFakeIP=>IngressAction::DropUnknownFake,
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    use crate::v4_client_split::{Ipv4Cidr,Mode,Ranges,DomainRuleType};
    fn ip(a:u8,b:u8,c:u8,d:u8)->u32{u32::from_be_bytes([a,b,c,d])}
    fn range(network:u32,bits:u8)->Ranges{
        Ranges::compile(&[Ipv4Cidr{network,bits}]).unwrap()
    }
    fn ingress(mode:Mode,direct_hard:usize,tunnel_soft:usize)->PacketIngress{
        let mut policy=SplitPolicy::new(mode,
            range(ip(192,168,0,0),16),range(ip(203,0,113,0),24),
            range(ip(172,16,0,0),12),range(ip(198,18,0,0),16));
        if mode==Mode::BypassLanCn {
            policy.remember_announced_fake(ip(198,18,1,9),ip(198,51,100,77)).unwrap();
        }
        let mut domains=DomainIndex::default();
        domains.insert("cn.example",DomainRuleType::Suffix).unwrap();
        PacketIngress::new(Arc::new(policy),Arc::new(domains),ip(10,234,12,34),
            direct_hard,tunnel_soft,128)
    }
    fn ipv4(dst:u32,proto:u8,id:u16,offset:u16,payload:&[u8])->Vec<u8>{
        let src=ip(10,234,12,34);
        let mut out=vec![0u8;20+payload.len()];
        out[0]=0x45;let total=out.len() as u16;
        out[2..4].copy_from_slice(&total.to_be_bytes());
        out[4..6].copy_from_slice(&id.to_be_bytes());
        out[6..8].copy_from_slice(&offset.to_be_bytes());
        out[8]=64;out[9]=proto;
        out[12..16].copy_from_slice(&src.to_be_bytes());
        out[16..20].copy_from_slice(&dst.to_be_bytes());
        out[20..].copy_from_slice(payload);out
    }
    fn udp(dst:u32,sport:u16,dport:u16,body:&[u8])->Vec<u8>{
        let mut data=vec![0u8;8+body.len()];
        data[0..2].copy_from_slice(&sport.to_be_bytes());
        data[2..4].copy_from_slice(&dport.to_be_bytes());
        let n=data.len() as u16;
        data[4..6].copy_from_slice(&n.to_be_bytes());
        data[8..].copy_from_slice(body);
        ipv4(dst,17,22,0,&data)
    }
    fn tcp(dst:u32,sport:u16,dport:u16)->Vec<u8>{
        let mut data=[0u8;20];
        data[0..2].copy_from_slice(&sport.to_be_bytes());
        data[2..4].copy_from_slice(&dport.to_be_bytes());
        data[12]=0x50;data[13]=0x02;
        ipv4(dst,6,23,0,&data)
    }
    fn dns(name:&str,qtype:u16)->Vec<u8>{
        let mut d=vec![0u8;12];
        d[0..2].copy_from_slice(&0x4321u16.to_be_bytes());
        d[2..4].copy_from_slice(&0x0100u16.to_be_bytes());
        d[4..6].copy_from_slice(&1u16.to_be_bytes());
        for label in name.split('.'){
            d.push(label.len() as u8);
            d.extend_from_slice(label.as_bytes())
        }
        d.push(0);
        d.extend_from_slice(&qtype.to_be_bytes());
        d.extend_from_slice(&1u16.to_be_bytes());d
    }
    #[test]
    fn plan029_real_ingress_dns_qname_precedes_dns_upstream_ip_and_noncn_cn_ip_direct(){
        let mut s=ingress(Mode::BypassLanCn,4,2);
        let cn_dns=udp(ip(8,8,8,8),45001,53,&dns("WWW.CN.EXAMPLE",1));
        assert_eq!(s.on_ipv4(&cn_dns,1),Ok(IngressAction::DnsUdp{
            egress:DnsEgress::Direct,name:"www.cn.example".into(),qtype:1,id:0x4321,
            fake_eligible:true}));
        let overseas_fake=ip(198,18,1,9);
        assert_eq!(s.on_ipv4(&tcp(overseas_fake,45001,443),2),
            Ok(IngressAction::Direct{
                real_dst:ip(198,51,100,77),presented_dst:overseas_fake}));
        // The SAME real CDN IP without the fake association stays Tunnel.
        assert_eq!(s.on_ipv4(&tcp(ip(198,51,100,77),45002,443),3),
            Ok(IngressAction::Tunnel));
        let noncn_dns=udp(ip(203,0,113,5),45003,53,&dns("global.example",1));
        assert_eq!(s.on_ipv4(&noncn_dns,4),Ok(IngressAction::DnsUdp{
            egress:DnsEgress::Tunnel,name:"global.example".into(),qtype:1,id:0x4321,
            fake_eligible:false}));
        // A subsequent non-CN domain answer can still be a CN real IP.
        assert_eq!(s.on_ipv4(&tcp(ip(203,0,113,5),45004,443),5),
            Ok(IngressAction::Direct{
                real_dst:ip(203,0,113,5),presented_dst:ip(203,0,113,5)}));
    }
    #[test]
    fn plan029_real_ingress_all_and_lan_never_force_cn_domain_or_ip(){
        for mode in [Mode::All,Mode::BypassLan]{
            let mut s=ingress(mode,2,2);
            let q=udp(ip(203,0,113,4),50333,53,&dns("www.cn.example",28));
            assert_eq!(s.on_ipv4(&q,1),Ok(IngressAction::DnsUdp{
                egress:DnsEgress::Tunnel,name:"www.cn.example".into(),qtype:28,
                id:0x4321,fake_eligible:false}));
            assert_eq!(s.on_ipv4(&tcp(ip(203,0,113,4),50334,443),2),
                Ok(IngressAction::Tunnel));
        }
        let mut s=ingress(Mode::BypassLan,2,2);
        assert_eq!(s.on_ipv4(&tcp(ip(192,168,1,9),50335,80),1),
            Ok(IngressAction::Direct{
                real_dst:ip(192,168,1,9),presented_dst:ip(192,168,1,9)}));
    }
    #[test]
    fn plan029_real_ingress_direct_hard_full_not_tunnel_or_fake_fallback(){
        let mut s=ingress(Mode::BypassLanCn,1,1);
        assert!(matches!(s.on_ipv4(&tcp(ip(203,0,113,1),1001,80),1),
            Ok(IngressAction::Direct{..})));
        assert_eq!(s.on_ipv4(&tcp(ip(203,0,113,2),1002,80),2),
            Err(IngressWireError::NoDirectFlowCapacity));
        assert_eq!(s.on_ipv4(&tcp(ip(8,8,4,4),1003,80),3),
            Ok(IngressAction::Tunnel));
        assert_eq!(s.on_ipv4(&tcp(ip(8,8,4,5),1004,80),4),
            Ok(IngressAction::Tunnel)); // soft pin cache full, tunnel not blocked
        assert_eq!(s.flow_count(),2);
        assert_eq!(s.on_ipv4(&tcp(ip(198,18,3,4),1005,80),5),
            Ok(IngressAction::DropUnknownFake));
        assert_eq!(s.flow_count(),2);
    }
    #[test]
    fn plan029_real_ingress_fragment_pin_ttl_and_unassociated_reject(){
        let mut s=ingress(Mode::BypassLanCn,2,2);
        let target=ip(203,0,113,9);
        // First fragment has source/dest UDP ports and MF; continuation
        // must use the immutable same IP-ID/direct association.
        let first=udp(target,30001,13001,&[7,8,9,10]);
        let mut first=first;first[4..6].copy_from_slice(&777u16.to_be_bytes());
        first[6..8].copy_from_slice(&0x2000u16.to_be_bytes());
        assert!(matches!(s.on_ipv4(&first,100),Ok(IngressAction::Direct{..})));
        let second=ipv4(target,17,777,2,&[1,2,3,4,5,6,7,8]);
        assert!(matches!(s.on_ipv4(&second,150),Ok(IngressAction::Direct{..})));
        assert_eq!(s.fragment_count(),1);
        s.on_expiry_tick(2100);
        assert_eq!(s.on_ipv4(&second,2101),Err(IngressWireError::UnassociatedFragment));
        assert_eq!(s.on_ipv4(&ipv4(target,17,999,2,&[1;8]),5),
            Err(IngressWireError::UnassociatedFragment));
    }
    #[test]
    fn plan029_real_ingress_dns53_cannot_guess_sni_or_dispatch_partial_query(){
        let mut s=ingress(Mode::BypassLanCn,2,2);
        let mut malformed=dns("www.cn.example",1);
        malformed[12]=0xc0; // compressed QNAME without validated context
        assert_eq!(s.on_ipv4(&udp(ip(1,1,1,1),50011,53,&malformed),10),
            Err(IngressWireError::MalformedDns));
        assert_eq!(s.on_ipv4(&tcp(ip(203,0,113,55),50011,53),10),
            Ok(IngressAction::DnsTcpNeedsQuestion));
        let mut fragmented=udp(ip(1,1,1,1),50011,53,&dns("global.example",1));
        fragmented[6..8].copy_from_slice(&0x2000u16.to_be_bytes());
        assert_eq!(s.on_ipv4(&fragmented,11),
            Err(IngressWireError::FragmentedDnsNeedsReassembly));
        // Encrypted DNS on 443 is opaque: no TLS decryption/SNI guessing.
        assert_eq!(s.on_ipv4(&tcp(ip(1,1,1,1),50012,443),12),
            Ok(IngressAction::Tunnel));
    }
}
