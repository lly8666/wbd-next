//! PLAN029 DNS query-level response creation, not a DNS listener.
//! Only a successfully resolved CN QNAME can get a local fake A; every
//! advertised fake must already have a durable reservation in FakeAllocator.
//! Non-CN answers are NOT rewritten here; their real IPs remain untouched.
//! Encrypted DNS is not visible, never parsed as a speculative hostname.
use crate::v4_client_dns_answer::{DnsAResolution,DnsAnswerStatus};
use crate::v4_client_fake_pool::{FakeAllocator,FakeKey};

const DNS_WIRE_CAP:usize=1232;
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) enum FakeDnsWireError{
    NotCnAAnswer,InvalidName,MissingDurableMapping,
    MismatchedCandidates,Capacity,InvalidCnameChain,
}
#[derive(Clone,Debug,Eq,PartialEq)]
pub(crate) struct FakeDnsWire{
    pub packet:Vec<u8>,
    pub fakes:Vec<u32>,
}
fn encode_name(name:&str,out:&mut Vec<u8>)->Result<(),FakeDnsWireError>{
    if name.is_empty()||name.len()>253||!name.is_ascii(){
        return Err(FakeDnsWireError::InvalidName)
    }
    for l in name.split('.') {
        if l.is_empty()||l.len()>63||
            l.as_bytes().first()==Some(&b'-')||
            l.as_bytes().last()==Some(&b'-')||
            !l.bytes().all(|b|b.is_ascii_lowercase()||b.is_ascii_digit()||b==b'-'){
            return Err(FakeDnsWireError::InvalidName)
        }
        out.push(l.len() as u8);out.extend_from_slice(l.as_bytes());
    }
    out.push(0);
    if out.len()>DNS_WIRE_CAP{return Err(FakeDnsWireError::Capacity)}
    Ok(())
}
fn push_rr(packet:&mut Vec<u8>,owner:&str,typ:u16,ttl:u32,
    data:&[u8])->Result<(),FakeDnsWireError>{
    encode_name(owner,packet)?;
    let data_len=u16::try_from(data.len()).map_err(|_|FakeDnsWireError::Capacity)?;
    packet.extend_from_slice(&typ.to_be_bytes());
    packet.extend_from_slice(&1u16.to_be_bytes());
    packet.extend_from_slice(&ttl.to_be_bytes());
    packet.extend_from_slice(&data_len.to_be_bytes());
    packet.extend_from_slice(data);
    if packet.len()>DNS_WIRE_CAP{return Err(FakeDnsWireError::Capacity)}
    Ok(())
}
fn question(out:&mut Vec<u8>,qname:&str,qtype:u16)->Result<(),FakeDnsWireError>{
    encode_name(qname,out)?;
    out.extend_from_slice(&qtype.to_be_bytes());
    out.extend_from_slice(&1u16.to_be_bytes());
    Ok(())
}
fn header(id:u16,answers:u16,rcode:u16)->Vec<u8>{
    let mut h=vec![0u8;12];
    h[0..2].copy_from_slice(&id.to_be_bytes());
    // QR=1, standard response, RD=1, RA=1; AD=0, not DNSSEC signed.
    // No OPT or additional records: no real A/IP hints can escape.
    h[2..4].copy_from_slice(&(0x8180u16|(rcode&0xf)).to_be_bytes());
    h[4..6].copy_from_slice(&1u16.to_be_bytes());
    h[6..8].copy_from_slice(&answers.to_be_bytes());
    h
}
/// Build the all-or-none client-visible CN DNS response after the cold
/// writer acknowledged the exact snapshot for every fake. Candidate A
/// addresses are never exposed on the DNS wire (or via additional).
/// This doesn't drive upstream sockets, mutate Wintun or open a route.
pub(crate) fn synthesize_cn_a(
    id:u16,qname:&str,resolved:&DnsAResolution,
    allocator:&FakeAllocator,
    policy_rev:u64,resolver_rev:u64,now_unix_ms:u64
)->Result<FakeDnsWire,FakeDnsWireError>{
    if resolved.status!=DnsAnswerStatus::Answered||
        resolved.candidates.is_empty()||resolved.candidates.len()>16{
        return Err(FakeDnsWireError::NotCnAAnswer)
    }
    if resolved.cname_chain.len()>8 ||
        !resolved.cname_chain.first().map_or(qname==resolved.canonical,|first|first==qname) {
        return Err(FakeDnsWireError::InvalidCnameChain)
    }
    let mut visible=Vec::with_capacity(resolved.candidates.len());
    let mut ttl=Vec::with_capacity(resolved.candidates.len());
    let mut unique=std::collections::HashSet::new();
    for candidate in &resolved.candidates {
        let key=FakeKey{
            qname:qname.to_string(),
            canonical:resolved.canonical.clone(),
            real4:candidate.address,policy_rev,resolver_rev,
        };
        let fake=allocator.issued_for(&key,now_unix_ms)
            .ok_or(FakeDnsWireError::MissingDurableMapping)?;
        if !unique.insert(fake){
            return Err(FakeDnsWireError::MismatchedCandidates)
        }
        visible.push(fake);
        ttl.push(candidate.ttl.min(60));
    }
    let answer_count=resolved.cname_chain.len().checked_add(visible.len())
        .ok_or(FakeDnsWireError::Capacity)?;
    let answers=u16::try_from(answer_count).map_err(|_|FakeDnsWireError::Capacity)?;
    let mut wire=header(id,answers,0);
    question(&mut wire,qname,1)?;
    // A response can be CNAME(qname→alias1) ... CNAME(aliasN→canonical).
    // TTL for each alias is conservatively <= the shortest actual A
    // candidate chain, even when CNAME TTL itself was longer.
    let minimum_ttl=ttl.iter().min().copied().unwrap_or(0);
    for (i,alias) in resolved.cname_chain.iter().enumerate(){
        let target=resolved.cname_chain.get(i+1)
            .map_or(resolved.canonical.as_str(),|s|s.as_str());
        if alias==target{return Err(FakeDnsWireError::InvalidCnameChain)}
        let mut name=Vec::new();
        encode_name(target,&mut name)?;
        push_rr(&mut wire,alias,5,minimum_ttl,&name)?;
    }
    for (i,&fake) in visible.iter().enumerate(){
        push_rr(&mut wire,&resolved.canonical,1,ttl[i],&fake.to_be_bytes())?;
    }
    Ok(FakeDnsWire{packet:wire,fakes:visible})
}
/// CN AAAA and HTTPS/SVCB only: deliberately empty answer to prevent
/// ipv6hint/ipv4hint escaping the local mapping. Non-CN RR behavior is
/// outside this function. rcode3 is permitted for upstream NXDOMAIN.
pub(crate) fn synthesize_cn_nodata(id:u16,qname:&str,qtype:u16,
    upstream_nxdomain:bool)->Result<Vec<u8>,FakeDnsWireError>{
    if !matches!(qtype,28|64|65) {
        return Err(FakeDnsWireError::NotCnAAnswer)
    }
    let mut packet=header(id,0,if upstream_nxdomain{3}else{0});
    question(&mut packet,qname,qtype)?;
    Ok(packet)
}
#[cfg(test)]
mod tests{
    use super::*;
    use crate::v4_client_dns_answer::ResolvedA;
    fn ip(a:u8,b:u8,c:u8,d:u8)->u32{u32::from_be_bytes([a,b,c,d])}
    fn allocator()->FakeAllocator{
        FakeAllocator::new(ip(198,18,0,1),ip(198,18,0,127),
            &[],8,1024*1024).unwrap()
    }
    fn resolved(real:u32)->DnsAResolution{
        DnsAResolution{status:DnsAnswerStatus::Answered,
            canonical:"shared.cdn.example".into(),
            cname_chain:vec!["www.cn.example".into()],
            candidates:vec![ResolvedA{address:real,ttl:180}]}
    }
    fn key(real:u32,qname:&str)->FakeKey{
        FakeKey{qname:qname.into(),canonical:"shared.cdn.example".into(),
            real4:real,policy_rev:11,resolver_rev:22}
    }
    #[test]
    fn plan029_cn_dns_wire_rejects_unpersisted_then_only_announced_fake_not_shared_cdn(){
        let real=ip(198,51,100,88);let mut pool=allocator();
        let p=pool.prepare(key(real,"www.cn.example"),180,1000).unwrap();
        assert_eq!(synthesize_cn_a(99,"www.cn.example",&resolved(real),
            &pool,11,22,1001),Err(FakeDnsWireError::MissingDurableMapping));
        let snapshot=pool.durable_candidate();
        assert_eq!(snapshot.len(),1);
        pool.acknowledge_durable(p.fake4).unwrap();
        let made=synthesize_cn_a(99,"www.cn.example",&resolved(real),
            &pool,11,22,1001).unwrap();
        assert_eq!(made.fakes,vec![p.fake4]);
        assert!(!made.packet.windows(4).any(|w|w==real.to_be_bytes()));
        assert!(made.packet.windows(4).any(|w|w==p.fake4.to_be_bytes()));
        assert_eq!(u16::from_be_bytes([made.packet[6],made.packet[7]]),2);
        assert_eq!(made.packet[3]&0x20,0); // DNSSEC AD cleared
        // Same overseas CDN IP used by a NON-CN name has no DNS remap;
        // even another CN hostname cannot claim this advertised fake.
        assert_eq!(synthesize_cn_a(100,"other.cn.example",
            &DnsAResolution{cname_chain:vec!["other.cn.example".into()],..resolved(real)},
            &pool,11,22,1002),Err(FakeDnsWireError::MissingDurableMapping));
        assert_eq!(synthesize_cn_a(101,"www.cn.example",&resolved(real),
            &pool,12,22,1002),Err(FakeDnsWireError::MissingDurableMapping));
    }
    #[test]
    fn plan029_cn_dns_wire_multi_a_ttl0_and_quarantine_real_hints_never_escape(){
        let mut pool=allocator();
        let mut a=resolved(ip(203,0,113,21));
        a.candidates.push(ResolvedA{address:ip(203,0,113,22),ttl:0});
        let mut fake=Vec::new();
        for r in &a.candidates{
            let p=pool.prepare(key(r.address,"www.cn.example"),r.ttl,4000).unwrap();
            pool.acknowledge_durable(p.fake4).unwrap();fake.push(p.fake4)
        }
        let response=synthesize_cn_a(42,"www.cn.example",&a,&pool,11,22,4000).unwrap();
        assert_eq!(response.fakes,fake);
        assert_eq!(u16::from_be_bytes([response.packet[6],response.packet[7]]),3);
        assert!(!response.packet.windows(4).any(|w|w==ip(203,0,113,21).to_be_bytes()));
        assert!(!response.packet.windows(4).any(|w|w==ip(203,0,113,22).to_be_bytes()));
        assert_eq!(pool.announced_real(fake[1]),Some(ip(203,0,113,22)));
        assert!(matches!(synthesize_cn_a(43,"www.cn.example",&a,&pool,11,22,4001),
            Err(FakeDnsWireError::MissingDurableMapping))); // TTL0 not refreshed silently
    }
    #[test]
    fn plan029_cn_dns_wire_aaaa_svcb_https_explicit_nodata_no_hint_leak(){
        for qtype in [28,64,65]{
            let resp=synthesize_cn_nodata(513,"www.cn.example",qtype,false).unwrap();
            assert_eq!(u16::from_be_bytes([resp[6],resp[7]]),0);
            assert_eq!(resp[3]&0xf,0);
            assert_eq!(resp[3]&0x20,0);
            let nx=synthesize_cn_nodata(514,"www.cn.example",qtype,true).unwrap();
            assert_eq!(nx[3]&0xf,3);
        }
        assert_eq!(synthesize_cn_nodata(1,"world.example",1,false),
            Err(FakeDnsWireError::NotCnAAnswer));
    }
}
