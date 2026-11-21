//! B6: identical DNS routing for both original Android M4 small and jumbo
//! packets. Pure cold-state decision: no system netd override, extra socket,
//! second TUN reader, Go/JNI packet callback, TLS check or FakeIP.
use crate::v4_android_cn_dns::CNDnsMatcher;
use crate::v4_android_dns_ingress::Dns53Observation;

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) enum DnsRoute{
    Original, // non-DNS, incomplete or feature disabled: original encrypted DATA
    PhysicalUDP, // CN matched or explicit all-physical, same bounded M4 socket
    TunnelUDP, // non-CN or explicit all-tunnel, original M3 AEAD flow
    TCP53OriginalTunnel, // ordinary TCP53, unchanged original M1/M3 transport
}
pub(crate) fn choose(
    packet:&[u8],observation:Dns53Observation,enabled:bool,
    physical:bool,cn:Option<&CNDnsMatcher>
)->DnsRoute{
    if !enabled{return DnsRoute::Original}
    match observation{
        Dns53Observation::UdpQuestion{..}=>{
            if physical && cn.is_none_or(|m|m.is_cn_ipv4_query(packet)){
                DnsRoute::PhysicalUDP
            }else{
                DnsRoute::TunnelUDP
            }
        },
        Dns53Observation::TcpPort53=>DnsRoute::TCP53OriginalTunnel,
        Dns53Observation::NotDns|Dns53Observation::Incomplete=>DnsRoute::Original,
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    use crate::v4_android_dns_ingress::observe_ipv4_dns53;
    use crate::v4_android_dns_physical_flow::{PhysicalDnsUdpFlows,MAX_DNS_WIRE,MAX_DNS_REPLY_IPV4,PhysicalDnsError};
    use crate::v4_android_dns_udp_flow::TunnelDnsUdpFlows;
    fn be16(b:&[u8])->u16{u16::from_be_bytes([b[0],b[1]])}
    fn dns_query(name:&str,txid:u16)->Vec<u8>{
        let mut q=vec![0u8;12];
        q[0..2].copy_from_slice(&txid.to_be_bytes());
        q[2]=1;q[5]=1;
        for label in name.split('.'){
            q.push(label.len() as u8);q.extend_from_slice(label.as_bytes());
        }
        q.extend_from_slice(&[0,0,1,0,1]);
        q
    }
    fn ipv4_udp53(name:&str,ip:[u8;4],port:u16)->Vec<u8>{
        let wire=dns_query(name,0x4567);
        let total=28+wire.len();
        let mut p=vec![0u8;total];
        p[0]=0x45;p[2..4].copy_from_slice(&(total as u16).to_be_bytes());
        p[8]=64;p[9]=17;
        p[12..16].copy_from_slice(&[10,66,0,2]);
        p[16..20].copy_from_slice(&ip);
        p[20..22].copy_from_slice(&port.to_be_bytes());
        p[22..24].copy_from_slice(&53u16.to_be_bytes());
        p[24..26].copy_from_slice(&((total-20) as u16).to_be_bytes());
        p[28..].copy_from_slice(&wire);
        p
    }
    fn ipv4_tcp53_syn(ip:[u8;4])->Vec<u8>{
        let mut p=vec![0u8;40];
        p[0]=0x45;p[2..4].copy_from_slice(&40u16.to_be_bytes());
        p[8]=64;p[9]=6;p[12..16].copy_from_slice(&[10,66,0,2]);
        p[16..20].copy_from_slice(&ip);
        p[20..22].copy_from_slice(&50000u16.to_be_bytes());
        p[22..24].copy_from_slice(&53u16.to_be_bytes());
        p[32]=0x50;p[33]=2;p
    }
    fn route(m:&CNDnsMatcher,p:&[u8])->DnsRoute{
        choose(p,observe_ipv4_dns53(p,p.len()),true,true,Some(m))
    }
    #[test]
    fn b6_original_m4_dns_three_compat_modes_and_tcp53_passthrough(){
        let m=CNDnsMatcher::from_go_cold(
            b"domain:baidu.com\nfull:only.example\nregexp:^ads[0-9]+[.]cn$\n"
        ).unwrap();
        let cn=ipv4_udp53("www.baidu.com",[8,8,8,8],50001);
        let noncn=ipv4_udp53("www.example.net",[9,9,9,9],50002);
        let tcp=ipv4_tcp53_syn([8,8,8,8]);
        assert_eq!(route(&m,&cn),DnsRoute::PhysicalUDP);
        assert_eq!(route(&m,&noncn),DnsRoute::TunnelUDP);
        assert_eq!(route(&m,&tcp),DnsRoute::TCP53OriginalTunnel);
        assert_eq!(choose(&cn,observe_ipv4_dns53(&cn,cn.len()),
            false,true,Some(&m)),DnsRoute::Original);
        assert_eq!(choose(&noncn,observe_ipv4_dns53(&noncn,noncn.len()),
            true,false,None),DnsRoute::TunnelUDP);
        assert_eq!(choose(&noncn,observe_ipv4_dns53(&noncn,noncn.len()),
            true,true,None),DnsRoute::PhysicalUDP);
        assert_eq!(choose(&cn[..35],observe_ipv4_dns53(&cn[..35],cn.len()),
            true,true,Some(&m)),DnsRoute::Original);
        let mut different=tcp.clone();different[22..24].copy_from_slice(&443u16.to_be_bytes());
        assert_eq!(route(&m,&different),DnsRoute::Original);
    }
    #[test]
    fn b6_original_m4_cn_physical_tc_inverse_and_noncn_tunnel_inverse(){
        let m=CNDnsMatcher::from_go_cold(b"domain:baidu.com\n").unwrap();
        let cn=ipv4_udp53("www.baidu.com",[8,8,8,8],40001);
        let mut noncn=ipv4_udp53("www.example.net",[9,9,9,9],40002);
        let cn_before=cn.clone();
        assert_eq!(route(&m,&cn),DnsRoute::PhysicalUDP);
        assert_eq!(route(&m,&noncn),DnsRoute::TunnelUDP);
        let mut physical=PhysicalDnsUdpFlows::default();
        let mut tunnel=TunnelDnsUdpFlows::default();
        let mut wire=[0u8;MAX_DNS_WIRE];
        let (n,synthetic,created)=physical.prepare(&cn,&mut wire,100).unwrap();
        assert!(created);
        assert_ne!(synthetic,0x4567);
        assert_eq!(cn,cn_before,"physical question must not mutate original IP");
        let mut answer=wire[..n].to_vec();
        answer[2]=0x83;answer[3]=0x80; // QR=1, TC=1 => App may retry TCP53
        let mut restored=[0u8;MAX_DNS_REPLY_IPV4];
        let size=physical.receive(&answer,&mut restored,101).unwrap();
        assert_eq!(&restored[12..20],&[8,8,8,8,10,66,0,2]);
        assert_eq!(&restored[22..24],&40001u16.to_be_bytes());
        assert_eq!(be16(&restored[28..30]),0x4567);
        assert_eq!(restored[30]&0x02,0x02,"truncation must reach App");
        assert_eq!(physical.len(),0);
        let tcp=ipv4_tcp53_syn([8,8,8,8]);
        assert_eq!(route(&m,&tcp),DnsRoute::TCP53OriginalTunnel);
        let original_noncn=noncn.clone();
        tunnel.rewrite_query(&mut noncn,100).unwrap();
        assert_eq!(&noncn[16..20],&[1,1,1,1]);
        assert_ne!(&noncn[20..22],&original_noncn[20..22]);
        let mut received=noncn.clone();
        received[12..16].copy_from_slice(&[1,1,1,1]);
        received[16..20].copy_from_slice(&[10,66,0,2]);
        received[20..22].copy_from_slice(&53u16.to_be_bytes());
        received[22..24].copy_from_slice(&noncn[20..22]);
        received[30]|=0x80; // DNS answer
        tunnel.rewrite_reply(&mut received,101).unwrap();
        assert_eq!(&received[12..20],&[9,9,9,9,10,66,0,2]);
        assert_eq!(&received[22..24],&40002u16.to_be_bytes());
        assert_eq!(be16(&received[28..30]),0x4567);
        assert_eq!(tunnel.len(),0);
        // Stop retires both original generation inverse maps.
        let (n,_,created)=physical.prepare(&cn,&mut wire,103).unwrap();
        assert!(created);
        let mut old=wire[..n].to_vec();old[2]|=0x80;
        tunnel.rewrite_query(&mut noncn,103).unwrap(); 
        physical.stop();tunnel.stop();
        assert_eq!(physical.receive(&old,&mut restored,104),Err(PhysicalDnsError::Unowned));
        assert_eq!(physical.len(),0);
        assert_eq!(tunnel.len(),0);
        assert_eq!(size,cn.len());
    }
}
