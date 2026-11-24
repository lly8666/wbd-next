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
    serial:u64,udp_cap:usize,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) struct TcpFallbackTicket{id:u16,serial:u64}
pub(crate) struct PhysicalDnsUdpFlows{
    entries:[Option<Original>;CAP],
    questions:[Option<Vec<u8>>;CAP],
    next:usize,serial:u64,
}
impl Default for PhysicalDnsUdpFlows{
    fn default()->Self{Self{entries:[None;CAP],
        questions:std::array::from_fn(|_|None),next:0,serial:0}}
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
        self.questions.iter_mut().for_each(|q|*q=None);
        self.next=0;
    }
    /// Prepare only a DNS wire question to send through the pre-bound
    /// physical socket; NEVER mutate the original TUN kernel packet.
    /// Original source/destination are held for one reverse IP reply.
    pub(crate) fn prepare(
        &mut self,packet:&[u8],wire:&mut [u8],now_ms:u64
    )->Result<(usize,u16,bool),PhysicalDnsError>{
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
        let source_port=be16(&packet[ihl..ihl+2]);
        let local:[u8;4]=packet[12..16].try_into().unwrap();
        let resolver:[u8;4]=packet[16..20].try_into().unwrap();
        // B7: a real application's retry of one still-live DNS question
        // reuses its original synthetic ID and 64-slot owner entry.
        // Different app sockets/resolvers/questions never share a reply.
        let identical=self.entries.iter().position(|entry|entry.is_some_and(|f|
            f.until_ms>now_ms&&f.local==local&&
            f.resolver==resolver&&f.source_port==source_port&&
            f.id==id&&f.qname_len==qname_len&&
            f.qname[..usize::from(qname_len)]==qname[..usize::from(qname_len)]));
        let (slot,new_slot)=if let Some(idx)=identical{
            (idx,false)
        }else{
            let idx=(0..CAP).map(|v|(self.next+v)%CAP)
                .find(|&idx|self.entries[idx].is_none_or(
                    |f|f.until_ms<=now_ms))
                .ok_or(PhysicalDnsError::Capacity)?;
            (idx,true)
        };
        let synthetic=FIRST_DNS_ID+slot as u16;
        wire[..dns.len()].copy_from_slice(dns);
        wire[..2].copy_from_slice(&synthetic.to_be_bytes());
        // The validated ingress grammar admits either no OPT or one
        // complete EDNS OPT. Respect the App's advertised UDP answer size.
        let udp_cap=if be16(&dns[10..12])==1{
            let end=12+usize::from(qname_len);
            usize::from(be16(&dns[end+3..end+5])).clamp(512,MAX_DNS_WIRE)
        }else{512};
        if new_slot{
            self.serial=self.serial.wrapping_add(1);
            self.entries[slot]=Some(Original{
                local,resolver,source_port,id,qname_len,qname,
                until_ms:now_ms.saturating_add(MAX_AGE_MS),
                serial:self.serial,udp_cap,
            });
            self.next=(slot+1)%CAP;
        }else if let Some(flow)=self.entries[slot].as_mut(){flow.udp_cap=udp_cap;}
        // Only physical DNS questions need this original-wire snapshot.
        // An identical App retransmit does not allocate another buffer.
        if self.questions[slot].as_deref()!=Some(&wire[..dns.len()]){
            self.questions[slot]=Some(wire[..dns.len()].to_vec());
        }
        // A failed retransmit must NOT erase the still-valid earlier
        // outbound request. The owner cancels only a newly reserved slot.
        Ok((dns.len(),synthetic,new_slot))
    }
    /// Abort a failed kernel send. The original IP remains unmodified and
    /// may be retried by the application, not transparently via Tunnel DNS.
    pub(crate) fn cancel(&mut self,synthetic:u16){
        if let Some(idx)=synthetic.checked_sub(FIRST_DNS_ID).map(usize::from){
            if idx<CAP{self.entries[idx]=None;self.questions[idx]=None}
        }
    }
    fn matching_reply(&self,wire:&[u8],now_ms:u64)
        ->Result<(usize,Original),PhysicalDnsError>{
        let (id,len,qname)=dns_question(wire,true)?;
        let idx=usize::from(id.checked_sub(FIRST_DNS_ID).ok_or(PhysicalDnsError::Unowned)?);
        if idx>=CAP{return Err(PhysicalDnsError::Unowned)}
        let flow=self.entries[idx].ok_or(PhysicalDnsError::Unowned)?;
        if flow.until_ms<=now_ms{return Err(PhysicalDnsError::Expired)}
        if flow.qname_len!=len||
           flow.qname[..usize::from(len)]!=qname[..usize::from(len)]{
            return Err(PhysicalDnsError::QuestionMismatch)
        }
        Ok((idx,flow))
    }
    // B63: a real TC reply can replay ONLY its original question on
    // the same selected physical TCP endpoint, while the original UDP
    // transaction remains owned. No destination/QNAME policy change.
    pub(crate) fn fallback_question(&self,wire:&[u8],now_ms:u64)
        ->Option<(TcpFallbackTicket,&[u8])>{
        if wire.get(2).is_none_or(|flags|flags&2==0){return None}
        let (idx,flow)=self.matching_reply(wire,now_ms).ok()?;
        Some((TcpFallbackTicket{id:be16(&wire[..2]),serial:flow.serial},
            self.questions[idx].as_deref()?))
    }
    pub(crate) fn tcp_completion_wire<'a>(&self,ticket:TcpFallbackTicket,
        full:Option<&'a [u8]>,tc:&'a [u8],now_ms:u64)->Option<&'a [u8]>{
        let (idx,flow)=self.matching_reply(tc,now_ms).ok()?;
        if flow.serial!=ticket.serial||be16(&tc[..2])!=ticket.id{return None}
        if let Some(answer)=full{
            if answer.len()<=flow.udp_cap&&answer.get(2).is_some_and(|flags|flags&2==0)&&
               self.matching_reply(answer,now_ms).is_ok_and(|(other,_)|other==idx){
                return Some(answer)
            }
        }
        // Failed/oversized TCP answer: retain original genuine TC reply;
        // the App may use its existing ordinary TCP/53 tunnel flow.
        Some(tc)
    }
    /// Exactly one OS UDP datagram or a completed same-physical TCP fallback from the physically connected socket.
    /// The caller must validate generation/physical scope before writing
    /// the resulting packet into the SAME owned TUN FD.
    pub(crate) fn receive(
        &mut self,wire:&[u8],packet:&mut [u8],now_ms:u64
    )->Result<usize,PhysicalDnsError>{
        let (idx,flow)=self.matching_reply(wire,now_ms)?;
        let id=be16(&wire[..2]);
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
        self.questions[idx]=None;
        Ok(size)
    }
}
/// B59: large physical DNS UDP answers (e.g. EDNS0) are synthesized by
/// the existing exact App-ID/QNAME/lease mapper above. If their IPv4 length
/// exceeds the original TUN's bounded inner MTU, use B16's RFC791 fragment
/// builder to send the same restored UDP datagram in smaller TUN writes.
/// This never opens a second socket, changes a DNS response or invokes M3.
/// Each callback writes through the original scoped physical-DNS TUN owner.
/// A false callback cannot be counted as a completed App DNS reply.
pub(crate) fn emit_physical_dns_tun_reply<F:FnMut(&[u8],bool)->bool>(
    packet:&mut [u8],inner_mtu:usize,scratch:&mut [u8],mut write:F
)->Result<usize,()>{
    if inner_mtu<68||inner_mtu>scratch.len()||
       packet.len()<28||packet.len()>MAX_DNS_REPLY_IPV4||
       packet[0]!=0x45||packet[9]!=17||
       usize::from(be16(&packet[2..4]))!=packet.len()||
       be16(&packet[6..8])!=0x4000||
       be16(&packet[20..22])!=53{
        return Err(())
    }
    if packet.len()<=inner_mtu{
        return if write(packet,false){Ok(1)}else{Err(())};
    }
    // The physical synthetic response is generated locally with DF set.
    // Temporarily clear DF to permit real RFC791 fragments, then restore
    // the unchanged original complete reply even after a failed TUN write.
    let original_flags=[packet[6],packet[7]];
    let original_sum=[packet[10],packet[11]];
    packet[6..8].fill(0);
    packet[10..12].fill(0);
    let sum=checksum(&packet[..20],0);
    packet[10..12].copy_from_slice(&sum.to_be_bytes());
    let mut offset=0;
    let mut result=Err(());
    for i in 0..128{
        let Some((n,end,done))=crate::v4_android_ipv4_mtu::fragment(
            packet,offset,inner_mtu,scratch
        )else{break};
        if !write(&scratch[..n],true){break}
        if done{result=Ok(i+1);break}
        offset=end;
    }
    packet[6..8].copy_from_slice(&original_flags);
    packet[10..12].copy_from_slice(&original_sum);
    result
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
    fn b63_physical_dns_tcp_fallback_exact_udp_ticket_and_size(){
        let mut query=make_query(0x1001);
        query[11]=1;
        query.extend_from_slice(&[0,0,41,4,208,0,0,0,0,0,0]); // EDNS 1232
        let mut flows=PhysicalDnsUdpFlows::default();
        let mut wire=[0u8;MAX_DNS_WIRE];
        let (n,_,_)=flows.prepare(&ip_query(&query),&mut wire,1).unwrap();
        let mut tc=wire[..n].to_vec();tc[2]=0x83;tc[3]=0x80;
        let (ticket,original)=flows.fallback_question(&tc,2).unwrap();
        assert_eq!(original,&wire[..n]);
        let mut full=make_query(be16(&tc[..2]));
        full[2]=0x81;full[3]=0x80;full[7]=32;
        for _ in 0..32{
            full.extend_from_slice(&[0xc0,12,0,1,0,1,0,0,0,60,0,4,1,2,3,4]);
        }
        assert!(full.len()>512&&full.len()<1232);
        assert_eq!(flows.tcp_completion_wire(ticket,Some(&full),&tc,3),Some(full.as_slice()));
        let mut wrong=full.clone();wrong[1]^=1;
        assert_eq!(flows.tcp_completion_wire(ticket,Some(&wrong),&tc,3),Some(tc.as_slice()));
        let mut ip=[0u8;MAX_DNS_REPLY_IPV4];
        let size=flows.receive(&full,&mut ip,3).unwrap();
        assert_eq!(size,28+full.len());
        assert_eq!(&ip[28..30],&0x1001u16.to_be_bytes());
        assert!(flows.tcp_completion_wire(ticket,Some(&full),&tc,4).is_none());
        let (n,_,_)=flows.prepare(&ip_query(&make_query(0x1002)),&mut wire,5).unwrap();
        let mut tc=wire[..n].to_vec();tc[2]=0x83;tc[3]=0x80;
        let (ticket,_)=flows.fallback_question(&tc,6).unwrap();
        full[..2].copy_from_slice(&tc[..2]);
        assert_eq!(flows.tcp_completion_wire(ticket,Some(&full),&tc,6),Some(tc.as_slice()));
        flows.stop();
        assert!(flows.tcp_completion_wire(ticket,None,&tc,7).is_none());
    }
    #[test]
    fn b2c2b3_physical_owned_ipv4_udp53_real_question_reply_checksum(){
        let original=ip_query(&make_query(0x1001));
        let mut flows=PhysicalDnsUdpFlows::default();
        let mut wire=[0u8;MAX_DNS_WIRE];
        let (n,id,created)=flows.prepare(&original,&mut wire,1).unwrap();
        assert!(created);
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
        let (n,id,created)=flows.prepare(&p,&mut wire,1).unwrap();
        assert!(created);
        let mut response=wire[..n].to_vec();response[2]=0x81;response[3]=0x80;
        let old=response[20];
        response[20]=if old==b'x'{b'y'}else{b'x'};
        let mut ip=[0u8;MAX_DNS_REPLY_IPV4];
        assert_eq!(flows.receive(&response,&mut ip,2),Err(PhysicalDnsError::QuestionMismatch));
        response[20]=old;
        assert_eq!(flows.receive(&response,&mut ip,12_001),Err(PhysicalDnsError::Expired));
        flows.cancel(id);
        assert_eq!(flows.len(),0);
        let (_,next,created)=flows.prepare(&p,&mut wire,2).unwrap();
        assert!(created);
        flows.stop();
        let mut okay=wire[..n].to_vec();okay[2]=0x81;okay[3]=0x80;
        assert_eq!(flows.receive(&okay,&mut ip,3),Err(PhysicalDnsError::Unowned));
        assert_eq!(flows.len(),0);
        assert_ne!(next,0);
    }
    #[test]
    fn b7_physical_dns_app_retransmit_reuses_generation_slot_not_other_apps(){
        let first=ip_query(&make_query(0x2222));
        let mut other=first.clone();
        other[20..22].copy_from_slice(&50002u16.to_be_bytes());
        let mut flows=PhysicalDnsUdpFlows::default();
        let mut wire=[0u8;MAX_DNS_WIRE];
        let (n,id,fresh)=flows.prepare(&first,&mut wire,100).unwrap();
        assert!(fresh);assert_eq!(flows.len(),1);
        let original_wire=wire[..n].to_vec();
        for at in [101,102,103,104,105,106,107,108]{
            let (again,reused,created)=flows.prepare(&first,&mut wire,at).unwrap();
            assert_eq!((again,reused,created),(n,id,false));
            assert_eq!(&wire[..n],original_wire);
            assert_eq!(flows.len(),1);
            // On a retry send failure original in-flight mapping survives.
            if created{flows.cancel(reused)}
            assert_eq!(flows.len(),1);
        }
        let (_,second,fresh)=flows.prepare(&other,&mut wire,109).unwrap();
        assert!(fresh);assert_ne!(second,id);assert_eq!(flows.len(),2);
        let mut reply=original_wire.clone();
        reply[2]=0x81;reply[3]=0x80;
        let mut output=[0u8;MAX_DNS_REPLY_IPV4];
        assert!(flows.receive(&reply,&mut output,110).is_ok());
        assert_eq!(&output[22..24],&40001u16.to_be_bytes());
        assert_eq!(flows.len(),1);
        assert_eq!(flows.receive(&reply,&mut output,111),Err(PhysicalDnsError::Unowned));
        // Stop cancels the other App's unrelated pending transaction.
        flows.stop();
        assert_eq!(flows.len(),0);
        let mut new_reply=wire[..n].to_vec();
        new_reply[2]=0x81;new_reply[3]=0x80;
        assert_eq!(flows.receive(&new_reply,&mut output,112),
            Err(PhysicalDnsError::Unowned));
    }
    #[test]
    fn b7_physical_dns_retransmit_expiry_and_query_identity(){
        let source=ip_query(&make_query(0x3001));
        let mut different=ip_query(&make_query(0x3002));
        different[16..20].copy_from_slice(&[9,9,9,9]);
        let mut flows=PhysicalDnsUdpFlows::default();
        let mut wire=[0u8;MAX_DNS_WIRE];
        let (n,first,fresh)=flows.prepare(&source,&mut wire,1).unwrap();
        assert!(fresh);
        let (_,different_id,fresh)=flows.prepare(&different,&mut wire,2).unwrap();
        assert!(fresh);assert_ne!(first,different_id);
        let (_,retry,fresh)=flows.prepare(&source,&mut wire,11_999).unwrap();
        assert_eq!(retry,first);assert!(!fresh);
        let (_,after_expiry,fresh)=flows.prepare(&source,&mut wire,12_002).unwrap();
        assert!(fresh);assert_ne!(after_expiry,first);
        assert_eq!(n,make_query(0x3001).len());
        flows.cancel(after_expiry);flows.stop();
        assert_eq!(flows.len(),0);
    }
    #[test]
    fn b2c2b3_b4_physical_two_app_resolvers_reverse_order_and_stop(){
        let a=ip_query(&make_query(0x1111));
        let mut b=ip_query(&make_query(0x2222));
        b[16..20].copy_from_slice(&[9,9,9,9]);
        b[20..22].copy_from_slice(&50002u16.to_be_bytes());
        let mut flows=PhysicalDnsUdpFlows::default();
        let mut wire=[0u8;MAX_DNS_WIRE];
        let (na,ida,created)=flows.prepare(&a,&mut wire,1).unwrap();
        assert!(created);
        let mut ra=wire[..na].to_vec();ra[2]=0x81;ra[3]=0x80;
        let (nb,idb,created)=flows.prepare(&b,&mut wire,1).unwrap();
        assert!(created);
        assert_ne!(ida,idb);
        let mut rb=wire[..nb].to_vec();rb[2]=0x81;rb[3]=0x80;
        let mut ip=[0u8;MAX_DNS_REPLY_IPV4];
        let len=flows.receive(&rb,&mut ip,2).unwrap();
        assert_eq!(&ip[12..20],&[9,9,9,9,10,66,0,2]);
        assert_eq!(&ip[22..24],&50002u16.to_be_bytes());
        assert_eq!(&ip[28..30],&0x2222u16.to_be_bytes());
        assert_eq!(checksum(&ip[..20],0),0);
        assert!(len>28);
        assert_eq!(flows.len(),1);
        flows.stop();
        assert_eq!(flows.receive(&ra,&mut ip,3),Err(PhysicalDnsError::Unowned));
        assert_eq!(flows.len(),0);
    }
}

#[cfg(test)]
mod b59_tests{
    use super::*;

    fn original_query()->Vec<u8>{
        let mut q=vec![0u8;12];
        q[0..2].copy_from_slice(&0x1234u16.to_be_bytes());
        q[2]=1;q[5]=1;q[11]=1; // QD=1; EDNS OPT additional
        for label in ["wide","example","org"]{
            q.push(label.len() as u8);
            q.extend_from_slice(label.as_bytes());
        }
        q.extend_from_slice(&[0,0,16,0,1]); // TXT IN
        q.extend_from_slice(&[0,0,41,16,0,0,0,0,0,0,0]); // OPT 4096
        let size=28+q.len();
        let mut ip=vec![0u8;size];
        ip[0]=0x45;ip[2..4].copy_from_slice(&(size as u16).to_be_bytes());
        ip[8]=64;ip[9]=17;
        ip[12..16].copy_from_slice(&[10,66,0,2]);
        ip[16..20].copy_from_slice(&[8,8,8,8]);
        ip[20..22].copy_from_slice(&41011u16.to_be_bytes());
        ip[22..24].copy_from_slice(&53u16.to_be_bytes());
        ip[24..26].copy_from_slice(&((size-20) as u16).to_be_bytes());
        ip[28..].copy_from_slice(&q);
        ip
    }
    fn original_physical_reply(large:bool)->Vec<u8>{
        let request=original_query();
        let mut flows=PhysicalDnsUdpFlows::default();
        let mut outbound=[0u8;MAX_DNS_WIRE];
        let (n,synthetic,new)=flows.prepare(&request,&mut outbound,10).unwrap();
        assert!(new);
        let mut response=outbound[..n].to_vec();
        let opt=response.split_off(n-11);
        response[2]=0x81;response[3]=0x80;
        if large{
            response[6..8].copy_from_slice(&1u16.to_be_bytes()); // 1 TXT answer
            // A valid multiple-string TXT RDATA, almost a full EDNS datagram.
            let mut txt=Vec::new();
            for _ in 0..15{
                txt.push(240);
                txt.extend_from_slice(&[b'x';240]);
            }
            response.extend_from_slice(&[0xc0,0x0c,0,16,0,1,0,0,0,60]);
            response.extend_from_slice(&(txt.len() as u16).to_be_bytes());
            response.extend_from_slice(&txt);
        }
        response.extend_from_slice(&opt);
        assert!(response.len()<=MAX_DNS_WIRE);
        let mut packet=vec![0u8;MAX_DNS_REPLY_IPV4];
        let len=flows.receive(&response,&mut packet,11).unwrap();
        assert_eq!(flows.len(),0);
        packet.truncate(len);
        assert_eq!(&packet[12..20],&[8,8,8,8,10,66,0,2]);
        assert_eq!(&packet[20..24],&[0,53,0xa0,0x33]); // 41011 app UDP port
        assert_eq!(&packet[28..30],&0x1234u16.to_be_bytes());
        assert_eq!(checksum(&packet[..20],0),0);
        let mut pseudo=0u32;
        for word in packet[12..20].chunks_exact(2){
            pseudo+=u32::from(be16(word));
        }
        pseudo+=17+(packet.len()-20) as u32;
        assert_eq!(checksum(&packet[20..],pseudo),0);
        packet
    }

    #[test]
    fn b59_physical_dns_edns_large_response_normal_game_ipv4_reassembles(){
        let original=original_physical_reply(true);
        assert!(original.len()>3_600);
        for mtu in [576usize,1_260,1_460]{
            let mut packet=original.clone();
            let mut scratch=[0u8;2_048];
            let mut pieces=Vec::new();
            let count=emit_physical_dns_tun_reply(
                &mut packet,mtu,&mut scratch,|p,fragmented|{
                    assert!(fragmented);
                    assert!(p.len()<=mtu);
                    pieces.push(p.to_vec());
                    true
                }).unwrap();
            assert!(count>=3&&count<=128);
            assert_eq!(pieces.len(),count);
            let mut reconstructed=Vec::new();
            for (i,fragment) in pieces.iter().enumerate(){
                let offset=usize::from(be16(&fragment[6..8])&0x1fff)*8;
                assert_eq!(offset,reconstructed.len());
                assert_eq!(usize::from(be16(&fragment[2..4])),fragment.len());
                assert_eq!(checksum(&fragment[..20],0),0);
                if i==0{
                    assert_eq!(&fragment[20..22],&53u16.to_be_bytes());
                }
                let more=be16(&fragment[6..8])&0x2000!=0;
                assert_eq!(more,i+1<count);
                reconstructed.extend_from_slice(&fragment[20..]);
            }
            // Exact original App UDP length, DNS ID, TXT bytes and checksum
            // reassemble without any new DNS parser or TCP stack.
            assert_eq!(reconstructed,&original[20..]);
            assert_eq!(packet,original); // helper restores synthetic DF/checksum
        }
    }
    #[test]
    fn b59_physical_dns_small_reply_unchanged_one_tun_write(){
        let original=original_physical_reply(false);
        assert!(original.len()<576);
        let mut packet=original.clone();
        let mut scratch=[0u8;2_048];
        let mut writes=0;
        let count=emit_physical_dns_tun_reply(
            &mut packet,1_300,&mut scratch,|p,fragmented|{
                assert!(!fragmented);
                assert_eq!(p,original.as_slice());
                writes+=1;true
            }).unwrap();
        assert_eq!((count,writes),(1,1));
        assert_eq!(packet,original);
    }
    #[test]
    fn b59_physical_dns_partial_tun_write_never_reports_complete(){
        let original=original_physical_reply(true);
        let mut packet=original.clone();
        let mut scratch=[0u8;2_048];
        let mut attempts=0;
        assert_eq!(emit_physical_dns_tun_reply(
            &mut packet,1_200,&mut scratch,|_,fragmented|{
                assert!(fragmented);
                attempts+=1;
                attempts==1
            }),Err(()));
        assert_eq!(attempts,2);
        assert_eq!(packet,original);
        let mut wrong=original.clone();
        wrong[20]=1; // unowned source port no longer DNS53
        assert_eq!(emit_physical_dns_tun_reply(
            &mut wrong,1_200,&mut scratch,|_,_|panic!("unowned DNS emitted")),Err(()));
        assert_eq!(emit_physical_dns_tun_reply(
            &mut packet,60,&mut scratch,|_,_|panic!("invalid MTU emitted")),Err(()));
    }
}
