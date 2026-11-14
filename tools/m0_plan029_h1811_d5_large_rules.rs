// PLAN029 D5: source-locked REAL PRODUCTION Rust classifier included verbatim,
// compiled as a native test executable without an extra dependency tree.
// This does not simulate OS routes, WinForms connection or Wintun packets.
#[path="../crates/wbd-engine/src/v4_client_split.rs"]
mod production_split;

#[cfg(test)]
mod test {
    use super::production_split::{
        DnsEgress,DnsUse,DomainIndex,DomainRuleType,Egress,FlowKey,FlowPin,
        Ipv4Cidr,Mode,Ranges,SplitPolicy,
    };
    use std::time::Instant;
    fn ip(a:u8,b:u8,c:u8,d:u8)->u32{u32::from_be_bytes([a,b,c,d])}
    fn empty()->Ranges{Ranges::compile(&[]).unwrap()}

    #[test]
    fn plan029_d5_ten_thousand_domain_exact_suffix_dns_and_snapshot_pins(){
        let start=Instant::now();
        let mut names=DomainIndex::default();
        for n in 0..10_000u32{
            let name=format!("host{n:05}.cn.rule.example");
            let kind=if n%2==0{DomainRuleType::Exact}else{DomainRuleType::Suffix};
            names.insert(&name,kind).unwrap();
        }
        assert_eq!(names.len(),10_000);
        let rules_build_ms=start.elapsed().as_millis();
        let policy=SplitPolicy::new(Mode::BypassLanCn,empty(),empty(),empty(),
            Ranges::interval(ip(198,18,0,1),ip(198,18,255,254)).unwrap());
        let qstart=Instant::now();
        for n in 0..10_000u32{
            let name=format!("host{n:05}.cn.rule.example");
            assert!(names.contains(&name).unwrap());
            assert_eq!(policy.dns_egress(DnsUse::Ordinary{
                china_domain:names.contains(&name).unwrap()
            }),DnsEgress::Direct);
            let child=format!("www.{name}");
            assert_eq!(names.contains(&child).unwrap(),n%2!=0);
        }
        assert!(!names.contains("host10000.cn.rule.example").unwrap());
        assert!(!names.contains("host00000.other.rule.example").unwrap());
        let qms=qstart.elapsed().as_millis();
        // Rules change only the snapshot for NEW connections. An already
        // pinned flow never hot-switches its established Tunnel exit.
        let mut pin=FlowPin::with_limits(4,4);
        let key=FlowKey{source:ip(10,66,0,2),destination:ip(8,8,8,8),
            source_port:40100,destination_port:443,protocol:6};
        assert_eq!(pin.first(key,Egress::Tunnel),Some(Egress::Tunnel));
        assert_eq!(pin.first(key,Egress::Direct{
            real_dst:ip(8,8,8,8),presented_dst:ip(8,8,8,8)
        }),Some(Egress::Tunnel));
        assert_eq!(pin.tunnel_len(),1);
        println!("PLAN029_D5_10000_DOMAINS_NATIVE rules=10000 build_ms={rules_build_ms} lookup_ms={qms} os_routes=NOT_MEASURED");
    }

    #[test]
    fn plan029_d5_ten_thousand_cn_ipv4_intervals_no_per_rule_route_emission(){
        let start=Instant::now();
        let cidrs=(0..10_000u32).map(|n|Ipv4Cidr{
            network:ip(101,(n/128) as u8,((n%128)*2) as u8,1),
            bits:32
        }).collect::<Vec<_>>();
        let cn=Ranges::compile(&cidrs).unwrap();
        assert_eq!(cn.interval_count(),10_000);
        for n in 0..10_000u32{
            let a=ip(101,(n/128) as u8,((n%128)*2) as u8,1);
            assert!(cn.contains(a));
            assert!(!cn.contains(a+1));
        }
        let fake=Ranges::interval(ip(198,18,0,1),ip(198,18,255,254)).unwrap();
        let policy=SplitPolicy::new(Mode::BypassLanCn,empty(),cn,empty(),fake);
        let cn_ip=ip(101,0,0,1);
        let abroad=ip(8,8,4,4);
        assert_eq!(policy.destination(cn_ip),
            Egress::Direct{real_dst:cn_ip,presented_dst:cn_ip});
        assert_eq!(policy.destination(abroad),Egress::Tunnel);
        // A non-China DNS name that resolves to a CN address still goes
        // through Tunnel DNS but its later real IPv4 business is Direct.
        assert_eq!(policy.dns_egress(DnsUse::Ordinary{china_domain:false}),
            DnsEgress::Tunnel);
        assert_eq!(policy.destination(cn_ip),
            Egress::Direct{real_dst:cn_ip,presented_dst:cn_ip});
        assert_eq!(policy.destination(ip(198,18,0,1)),Egress::RejectUnknownFakeIP);
        println!("PLAN029_D5_10000_IP_INTERVALS_NATIVE intervals=10000 lookup_and_build_ms={} os_routes=NOT_MEASURED",start.elapsed().as_millis());
    }
}
