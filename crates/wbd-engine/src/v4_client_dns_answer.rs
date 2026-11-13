//! PLAN029 upstream DNS reply validation and CNAME-constrained A extraction.
//! This is cold/sparse DNS-work only: not a Wintun packet path or product
//! resolver. It does not lookup reverse real CDN IP→domain and never learns
//! addresses from unrelated additional/authority sections.
//! A real bounded async dispatcher must validate the physical/tunnel source
//! socket and original query ticket BEFORE calling this parser.
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) enum DnsReplyError{
    Short,NotResponse,QuestionMismatch,MalformedName,
    BadRecord,ConflictingCname,CnameCycle,TooManyRecords,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) enum DnsAnswerStatus{Answered,NoData,NxDomain,Truncated,UpstreamError}
#[derive(Clone,Debug,Eq,PartialEq)]
pub(crate) struct ResolvedA {
    pub address:u32,
    /// Minimum TTL across all CNAME hops and this real A record.
    pub ttl:u32,
}
#[derive(Clone,Debug,Eq,PartialEq)]
pub(crate) struct DnsAResolution{
    pub status:DnsAnswerStatus,
    pub canonical:String,
    pub cname_chain:Vec<String>,
    pub candidates:Vec<ResolvedA>,
}
#[derive(Clone,Debug)]
struct Rr{
    owner:String,
    kind:u16,
    ttl:u32,
    rdata_start:usize,
    rdata_end:usize,
}
fn u16be(d:&[u8])->u16{u16::from_be_bytes([d[0],d[1]])}
fn u32be(d:&[u8])->u32{u32::from_be_bytes([d[0],d[1],d[2],d[3]])}
/// RFC1035 pointer bounds/hop limiting; no copies of pointer targets into
/// the packet; refuse forward/self cycles and malformed labels.
fn read_name(packet:&[u8],pos:usize)->Result<(String,usize),DnsReplyError>{
    if pos>=packet.len(){return Err(DnsReplyError::MalformedName)}
    let mut cursor=pos;
    let mut end=None;
    let mut jumps=0usize;
    let mut total=0usize;
    let mut name=String::new();
    loop{
        let b=*packet.get(cursor).ok_or(DnsReplyError::MalformedName)?;
        if b&0xc0==0xc0{
            let second=*packet.get(cursor+1).ok_or(DnsReplyError::MalformedName)?;
            let target=(usize::from(b&0x3f)<<8)|usize::from(second);
            if target>=cursor||target>=packet.len()||jumps>=16{
                return Err(DnsReplyError::MalformedName)
            }
            if end.is_none(){end=Some(cursor+2)}
            cursor=target;jumps+=1;continue
        }
        if b&0xc0!=0{return Err(DnsReplyError::MalformedName)}
        cursor+=1;
        if b==0{
            let consumed=end.unwrap_or(cursor);
            if name.is_empty(){return Err(DnsReplyError::MalformedName)}
            return Ok((name,consumed))
        }
        let size=b as usize;
        if size>63||cursor+size>packet.len()||total+size+1>253{
            return Err(DnsReplyError::MalformedName)
        }
        let label=&packet[cursor..cursor+size];
        if !label.iter().all(|x|x.is_ascii_graphic() && *x!=b'.' && *x!=b'\\'){
            return Err(DnsReplyError::MalformedName)
        }
        if !name.is_empty(){name.push('.')}
        for b in label{name.push((*b as char).to_ascii_lowercase())}
        total+=size+1;cursor+=size;
    }
}
fn question(packet:&[u8])->Result<(String,u16,u16,usize),DnsReplyError>{
    let (name,pos)=read_name(packet,12)?;
    if pos+4>packet.len(){return Err(DnsReplyError::Short)}
    Ok((name,u16be(&packet[pos..pos+2]),u16be(&packet[pos+2..pos+4]),pos+4))
}
/// Parse a response bound to one original query ID, QNAME, QTYPE and QCLASS.
/// No transport fallback, egress decision or FakeIP allocation happens here.
pub(crate) fn extract_a(packet:&[u8],id:u16,expected_name:&str,query_type:u16)
    ->Result<DnsAResolution,DnsReplyError>{
    if packet.len()<12{return Err(DnsReplyError::Short)}
    let header_id=u16be(&packet[0..2]);
    let flags=u16be(&packet[2..4]);
    if flags&0x8000==0||flags&0x7800!=0{
        return Err(DnsReplyError::NotResponse)
    }
    if header_id!=id||u16be(&packet[4..6])!=1{
        return Err(DnsReplyError::QuestionMismatch)
    }
    let (name,typ,class,mut pos)=question(packet)?;
    if !name.eq_ignore_ascii_case(expected_name.trim_end_matches('.'))||
        typ!=query_type||class!=1{
        return Err(DnsReplyError::QuestionMismatch)
    }
    let base=||DnsAResolution{
        status:DnsAnswerStatus::NoData,
        canonical:name.clone(),
        cname_chain:Vec::new(),
        candidates:Vec::new(),
    };
    if flags&0x0200!=0{return Ok(DnsAResolution{
        status:DnsAnswerStatus::Truncated,..base()
    })}
    let rcode=flags&0x000f;
    if rcode==3{return Ok(DnsAResolution{status:DnsAnswerStatus::NxDomain,..base()})}
    if rcode!=0{return Ok(DnsAResolution{status:DnsAnswerStatus::UpstreamError,..base()})}
    // Only the answer section may contribute addresses; the additional
    // section cannot pollute the shared-CDN decision, even with valid A.
    let count=usize::from(u16be(&packet[6..8]));
    if count>128{return Err(DnsReplyError::TooManyRecords)}
    let mut answers=Vec::with_capacity(count.min(16));
    for _ in 0..count{
        let (owner,after_name)=read_name(packet,pos)?;
        pos=after_name;
        if pos+10>packet.len(){return Err(DnsReplyError::BadRecord)}
        let kind=u16be(&packet[pos..pos+2]);
        let class=u16be(&packet[pos+2..pos+4]);
        let ttl=u32be(&packet[pos+4..pos+8]);
        let size=usize::from(u16be(&packet[pos+8..pos+10]));
        let start=pos+10;
        let end=start.checked_add(size).ok_or(DnsReplyError::BadRecord)?;
        if end>packet.len(){return Err(DnsReplyError::BadRecord)}
        if class==1&&(kind==1||kind==5){
            if kind==1&&size!=4{return Err(DnsReplyError::BadRecord)}
            answers.push(Rr{owner,kind,ttl,rdata_start:start,rdata_end:end});
        }
        pos=end;
    }
    // CN qtype AAAA/SVCB/HTTPS is answered locally with NODATA by its
    // dispatcher; no fake address can be created from address hints.
    if query_type!=1{return Ok(base())}
    let mut current=name.clone();
    let mut chain=Vec::<String>::new();
    let mut min_ttl=u32::MAX;
    for _ in 0..=8 {
        let aliases=answers.iter().filter(|rr|rr.kind==5&&rr.owner==current)
            .collect::<Vec<_>>();
        if aliases.is_empty(){break}
        if aliases.len()!=1{return Err(DnsReplyError::ConflictingCname)}
        let rr=aliases[0];
        let (target,end)=read_name(packet,rr.rdata_start)?;
        if end!=rr.rdata_end{return Err(DnsReplyError::BadRecord)}
        if target==current||chain.iter().any(|s|s==&target){
            return Err(DnsReplyError::CnameCycle)
        }
        min_ttl=min_ttl.min(rr.ttl);
        chain.push(current);
        current=target;
        if chain.len()>8{return Err(DnsReplyError::TooManyRecords)}
    }
    let mut unique=Vec::new();
    for rr in answers.iter().filter(|rr|rr.kind==1&&rr.owner==current){
        let real=u32be(&packet[rr.rdata_start..rr.rdata_end]);
        if real==0||real==u32::MAX{continue}
        if !unique.iter().any(|a:&ResolvedA|a.address==real){
            if unique.len()>=16{return Err(DnsReplyError::TooManyRecords)}
            unique.push(ResolvedA{address:real,ttl:min_ttl.min(rr.ttl)});
        }
    }
    let status=if unique.is_empty(){DnsAnswerStatus::NoData}else{DnsAnswerStatus::Answered};
    Ok(DnsAResolution{status,canonical:current,cname_chain:chain,candidates:unique})
}
#[cfg(test)]
mod tests{
    use super::*;
    fn name(text:&str)->Vec<u8>{
        let mut v=Vec::new();
        for label in text.split('.'){v.push(label.len() as u8);v.extend_from_slice(label.as_bytes())}
        v.push(0);v
    }
    fn query(name_str:&str,kind:u16)->Vec<u8>{
        let mut v=vec![0u8;12];
        v[0..2].copy_from_slice(&0x1234u16.to_be_bytes());
        v[2..4].copy_from_slice(&0x8180u16.to_be_bytes());
        v[4..6].copy_from_slice(&1u16.to_be_bytes());
        v.extend(name(name_str));
        v.extend_from_slice(&kind.to_be_bytes());
        v.extend_from_slice(&1u16.to_be_bytes());v
    }
    fn record(out:&mut Vec<u8>,owner:&[u8],kind:u16,ttl:u32,body:&[u8]){
        out.extend_from_slice(owner);
        out.extend_from_slice(&kind.to_be_bytes());
        out.extend_from_slice(&1u16.to_be_bytes());
        out.extend_from_slice(&ttl.to_be_bytes());
        out.extend_from_slice(&(body.len() as u16).to_be_bytes());
        out.extend_from_slice(body);
    }
    #[test]
    fn plan029_dns_answer_real_cn_cname_compressed_alias_two_a_min_ttl_no_additional_pollution(){
        let mut d=query("www.cn.example",1);
        d[6..8].copy_from_slice(&3u16.to_be_bytes());
        d[10..12].copy_from_slice(&1u16.to_be_bytes());
        // pointer to original www.cn.example at offset12.
        record(&mut d,&[0xc0,12],5,40,&name("edge.cdn.example"));
        record(&mut d,&name("edge.cdn.example"),1,300,&[198,51,100,30]);
        record(&mut d,&name("edge.cdn.example"),1,20,&[198,51,100,31]);
        // This A record is in ADDITIONAL only and must NOT enter CN mapping.
        record(&mut d,&name("attacker.other.example"),1,9999,&[203,0,113,5]);
        let a=extract_a(&d,0x1234,"www.cn.example",1).unwrap();
        assert_eq!(a.status,DnsAnswerStatus::Answered);
        assert_eq!(a.canonical,"edge.cdn.example");
        assert_eq!(a.cname_chain,vec!["www.cn.example"]);
        assert_eq!(a.candidates,vec![
            ResolvedA{address:u32::from_be_bytes([198,51,100,30]),ttl:40},
            ResolvedA{address:u32::from_be_bytes([198,51,100,31]),ttl:20},
        ]);
    }
    #[test]
    fn plan029_dns_answer_no_other_qname_or_id_cdn_learned(){
        let mut d=query("world.example",1);
        d[6..8].copy_from_slice(&1u16.to_be_bytes());
        record(&mut d,&name("unrelated.other"),1,60,&[203,0,113,9]);
        assert_eq!(extract_a(&d,0x1234,"world.example",1).unwrap().status,
            DnsAnswerStatus::NoData);
        assert_eq!(extract_a(&d,0x1235,"world.example",1),
            Err(DnsReplyError::QuestionMismatch));
        assert_eq!(extract_a(&d,0x1234,"wrong.cn",1),
            Err(DnsReplyError::QuestionMismatch));
    }
    #[test]
    fn plan029_dns_answer_nxdomain_truncated_aaaa_https_nodata_no_fake(){
        let mut d=query("cn.example",1);
        d[2..4].copy_from_slice(&0x8183u16.to_be_bytes());
        assert_eq!(extract_a(&d,0x1234,"cn.example",1).unwrap().status,
            DnsAnswerStatus::NxDomain);
        d[2..4].copy_from_slice(&0x8380u16.to_be_bytes());
        assert_eq!(extract_a(&d,0x1234,"cn.example",1).unwrap().status,
            DnsAnswerStatus::Truncated);
        for kind in [28,64,65]{
            let mut answer=query("cn.example",kind);
            answer[6..8].copy_from_slice(&1u16.to_be_bytes());
            record(&mut answer,&name("cn.example"),1,90,&[1,2,3,4]);
            assert_eq!(extract_a(&answer,0x1234,"cn.example",kind).unwrap().status,
                DnsAnswerStatus::NoData);
        }
    }
    #[test]
    fn plan029_dns_answer_compressed_pointer_cycles_reject_and_no_unrelated_additional(){
        let mut d=query("cn.example",1);
        d[6..8].copy_from_slice(&1u16.to_be_bytes());
        let start=d.len();
        // Illegal self-pointer, never recurse indefinitely or trust source.
        record(&mut d,&[0xc0,((start+1)&255) as u8],1,20,&[1,2,3,4]);
        assert_eq!(extract_a(&d,0x1234,"cn.example",1),
            Err(DnsReplyError::MalformedName));
    }
}
