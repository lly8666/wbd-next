//! B2c2b1: bounded original-Rust Tunnel DNS UDP/53 transaction NAT.
//! Source-only *candidate* for the existing Android M4 owner; not armed.
//! In particular, no physical/Ndk socket, DNS listener or second TUN fd.
//! The live original M1/M3 packets remain unchanged until a separate
//! authenticated RX inverse-map + Stop, CN policy and netd admission gate.
use crate::v4_android_dns_ingress::{
    observe_ipv4_dns53,Dns53Observation,
};

const TUNNEL_DNS:[u8;4]=[1,1,1,1];
const CAP:usize=64;
const FIRST_PORT:u16=50_000;
const MAX_AGE_MS:u64=12_000;
const QUESTION_MAX:usize=260;

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) enum FlowError { Malformed,Capacity,Unowned,Expired,QuestionMismatch }
#[derive(Clone,Copy,Debug)]
struct Question { len:u16, bytes:[u8;QUESTION_MAX], txid:u16 }
impl Question {
    fn same(&self,other:&Self)->bool{
        self.len==other.len&&self.txid==other.txid&&
        self.bytes[..usize::from(self.len)]==other.bytes[..usize::from(other.len)]
    }
}
#[derive(Clone,Copy,Debug)]
struct Flow {
    local:[u8;4],original_server:[u8;4],original_port:u16,
    question:Question,expiry_ms:u64,
}
/// Bounded to 64 outstanding original application DNS questions. The
/// translated source port is owned exclusively by the corresponding slot.
/// A generation Stop simply drops this fixed stack/owner allocation.
pub(crate) struct TunnelDnsUdpFlows {
    slots:[Option<Flow>;CAP],
    next:usize,
}
impl Default for TunnelDnsUdpFlows {
    fn default()->Self{Self{slots:[None;CAP],next:0}}
}
fn be16(b:&[u8])->u16{u16::from_be_bytes([b[0],b[1]])}
fn sum_words(data:&[u8],sum:&mut u32){
    for chunk in data.chunks_exact(2){
        *sum+=u32::from(be16(chunk));
    }
    if data.len()%2!=0{*sum+=u32::from(data[data.len()-1])<<8}
}
fn finish(mut n:u32)->u16{
    while n>>16!=0{n=(n&0xffff)+(n>>16)}
    !(n as u16)
}
fn set_checksums(packet:&mut [u8],ihl:usize){
    packet[10..12].copy_from_slice(&0u16.to_be_bytes());
    let mut header=0u32;
    sum_words(&packet[..ihl],&mut header);
    packet[10..12].copy_from_slice(&finish(header).to_be_bytes());
    packet[ihl+6..ihl+8].copy_from_slice(&0u16.to_be_bytes());
    let udp_len=packet.len()-ihl;
    let mut udp=0u32;
    sum_words(&packet[12..20],&mut udp); // 4-byte source + 4-byte dest
    udp+=17+udp_len as u32;
    sum_words(&packet[ihl..],&mut udp);
    let mut check=finish(udp);
    if check==0{check=0xffff} // UDP zero means checksum omitted
    packet[ihl+6..ihl+8].copy_from_slice(&check.to_be_bytes());
}
// Return an exact complete IPv4 UDP datagram with no fragment, no hidden
// bytes, no undefined option length and no incompatible UDP length.
fn udp_ipv4(packet:&[u8])->Result<usize,FlowError>{
    if packet.len()<20+8+12||packet.len()>65535||
       packet[0]>>4!=4||packet[9]!=17{return Err(FlowError::Malformed)}
    let ihl=usize::from(packet[0]&15)*4;
    if ihl<20||ihl>60||ihl+8+12>packet.len()||
       be16(&packet[2..4]) as usize!=packet.len()||
       be16(&packet[6..8])&0x3fff!=0||
       be16(&packet[ihl+4..ihl+6]) as usize!=packet.len()-ihl{
        return Err(FlowError::Malformed)
    }
    Ok(ihl)
}
// A canonical original QNAME/QTYPE/QCLASS, case-insensitive only for
// ASCII DNS label bytes. No compressed question, no heap, no FakeIP.
fn question(dns:&[u8],response:bool)->Result<Question,FlowError>{
    if dns.len()<17||dns.len()>4096{return Err(FlowError::Malformed)}
    let flags=be16(&dns[2..4]);
    if (flags&0x8000!=0)!=response||flags&0x7800!=0||
       be16(&dns[4..6])!=1{return Err(FlowError::Malformed)}
    if !response&&
       (be16(&dns[6..8])!=0||be16(&dns[8..10])!=0||
        be16(&dns[10..12])>1){return Err(FlowError::Malformed)}
    let mut bytes=[0u8;QUESTION_MAX];
    let mut p=12usize;
    let mut out=0usize;
    let mut labels=0usize;
    loop{
        let n=usize::from(*dns.get(p).ok_or(FlowError::Malformed)?);
        p+=1;
        if n>63||out+n+1>QUESTION_MAX{return Err(FlowError::Malformed)}
        bytes[out]=n as u8;
        out+=1;
        if n==0{break}
        if labels>=127{return Err(FlowError::Malformed)}
        let label=dns.get(p..p+n).ok_or(FlowError::Malformed)?;
        for &byte in label{
            if !byte.is_ascii_alphanumeric()&&byte!=b'-'&&byte!=b'_'{
                return Err(FlowError::Malformed)
            }
            bytes[out]=byte.to_ascii_lowercase();
            out+=1;
        }
        p+=n;
        labels+=1;
    }
    if labels==0||out>255{return Err(FlowError::Malformed)}
    let suffix=dns.get(p..p+4).ok_or(FlowError::Malformed)?;
    if be16(&suffix[0..2])==0||be16(&suffix[2..4])!=1{
        return Err(FlowError::Malformed)
    }
    bytes[out..out+4].copy_from_slice(suffix);
    out+=4;
    Ok(Question{
        len:out as u16,bytes,txid:be16(&dns[..2]),
    })
}
impl TunnelDnsUdpFlows {
    pub(crate) fn len(&self)->usize{
        self.slots.iter().filter(|x|x.is_some()).count()
    }
    pub(crate) fn stop(&mut self){
        self.slots.fill(None);
        self.next=0;
    }
    /// Prepare a nonfragmented client question for the authenticated
    /// 1.1.1.1:53 tunnel without any OS resolver/socket interaction.
    /// On ANY failure, packet bytes and flow state remain unchanged.
    /// The returned packet is only a candidate for the original M1 seal;
    /// DO NOT invoke from live M4 until the inverse RX owner is admitted.
    pub(crate) fn rewrite_query(
        &mut self,packet:&mut [u8],now_ms:u64
    )->Result<(),FlowError>{
        let ihl=udp_ipv4(packet)?;
        if !matches!(observe_ipv4_dns53(packet,packet.len()),
            Dns53Observation::UdpQuestion{..}){
            return Err(FlowError::Malformed)
        }
        let q=question(&packet[ihl+8..],false)?;
        let local:[u8;4]=packet[12..16].try_into().map_err(|_|FlowError::Malformed)?;
        let server:[u8;4]=packet[16..20].try_into().map_err(|_|FlowError::Malformed)?;
        if local==[0;4]||server==[0;4]||server[0]>=224||
           local[0]>=224||local==server{
            return Err(FlowError::Malformed)
        }
        let port=be16(&packet[ihl..ihl+2]);
        if port==0{return Err(FlowError::Malformed)}
        // Reuse a safe retransmit's same synthetic port; an unrelated
        // transaction can NEVER steal a live 5-tuple's reply slot.
        let identical=self.slots.iter().position(|entry|entry.is_some_and(|f|
            f.expiry_ms>now_ms&&f.local==local&&f.original_server==server&&
            f.original_port==port&&f.question.same(&q)));
        let free=identical.or_else(||(0..CAP).map(|n|(self.next+n)%CAP)
            .find(|&n|self.slots[n].is_none_or(|f|f.expiry_ms<=now_ms)))
            .ok_or(FlowError::Capacity)?;
        let expiry=now_ms.saturating_add(MAX_AGE_MS);
        // All validation and capacity checks precede the first mutation.
        packet[16..20].copy_from_slice(&TUNNEL_DNS);
        packet[ihl..ihl+2].copy_from_slice(&(FIRST_PORT+free as u16).to_be_bytes());
        set_checksums(packet,ihl);
        self.slots[free]=Some(Flow{
            local,original_server:server,original_port:port,
            question:q,expiry_ms:expiry,
        });
        self.next=(free+1)%CAP;
        Ok(())
    }
    /// Only a genuine original-M4 AEAD/replay-accepted IP reply to a
    /// leased client may call this. A missing/expired or mismatched DNS
    /// reply MUST NOT be delivered as a fabricated original resolver.
    /// On failure packet and map remain untouched; success consumes slot.
    pub(crate) fn rewrite_reply(
        &mut self,packet:&mut [u8],now_ms:u64
    )->Result<(),FlowError>{
        let ihl=udp_ipv4(packet)?;
        if packet[12..16]!=TUNNEL_DNS||
           be16(&packet[ihl..ihl+2])!=53{return Err(FlowError::Unowned)}
        let dest:[u8;4]=packet[16..20].try_into().map_err(|_|FlowError::Malformed)?;
        let port=be16(&packet[ihl+2..ihl+4]);
        let idx=usize::from(port.saturating_sub(FIRST_PORT));
        if port<FIRST_PORT||idx>=CAP{return Err(FlowError::Unowned)}
        let flow=self.slots[idx].ok_or(FlowError::Unowned)?;
        if flow.expiry_ms<=now_ms{return Err(FlowError::Expired)}
        if flow.local!=dest{return Err(FlowError::Unowned)}
        let q=question(&packet[ihl+8..],true)?;
        if !flow.question.same(&q){return Err(FlowError::QuestionMismatch)}
        packet[12..16].copy_from_slice(&flow.original_server);
        packet[ihl+2..ihl+4].copy_from_slice(&flow.original_port.to_be_bytes());
        set_checksums(packet,ihl);
        self.slots[idx]=None;
        Ok(())
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn dns_query(name:&str,id:u16)->Vec<u8>{
        let mut q=vec![0u8;12];
        q[0..2].copy_from_slice(&id.to_be_bytes());
        q[2]=1;q[5]=1;
        for label in name.split('.'){
            q.push(label.len() as u8);
            q.extend_from_slice(label.as_bytes());
        }
        q.extend_from_slice(&[0,0,1,0,1]);
        q
    }
    fn packet(query:&[u8],src:[u8;4],dest:[u8;4],src_port:u16,dst_port:u16)->Vec<u8>{
        let total=20+8+query.len();
        let mut p=vec![0u8;total];
        p[0]=0x45;
        p[2..4].copy_from_slice(&(total as u16).to_be_bytes());
        p[8]=64;p[9]=17;
        p[12..16].copy_from_slice(&src);
        p[16..20].copy_from_slice(&dest);
        p[20..22].copy_from_slice(&src_port.to_be_bytes());
        p[22..24].copy_from_slice(&dst_port.to_be_bytes());
        p[24..26].copy_from_slice(&((8+query.len()) as u16).to_be_bytes());
        p[28..].copy_from_slice(query);
        set_checksums(&mut p,20);
        p
    }
    fn good_checksums(p:&[u8])->bool{
        let ihl=udp_ipv4(p).unwrap();
        let mut ip=0u32;
        sum_words(&p[..ihl],&mut ip);
        if finish(ip)!=0{return false}
        let mut udp=0u32;
        sum_words(&p[12..20],&mut udp);
        udp+=17+(p.len()-ihl) as u32;
        sum_words(&p[ihl..],&mut udp);
        finish(udp)==0
    }
    fn reply_for(translated:&[u8],answer_name:&str)->Vec<u8>{
        let mut d=dns_query(answer_name,be16(&translated[28..30]));
        d[2]=0x81;d[3]=0x80; // QR=1, recursion requested/available
        packet(&d,TUNNEL_DNS,translated[12..16].try_into().unwrap(),
            53,be16(&translated[20..22]))
    }
    #[test]
    fn b2c2b1_rust_udp53_tunnel_real_ipv4_packet_pair_inverse_and_checksums(){
        let mut t=TunnelDnsUdpFlows::default();
        let origin=[10,0,0,7];
        let server=[8,8,4,4];
        let mut req=packet(&dns_query("www.Example.org",0x91b2),
            origin,server,41555,53);
        assert!(good_checksums(&req));
        t.rewrite_query(&mut req,4).unwrap();
        assert_eq!(&req[16..20],&TUNNEL_DNS);
        assert_eq!(&req[20..22],&FIRST_PORT.to_be_bytes());
        assert!(good_checksums(&req));
        let mut answer=reply_for(&req,"www.example.ORG");
        t.rewrite_reply(&mut answer,5).unwrap();
        assert_eq!(&answer[12..16],&server);
        assert_eq!(&answer[16..20],&origin);
        assert_eq!(&answer[22..24],&41555u16.to_be_bytes());
        assert!(good_checksums(&answer));
        assert_eq!(t.len(),0);
    }
    #[test]
    fn b2c2b1_rust_udp53_rejects_wrong_upstream_id_qname_and_replay(){
        let mut t=TunnelDnsUdpFlows::default();
        let mut req=packet(&dns_query("baidu.com",0x10),
            [10,0,0,3],[9,9,9,9],41234,53);
        t.rewrite_query(&mut req,1).unwrap();
        let mut bad_id=reply_for(&req,"baidu.com");
        bad_id[29]^=1;set_checksums(&mut bad_id,20);
        let before=bad_id.clone();
        assert_eq!(t.rewrite_reply(&mut bad_id,2),Err(FlowError::QuestionMismatch));
        assert_eq!(bad_id,before);
        let mut spoof=reply_for(&req,"evil.com");
        assert_eq!(t.rewrite_reply(&mut spoof,2),Err(FlowError::QuestionMismatch));
        let mut response=reply_for(&req,"baidu.com");
        response[12]=2;
        assert_eq!(t.rewrite_reply(&mut response,2),Err(FlowError::Unowned));
        let mut okay=reply_for(&req,"baidu.com");
        t.rewrite_reply(&mut okay,2).unwrap();
        assert_eq!(t.rewrite_reply(&mut okay,3),Err(FlowError::Unowned));
    }
    #[test]
    fn b2c2b1_rust_udp53_owner_has_exact_bounded_capacity_and_stop(){
        let mut t=TunnelDnsUdpFlows::default();
        let mut arr=Vec::new();
        for k in 0..CAP{
            let mut req=packet(&dns_query("www.qq.com",k as u16),
                [10,0,0,7],[8,8,8,8],40000+k as u16,53);
            t.rewrite_query(&mut req,1).unwrap();
            arr.push(req);
        }
        assert_eq!(t.len(),64);
        let mut extra=packet(&dns_query("www.qq.com",0xbeef),
            [10,0,0,7],[8,8,8,8],45000,53);
        let before=extra.clone();
        assert_eq!(t.rewrite_query(&mut extra,1),Err(FlowError::Capacity));
        assert_eq!(extra,before);
        assert_eq!(t.len(),64);
        let mut retransmit=packet(&dns_query("www.qq.com",0),
            [10,0,0,7],[8,8,8,8],40000,53);
        t.rewrite_query(&mut retransmit,2).unwrap();
        assert_eq!(&retransmit[20..22],&FIRST_PORT.to_be_bytes());
        assert_eq!(t.len(),64);
        let mut too_late=reply_for(&arr[0],"www.qq.com");
        assert_eq!(t.rewrite_reply(&mut too_late,MAX_AGE_MS+2),
            Err(FlowError::Expired));
        t.stop();
        assert_eq!(t.len(),0);
        assert_eq!(t.rewrite_reply(&mut too_late,3),Err(FlowError::Unowned));
    }
    #[test]
    fn b2c2b1_rust_udp53_rejects_fragments_and_malformed_without_packet_mutation(){
        let mut table=TunnelDnsUdpFlows::default();
        let req=packet(&dns_query("www.qq.com",17),
            [10,0,0,4],[223,5,5,5],44555,53);
        for tamper in 0..6{
            let mut p=req.clone();
            match tamper{
                0=>p[6]=0x20, // first fragment flag
                1=>p[7]=1, // nonfirst fragment
                2=>p[25]=0, // corrupt actual nonzero UDP length LOW byte
                3=>p[23]=54, // wrong target port
                4=>p[32]=2, // QR=1 response, not question
                _=>p[0]=0x60, // not IPv4
            }
            let saved=p.clone();
            assert_eq!(table.rewrite_query(&mut p,1),Err(FlowError::Malformed));
            assert_eq!(p,saved);
        }
        assert_eq!(table.len(),0);
    }
}
