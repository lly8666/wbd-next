//! B2c2a: bounded, transparent inspection of IPv4 DNS53 at the EXISTING
//! single original Rust AndroidOwnedTun::read_ip_scatter site. This is NOT
//! a second TUN reader, DNS redirect, packet modification, source of QNAME
//! policy, or Android system DNS receiver. Original M1/M3 AEAD/PN still
//! transmits the unchanged authentic TUN datagram after this observation.
//!
//! The next gate must replace transparent forwarding only once the same
//! owner has real scoped physical/Tunnel DNS backends, inverse reply map,
//! bounded TCP stream handling, Stop and Android system resolver proof.

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) enum Dns53Observation {
    NotDns,
    UdpQuestion { qtype:u16, wire_len:usize },
    TcpPort53,    // TCP is a flow: NOT a parsed DNS query without reassembly
    Incomplete,   // fragmented/malformed/partly in scatter tail, no takeover
}

fn be16(b:&[u8])->u16{u16::from_be_bytes([b[0],b[1]])}

fn valid_label_char(b:u8)->bool{
    b.is_ascii_alphanumeric()||b==b'-'||b==b'_'
}

/// The original Go B1 query wire grammar: standard single IN question,
/// no compressed question QNAME, at most one bounded EDNS OPT. No heap,
/// no regex, no kernel syscall or Go callback in the Rust M4 hot path.
fn dns_question(wire:&[u8])->Option<u16>{
    if !(17..=4096).contains(&wire.len()){return None}
    let flags=be16(wire.get(2..4)?);
    if flags&0x8000!=0||flags&0x7800!=0||
        be16(wire.get(4..6)?)!=1||
        be16(wire.get(6..8)?)!=0||
        be16(wire.get(8..10)?)!=0{return None}
    let extra=be16(wire.get(10..12)?);
    if extra>1{return None}
    let mut at=12usize;
    let mut qname_bytes=0usize;
    let mut labels=0usize;
    loop{
        let n=usize::from(*wire.get(at)?);
        at=at.checked_add(1)?;
        qname_bytes=qname_bytes.checked_add(n+1)?;
        if qname_bytes>255{return None}
        if n==0{break}
        if n>63||labels>=127{return None}
        let label=wire.get(at..at.checked_add(n)?)?;
        if !label.iter().copied().all(valid_label_char){return None}
        at=at.checked_add(n)?;
        labels+=1;
    }
    if labels==0{return None}
    let q=wire.get(at..at.checked_add(4)?)?;
    let qtype=be16(&q[..2]);
    if qtype==0||be16(&q[2..4])!=1{return None}
    at+=4;
    if extra==0{return (at==wire.len()).then_some(qtype)}
    // The only additional RR allowed by B1 is one explicit EDNS OPT.
    if *wire.get(at)?!=0||be16(wire.get(at+1..at+3)?)!=41{
        return None
    }
    let rdata_len=usize::from(be16(wire.get(at+9..at+11)?));
    (at.checked_add(11)?.checked_add(rdata_len)?==wire.len()).then_some(qtype)
}

/// Called only AFTER original_complete_ipv4_head validates the original
/// authenticated client lease/length, before ANY seal/send or jumbo stage.
/// The head is the *actual* first iovec of the one kernel TUN readv.
/// actual_len is the true single-syscall packet length; never read again.
/// A scatter-tail query is Incomplete, never guessed from a truncated head.
pub(crate) fn observe_ipv4_dns53(head:&[u8],actual_len:usize)->Dns53Observation{
    use Dns53Observation::{Incomplete,NotDns,TcpPort53,UdpQuestion};
    if actual_len<20||actual_len>65535||head.len()<20{return NotDns}
    if head[0]>>4!=4{return NotDns}
    let ihl=usize::from(head[0]&15)*4;
    if ihl<20||ihl>60||ihl>actual_len||ihl>head.len(){return NotDns}
    if usize::from(be16(&head[2..4]))!=actual_len{return NotDns}
    let kind=head[9];
    if kind!=17&&kind!=6{return NotDns}
    // Nonfirst fragments have no L4 destination port to classify safely.
    let frag=be16(&head[6..8]);
    if frag&0x1fff!=0{return NotDns}
    // Without a confirmed destination port, never attribute non-DNS
    // TCP/UDP traffic to the DNS counters.
    if actual_len<ihl+4||head.len()<ihl+4{return NotDns}
    if be16(&head[ihl+2..ihl+4])!=53{return NotDns}
    // First fragments cannot contain the complete query/flow identity.
    if frag&0x2000!=0{return Incomplete}
    if kind==6{
        if actual_len<ihl+20||head.len()<ihl+20{return Incomplete}
        let tcp_hlen=usize::from(head[ihl+12]>>4)*4;
        if tcp_hlen<20||tcp_hlen>60||ihl+tcp_hlen>actual_len||
            ihl+tcp_hlen>head.len(){return Incomplete}
        return TcpPort53
    }
    // Real UDP query: length must match exact IPv4 payload, not a
    // forged smaller DNS datagram followed by hidden bytes.
    if actual_len<ihl+8||head.len()<ihl+8{return Incomplete}
    let udp_len=usize::from(be16(&head[ihl+4..ihl+6]));
    if udp_len<8+17||udp_len!=actual_len-ihl||udp_len>8+4096{
        return Incomplete
    }
    let start=ihl+8;
    if head.len()<start+udp_len-8{return Incomplete}
    let wire=&head[start..start+udp_len-8];
    match dns_question(wire){
        Some(qtype)=>UdpQuestion{qtype,wire_len:wire.len()},
        None=>Incomplete,
    }
}

#[cfg(test)]
mod tests {
    use super::{observe_ipv4_dns53 as inspect,Dns53Observation as Seen};
    fn qname_query(name:&str)->Vec<u8>{
        let mut q=vec![0u8;12];
        q[0]=0x12;q[1]=0x34;q[2]=0x01;q[5]=1;
        for part in name.split('.'){
            q.push(part.len() as u8);
            q.extend_from_slice(part.as_bytes());
        }
        q.extend_from_slice(&[0,0,1,0,1]);
        q
    }
    fn ipv4_udp53(query:&[u8],dest_port:u16)->Vec<u8>{
        let n=20+8+query.len();
        let mut p=vec![0u8;n];
        p[0]=0x45;
        p[2..4].copy_from_slice(&(n as u16).to_be_bytes());
        p[8]=64;p[9]=17;
        p[12..16].copy_from_slice(&[10,55,0,8]);
        p[16..20].copy_from_slice(&[1,1,1,1]);
        p[20..22].copy_from_slice(&56789u16.to_be_bytes());
        p[22..24].copy_from_slice(&dest_port.to_be_bytes());
        p[24..26].copy_from_slice(&((8+query.len()) as u16).to_be_bytes());
        p[28..].copy_from_slice(query);
        p
    }
    fn ipv4_tcp53()->Vec<u8>{
        let mut p=vec![0u8;40];
        p[0]=0x45;p[2..4].copy_from_slice(&40u16.to_be_bytes());
        p[8]=64;p[9]=6;
        p[12..16].copy_from_slice(&[10,55,0,8]);
        p[16..20].copy_from_slice(&[1,1,1,1]);
        p[20..22].copy_from_slice(&56789u16.to_be_bytes());
        p[22..24].copy_from_slice(&53u16.to_be_bytes());
        p[32]=0x50;p[33]=2; // proper TCP SYN, no DNS payload yet
        p
    }
    #[test]
    fn b2c2_original_rust_m4_tun_udp53_observes_real_query_bytes_without_mutation(){
        let p=ipv4_udp53(&qname_query("www.baidu.com"),53);
        let before=p.clone();
        assert_eq!(inspect(&p,p.len()),Seen::UdpQuestion{qtype:1,wire_len:31});
        assert_eq!(p,before,"observer must not mutate original M1 packet/AEAD identity");
        let mut a=ipv4_udp53(&qname_query("www.example.net"),53);
        let length=a.len();
        assert_eq!(inspect(&a,length),Seen::UdpQuestion{qtype:1,wire_len:33});
        a[22..24].copy_from_slice(&5353u16.to_be_bytes());
        assert_eq!(inspect(&a,length),Seen::NotDns);
    }
    #[test]
    fn b2c2_original_rust_m4_tun_tcp53_is_only_flow_candidate(){
        let p=ipv4_tcp53();
        assert_eq!(inspect(&p,p.len()),Seen::TcpPort53);
        assert_eq!(inspect(&p[..25],p.len()),Seen::Incomplete);
        let mut invalid=p;
        invalid[32]=0x40; // TCP data-offset < 5
        assert_eq!(inspect(&invalid,invalid.len()),Seen::Incomplete);
    }
    #[test]
    fn b2c2_original_rust_m4_one_scatter_read_incomplete_never_second_reader(){
        let full=ipv4_udp53(&qname_query("www.baidu.com"),53);
        assert_eq!(inspect(&full[..28],full.len()),Seen::Incomplete);
        assert_eq!(inspect(&full[..45],full.len()),Seen::Incomplete);
        let mut fragment=full.clone();
        fragment[6..8].copy_from_slice(&0x2000u16.to_be_bytes());
        assert_eq!(inspect(&fragment,fragment.len()),Seen::Incomplete);
        fragment[6..8].copy_from_slice(&1u16.to_be_bytes());
        assert_eq!(inspect(&fragment,fragment.len()),Seen::NotDns);
    }
    #[test]
    fn b2c2_original_rust_m4_dns53_rejects_malformed_and_spoof_query(){
        let good=ipv4_udp53(&qname_query("www.baidu.com"),53);
        let mut qr=good.clone();
        qr[30]|=0x80;
        assert_eq!(inspect(&qr,qr.len()),Seen::Incomplete);
        let mut compress=good.clone();
        compress[40]=0xc0; // compressed QNAME in original question
        assert_eq!(inspect(&compress,compress.len()),Seen::Incomplete);
        let mut qcount=good.clone();
        qcount[33]=2; // two questions
        assert_eq!(inspect(&qcount,qcount.len()),Seen::Incomplete);
        let mut badlen=good.clone();
        badlen[24..26].copy_from_slice(&5u16.to_be_bytes());
        assert_eq!(inspect(&badlen,badlen.len()),Seen::Incomplete);
        let mut badip=good.clone();
        badip[2..4].copy_from_slice(&20u16.to_be_bytes());
        assert_eq!(inspect(&badip,badip.len()),Seen::NotDns);
        let mut ip6=good;
        ip6[0]=0x60;
        assert_eq!(inspect(&ip6,ip6.len()),Seen::NotDns);
    }
    #[test]
    fn b2c2_original_rust_m4_dns53_opt_and_bounded_wire_identity(){
        let mut q=qname_query("www.baidu.com");
        q[11]=1; // ARCOUNT=1
        q.extend_from_slice(&[0,0,41,16,0,0,0,0,0,0,0]); // EDNS OPT zero RDATA
        let p=ipv4_udp53(&q,53);
        assert_eq!(inspect(&p,p.len()),Seen::UdpQuestion{qtype:1,wire_len:q.len()});
        let mut bad=p;
        let last=bad.len()-1;
        bad[last]=42;
        assert_eq!(inspect(&bad,bad.len()),Seen::Incomplete);
    }
}
