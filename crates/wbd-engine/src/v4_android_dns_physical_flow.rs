//! B2c2c original Android Rust M4 physical DNS UDP/53 packet ownership.
//! One connected, netd-bound physical UDP socket receives the original DNS
//! wire, not an untrusted IPv4 packet. This module owns only the bounded
//! synthetic DNS ID/real app IPv4 inverse mapping, not a second TUN reader.
//! The physical reply is NOT remote WBD AEAD-authenticated: its admission is
//! the actual bound OS UDP endpoint + exact original DNS QNAME/ID + one
//! original M4 generation. It must never use the remote-authenticated sink.

use crate::v4_android_dns_ingress::{observe_ipv4_dns53,Dns53Observation};

const CAP:usize=64;
const MAX_AGE_MS:u64=12_000;
const FIRST_DNS_ID:u16=0x7100;
pub(crate) const MAX_DNS_WIRE:usize=4096;
pub(crate) const MAX_DNS_REPLY_IPV4:usize=20+8+MAX_DNS_WIRE;

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) enum PhysicalDnsError{Malformed,Capacity,Unowned,Expired,QuestionMismatch}
#[derive(Clone,Copy)]
struct Original {
    local:[u8;4],resolver:[u8;4],source_port:u16,
    id:u16,qname_len:u16,qname:[u8;260],until_ms:u64,
}
pub(crate) struct PhysicalDnsUdpFlows{
    entries:[Option<Original>;CAP],
    next:usize,
}
impl Default for PhysicalDnsUdpFlows{
    fn default()->Self{Self{entries:[None;CAP],next:0}}
}
fn be16(b:&[u8])->u16{u16::from_be_bytes([b[0],b[1]])}
fn checksum(data:&[u8],initial:u32)->u16{
    let mut sum=initial;
    for chunk in data.chunks_exact(2){sum+=u32::from(be16(chunk))}
    if data.len()%2!=0{sum+=u32::from(data[data.len()-1])<<8}
    while sum>>16!=0{sum=(sum&65535)+(sum>>16)}
    !(sum as u16)
}
fn dns_question(wire:&[u8],response:bool)
    ->Result<(u16,u16,[u8;260]),PhysicalDnsError>{
    if !(17..=MAX_DNS_WIRE).contains(&wire.len()){
        return Err(PhysicalDnsError::Malformed)
    }
    let flags=be16(&wire[2..4]);
    if (flags&0x8000!=0)!=response||flags&0x7800!=0||
        be16(&wire[4..6])!=1{return Err(PhysicalDnsError::Malformed)}
    if !response&&
        (be16(&wire[6..8])!=0||be16(&wire[8..10])!=0||
         be16(&wire[10..12])>1){return Err(PhysicalDnsError::Malformed)}
    let mut name=[0u8;260];
    let mut at=12usize;
    let mut len=0usize;
    let mut labels=0usize;
    loop{
        let count=usize::from(*wire.get(at).ok_or(PhysicalDnsError::Malformed)?);
        at+=1;
        if count>63||len+count+1>255{
            return Err(PhysicalDnsError::Malformed)
        }
        name[len]=count as u8;
        len+=1;
        if count==0{break}
        if labels>=127{return Err(PhysicalDnsError::Malformed)}
        let bytes=wire.get(at..at+count).ok_or(PhysicalDnsError::Malformed)?;
        for byte in bytes{
            if !byte.is_ascii_alphanumeric()&&*byte!=b'-'&&*byte!=b'_'{
                return Err(PhysicalDnsError::Malformed)
            }
            name[len]=byte.to_ascii_lowercase();
            len+=1;
        }
        at+=count;
        labels+=1;
    }
    if labels==0{return Err(PhysicalDnsError::Malformed)}
    let suffix=wire.get(at..at+4).ok_or(PhysicalDnsError::Malformed)?;
    if be16(&suffix[0..2])==0||be16(&suffix[2..4])!=1{
        return Err(PhysicalDnsError::Malformed)
    }
    name[len..len+4].copy_from_slice(suffix);
    len+=4;
    Ok((be16(&wire[0..2]),len as u16,name))
}
fn eligible(packet:&[u8])->Result<(usize,usize),PhysicalDnsError>{
    if packet.len()<28+17||packet.len()>65535||
        packet[0]>>4!=4||packet[9]!=17{
        return Err(PhysicalDnsError::Malformed)
    }
    let ihl=usize::from(packet[0]&15)*4;
    if ihl<20||ihl>60||ihl+8+17>packet.len()||
        be16(&packet[2..4]) as usize!=packet.len()||
        be16(&packet[6..8])&0x3fff!=0||
        be16(&packet[ihl+4..ihl+6]) as usize!=packet.len()-ihl||
        be16(&packet[ihl+2..ihl+4])!=53||
        !matches!(observe_ipv4_dns53(packet,packet.len()),
            Dns53Observation::UdpQuestion{..}){
        return Err(PhysicalDnsError::Malformed)
    }
    let start=ihl+8;
    if packet.len()-start>MAX_DNS_WIRE{return Err(PhysicalDnsError::Malformed)}
    Ok((ihl,start))
}
impl PhysicalDnsUdpFlows{
    pub(crate) fn len(&self)->usize{
        self.entries.iter().filter(|x|x.is_some()).count()
    }
    pub(crate) fn stop(&mut self){
        self.entries.fill(None);
        self.next=0;
    }
    /// Prepare only a DNS wire question to send through the pre-bound
    /// physical socket; NEVER mutate the original TUN kernel packet.
    /// Original source/destination are held for one reverse IP reply.
    pub(crate) fn prepare(
        &mut self,packet:&[u8],wire:&mut [u8],now_ms:u64
    )->Result<(usize,u16),PhysicalDnsError>{
        let (ihl,start)=eligible(packet)?;
        if be16(&packet[ihl..ihl+2])==0||
           packet[12..16]==[0;4]||packet[16..20]==[0;4]||
           packet[12]>=224||packet[16]>=224||
           packet[12..16]==packet[16..20]{
            return Err(PhysicalDnsError::Malformed)
        }
        let dns=&packet[start..];
        if wire.len()<dns.len(){return Err(PhysicalDnsError::Malformed)}
        let (id,qname_len,qname)=dns_question(dns,false)?;
        let slot=(0..CAP).map(|v|(self.next+v)%CAP)
            .find(|&idx|self.entries[idx].is_none_or(
                |f|f.until_ms<=now_ms))
            .ok_or(PhysicalDnsError::Capacity)?;
        let synthetic=FIRST_DNS_ID+slot as u16;
        wire[..dns.len()].copy_from_slice(dns);
        wire[..2].copy_from_slice(&synthetic.to_be_bytes());
        self.entries[slot]=Some(Original{
            local:packet[12..16].try_into().unwrap(),
            resolver:packet[16..20].try_into().unwrap(),
            source_port:be16(&packet[ihl..ihl+2]),
            id,qname_len,qname,until_ms:now_ms.saturating_add(MAX_AGE_MS),
        });
        self.next=(slot+1)%CAP;
        Ok((dns.len(),synthetic))
    }
    /// Abort a failed kernel send. The original IP remains unmodified and
    /// may be retried by the application, not transparently via Tunnel DNS.
    pub(crate) fn cancel(&mut self,synthetic:u16){
        if let Some(idx)=synthetic.checked_sub(FIRST_DNS_ID).map(usize::from){
            if idx<CAP{self.entries[idx]=None}
        }
    }
    /// Exactly one OS UDP datagram from the physically connected socket.
    /// The caller must validate generation/physical scope before writing
    /// the resulting packet into the SAME owned TUN FD.
    pub(crate) fn receive(
        &mut self,wire:&[u8],packet:&mut [u8],now_ms:u64
    )->Result<usize,PhysicalDnsError>{
        let (id,len,qname)=dns_question(wire,true)?;
        let idx=usize::from(id.checked_sub(FIRST_DNS_ID).ok_or(
            PhysicalDnsError::Unowned)?);
        if idx>=CAP{return Err(PhysicalDnsError::Unowned)}
        let flow=self.entries[idx].ok_or(PhysicalDnsError::Unowned)?;
        if flow.until_ms<=now_ms{return Err(PhysicalDnsError::Expired)}
        if flow.qname_len!=len||
           flow.qname[..usize::from(len)]!=qname[..usize::from(len)]{
            return Err(PhysicalDnsError::QuestionMismatch)
        }
        let size=28+wire.len();
        if packet.len()<size||size>65535{return Err(PhysicalDnsError::Malformed)}
        let out=&mut packet[..size];
        out.fill(0);
        out[0]=0x45;
        out[2..4].copy_from_slice(&(size as u16).to_be_bytes());
        out[4..6].copy_from_slice(&id.to_be_bytes());
        out[6]=0x40;
        out[8]=64;
        out[9]=17;
        out[12..16].copy_from_slice(&flow.resolver);
        out[16..20].copy_from_slice(&flow.local);
        out[20..22].copy_from_slice(&53u16.to_be_bytes());
        out[22..24].copy_from_slice(&flow.source_port.to_be_bytes());
        out[24..26].copy_from_slice(&((size-20) as u16).to_be_bytes());
        out[28..size].copy_from_slice(wire);
        out[28..30].copy_from_slice(&flow.id.to_be_bytes());
        let ip_sum=checksum(&out[..20],0);
        out[10..12].copy_from_slice(&ip_sum.to_be_bytes());
        let mut pseudo=0u32;
        for pair in out[12..20].chunks_exact(2){pseudo+=u32::from(be16(pair))}
        pseudo+=17+(size-20) as u32;
        let mut udp_sum=checksum(&out[20..],pseudo);
        if udp_sum==0{udp_sum=0xffff}
        out[26..28].copy_from_slice(&udp_sum.to_be_bytes());
        self.entries[idx]=None;
        Ok(size)
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    fn make_query(id:u16)->Vec<u8>{
        let mut d=vec![0u8;12];d[..2].copy_from_slice(&id.to_be_bytes());
        d[2]=1;d[5]=1;
        d.extend_from_slice(&[3,b'w',b'b',b'd',7,b'e',b'x',b'a',b'm',b'p',b'l',b'e',0,0,1,0,1]);
        d
    }
    fn ip_query(dns:&[u8])->Vec<u8>{
        let mut p=vec![0u8;28+dns.len()];let n=p.len();
        p[0]=0x45;p[2..4].copy_from_slice(&(n as u16).to_be_bytes());
        p[8]=64;p[9]=17;p[12..16].copy_from_slice(&[10,66,0,2]);
        p[16..20].copy_from_slice(&[8,8,8,8]);
        p[20..22].copy_from_slice(&40001u16.to_be_bytes());
        p[22..24].copy_from_slice(&53u16.to_be_bytes());
        p[24..26].copy_from_slice(&((n-20) as u16).to_be_bytes());
        p[28..].copy_from_slice(dns);p
    }
    #[test]
    fn b2c2b3_physical_owned_ipv4_udp53_real_question_reply_checksum(){
        let original=ip_query(&make_query(0x1001));
        let mut flows=PhysicalDnsUdpFlows::default();
        let mut wire=[0u8;MAX_DNS_WIRE];
        let (n,id)=flows.prepare(&original,&mut wire,1).unwrap();
        assert_eq!(flows.len(),1);
        assert_eq!(&original[16..20],&[8,8,8,8]);
        assert_ne!(be16(&wire[..2]),0x1001);
        assert_eq!(be16(&wire[..2]),id);
        let mut response=wire[..n].to_vec();response[2]=0x81;response[3]=0x80;
        let mut ip=[0u8;MAX_DNS_REPLY_IPV4];
        let size=flows.receive(&response,&mut ip,2).unwrap();
        assert_eq!(&ip[12..16],&[8,8,8,8]);
        assert_eq!(&ip[16..20],&[10,66,0,2]);
        assert_eq!(&ip[22..24],&40001u16.to_be_bytes());
        assert_eq!(&ip[28..30],&0x1001u16.to_be_bytes());
        assert_eq!(checksum(&ip[..20],0),0);
        let mut pseudo=0u32;
        for part in ip[12..20].chunks_exact(2){pseudo+=u32::from(be16(part))}
        pseudo+=17+(size-20) as u32;
        assert_eq!(checksum(&ip[20..size],pseudo),0);
        assert_eq!(flows.len(),0);
    }
    #[test]
    fn b2c2b3_physical_no_cross_flow_no_unowned_reply_after_stop(){
        let p=ip_query(&make_query(0x1001));
        let mut flows=PhysicalDnsUdpFlows::default();
        let mut wire=[0u8;MAX_DNS_WIRE];
        let (n,id)=flows.prepare(&p,&mut wire,1).unwrap();
        let mut response=wire[..n].to_vec();response[2]=0x81;response[3]=0x80;
        let old=response[20];
        response[20]=if old==b'x'{b'y'}else{b'x'};
        let mut ip=[0u8;MAX_DNS_REPLY_IPV4];
        assert_eq!(flows.receive(&response,&mut ip,2),Err(PhysicalDnsError::QuestionMismatch));
        response[20]=old;
        assert_eq!(flows.receive(&response,&mut ip,12_001),Err(PhysicalDnsError::Expired));
        flows.cancel(id);
        assert_eq!(flows.len(),0);
        let (_,next)=flows.prepare(&p,&mut wire,2).unwrap();
        flows.stop();
        let mut okay=wire[..n].to_vec();okay[2]=0x81;okay[3]=0x80;
        assert_eq!(flows.receive(&okay,&mut ip,3),Err(PhysicalDnsError::Unowned));
        assert_eq!(flows.len(),0);
        assert_ne!(next,0);
    }
}
