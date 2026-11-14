//! PLAN029 same-owner Tunnel DNS/53 purpose NAT. The original Rust TX
//! rewrites only captured UDP queries to the ONE forced dns.tunnel IP;
//! the authenticated Rust RX reverses the resolver source before Wintun
//! delivery. No Go per-packet callback, physical socket, cross-exit retry,
//! or third-party resolver selected by the client application's dst IPv4.
use std::collections::HashMap;
use crate::v4_client_split_wire::{dns_question,dns_reply_question};

const MAX_PENDING:usize=256;
const TTL_MS:u64=5_000;
#[derive(Clone,Debug,Eq,PartialEq)]
struct Ticket{original_dns:u32,until_ms:u64,qname:String,qtype:u16}
pub(crate) struct TunnelDnsMap{
    lease:u32,endpoint:u32,
    pending:HashMap<(u16,u16),Ticket>,
}
fn u16be(d:&[u8])->u16{u16::from_be_bytes([d[0],d[1]])}
fn u32be(d:&[u8])->u32{u32::from_be_bytes([d[0],d[1],d[2],d[3]])}
fn checksum(bytes:&[&[u8]])->u16{
    let mut total=0u32;
    for part in bytes{
        let mut chunks=part.chunks_exact(2);
        for word in &mut chunks{total+=u32::from(u16be(word))}
        if let Some(last)=chunks.remainder().first(){
            total+=u32::from(*last)<<8
        }
    }
    while total>0xffff{total=(total&0xffff)+(total>>16)}
    !(total as u16)
}
fn packet_udp(b:&[u8])->Option<usize>{
    if b.len()<40||b.len()>65535||b[0]>>4!=4||b[9]!=17{return None}
    let ihl=usize::from(b[0]&15)*4;
    if ihl<20||ihl+20>b.len()||u16be(&b[2..4]) as usize!=b.len()||
       u16be(&b[6..8])&0x3fff!=0{return None}
    let u=&b[ihl..];
    if u16be(&u[4..6]) as usize!=u.len(){return None}
    Some(ihl)
}
fn rechecksum(b:&mut[u8],ihl:usize){
    b[10..12].fill(0);
    let ip=checksum(&[&b[..ihl]]);
    b[10..12].copy_from_slice(&ip.to_be_bytes());
    if u16be(&b[ihl+6..ihl+8])==0{return} // IPv4 UDP zero is valid
    b[ihl+6..ihl+8].fill(0);
    let mut pseudo=[0u8;12];
    pseudo[..4].copy_from_slice(&b[12..16]);
    pseudo[4..8].copy_from_slice(&b[16..20]);
    pseudo[9]=17;
    pseudo[10..12].copy_from_slice(&b[ihl+4..ihl+6]);
    let sum=checksum(&[&pseudo,&b[ihl..]]);
    b[ihl+6..ihl+8].copy_from_slice(&(if sum==0{0xffff}else{sum}).to_be_bytes());
}
impl TunnelDnsMap{
    pub(crate) fn new(lease:u32,endpoint:u32)->Self{
        Self{lease,endpoint,pending:HashMap::new()}
    }
    pub(crate) fn len(&self)->usize{self.pending.len()}
    /// Called only after PacketIngress classified the QNAME as Tunnel.
    /// Prevent resolver-IP based Direct hijack even if endpoint lies
    /// inside LAN/CN. Record exact original visible DNS for inverse reply.
    pub(crate) fn rewrite_query(&mut self,b:&mut[u8],now_ms:u64)->Result<(),()>{
        let ihl=packet_udp(b).ok_or(())?;
        if u32be(&b[12..16])!=self.lease ||
           u16be(&b[ihl+2..ihl+4])!=53{return Err(())}
        let key=(u16be(&b[ihl..ihl+2]),u16be(&b[ihl+8..ihl+10]));
        let (id,name,qtype)=dns_question(&b[ihl+8..]).map_err(|_|())?;
        if id!=key.1{return Err(())}
        let presented=u32be(&b[16..20]);
        if presented==0||presented==u32::MAX{return Err(())}
        match self.pending.get(&key){
            Some(previous) if previous.until_ms>now_ms &&
                (previous.original_dns!=presented ||
                 previous.qname!=name||previous.qtype!=qtype)=>
                return Err(()),
            None if self.pending.len()>=MAX_PENDING=>return Err(()),
            _=>{},
        }
        self.pending.insert(key,Ticket{
            original_dns:presented,until_ms:now_ms.saturating_add(TTL_MS),
            qname:name,qtype,
        });
        b[16..20].copy_from_slice(&self.endpoint.to_be_bytes());
        rechecksum(b,ihl);
        Ok(())
    }
    /// None: not a reply from this internal Tunnel endpoint; transparent
    /// original Tunnel DATA. Some(false): unmatched or expired resolver
    /// response from configured endpoint, do not inject a forged answer.
    /// Some(true): exact 5tuple+DNS-id matched and original source restored.
    pub(crate) fn rewrite_reply(&mut self,b:&mut[u8],now_ms:u64)->Option<bool>{
        let ihl=packet_udp(b)?;
        if u32be(&b[12..16])!=self.endpoint ||
           u32be(&b[16..20])!=self.lease ||
           u16be(&b[ihl..ihl+2])!=53{return None}
        let key=(u16be(&b[ihl+2..ihl+4]),u16be(&b[ihl+8..ihl+10]));
        let Some(ticket)=self.pending.get(&key)else{return Some(false)};
        if ticket.until_ms<=now_ms{
            self.pending.remove(&key);
            return Some(false)
        }
        // Forged same-socket/ID QNAME cannot steal the real client's reply.
        let Ok((id,name,qtype))=dns_reply_question(&b[ihl+8..])else{
            return Some(false)
        };
        if id!=key.1||name!=ticket.qname||qtype!=ticket.qtype{
            return Some(false)
        }
        let original_dns=ticket.original_dns;
        self.pending.remove(&key);
        b[12..16].copy_from_slice(&original_dns.to_be_bytes());
        rechecksum(b,ihl);
        Some(true)
    }
    /// Exact, coarse due sweep only once per source-owner tick (<=256).
    pub(crate) fn expire(&mut self,now_ms:u64){
        self.pending.retain(|_,v|v.until_ms>now_ms);
    }
    pub(crate) fn clear(&mut self){self.pending.clear()}
}
#[cfg(test)]
mod tests{
    use super::*;
    fn udp(src:u32,dst:u32,sport:u16,dport:u16,id:u16)->Vec<u8>{
        let question=b"\x03www\x07globalx\x07example\x00\x00\x01\x00\x01";
        let total=40+question.len();
        let mut b=vec![0u8;total];
        b[0]=0x45;b[2..4].copy_from_slice(&(total as u16).to_be_bytes());
        b[8]=64;b[9]=17;
        b[12..16].copy_from_slice(&src.to_be_bytes());
        b[16..20].copy_from_slice(&dst.to_be_bytes());
        b[20..22].copy_from_slice(&sport.to_be_bytes());
        b[22..24].copy_from_slice(&dport.to_be_bytes());
        b[24..26].copy_from_slice(&((total-20) as u16).to_be_bytes());
        b[28..30].copy_from_slice(&id.to_be_bytes());
        b[30..32].copy_from_slice(&(if sport==53{0x8180u16}else{0x0100u16}).to_be_bytes());
        b[32..34].copy_from_slice(&1u16.to_be_bytes());
        b[40..].copy_from_slice(question);
        rechecksum(&mut b,20);
        b
    }
    #[test]
    fn plan029_tunnel_dns_wrong_question_cannot_consume_original_waiter(){
        let lease=0x0aea0c22;
        let mut map=TunnelDnsMap::new(lease,0x01010101);
        let mut query=udp(lease,0x08080808,49112,53,0x1788);
        assert_eq!(map.rewrite_query(&mut query,100),Ok(()));
        let mut wrong=udp(0x01010101,lease,53,49112,0x1788);
        wrong[45]=b'z'; // wrong QNAME, same socket/transaction ID
        rechecksum(&mut wrong,20);
        assert_eq!(map.rewrite_reply(&mut wrong,101),Some(false));
        assert_eq!(map.len(),1);
        let mut wrong_type=udp(0x01010101,lease,53,49112,0x1788);
        wrong_type[62]=28; // AAAA instead of A
        rechecksum(&mut wrong_type,20);
        assert_eq!(map.rewrite_reply(&mut wrong_type,102),Some(false));
        assert_eq!(map.len(),1);
        let mut good=udp(0x01010101,lease,53,49112,0x1788);
        assert_eq!(map.rewrite_reply(&mut good,103),Some(true));
        assert_eq!(u32be(&good[12..16]),0x08080808);
        assert_eq!(map.len(),0);
    }
    #[test]
    fn plan029_tunnel_dns_redirect_forces_configured_endpoint_reverses_app_source(){
        let lease=0x0aea0c22;
        let mut map=TunnelDnsMap::new(lease,0x01010101);
        let mut q=udp(lease,0x08080808,40021,53,0xa123);
        q[26..28].copy_from_slice(&1u16.to_be_bytes());
        rechecksum(&mut q,20);
        assert!(map.rewrite_query(&mut q,1).is_ok());
        assert_eq!(u32be(&q[16..20]),0x01010101);
        assert_eq!(map.len(),1);
        assert_eq!(checksum(&[&q[..20]]),0);
        let mut r=udp(0x01010101,lease,53,40021,0xa123);
        assert_eq!(map.rewrite_reply(&mut r,2),Some(true));
        assert_eq!(u32be(&r[12..16]),0x08080808);
        assert_eq!(map.len(),0);
        assert_eq!(checksum(&[&r[..20]]),0);
        assert_eq!(map.rewrite_reply(&mut r,3),None);
    }
    #[test]
    fn plan029_tunnel_dns_collision_foreign_answer_and_quota_never_fallback(){
        let lease=0x0aea0c22;
        let mut map=TunnelDnsMap::new(lease,0x01010101);
        let mut first=udp(lease,0x08080808,42100,53,1);
        assert_eq!(map.rewrite_query(&mut first,1),Ok(()));
        let mut collision=udp(lease,0x09090909,42100,53,1);
        assert_eq!(map.rewrite_query(&mut collision,2),Err(()));
        let mut forged=udp(0x01010101,lease,53,42100,2);
        assert_eq!(map.rewrite_reply(&mut forged,2),Some(false));
        let mut proper=udp(0x01010101,lease,53,42100,1);
        assert_eq!(map.rewrite_reply(&mut proper,5001),Some(false));
        assert_eq!(map.len(),0);
        let mut unrelated=udp(0xcb007109,lease,443,50000,3);
        assert_eq!(map.rewrite_reply(&mut unrelated,1),None);
        for n in 0..MAX_PENDING{
            let mut q=udp(lease,0x08080808,50000+n as u16,53,n as u16);
            assert_eq!(map.rewrite_query(&mut q,1),Ok(()));
        }
        let mut full=udp(lease,0x08080808,60000,53,65535);
        assert_eq!(map.rewrite_query(&mut full,2),Err(()));
        assert_eq!(map.len(),MAX_PENDING);
        map.expire(5002);
        assert_eq!(map.len(),0);
    }
}
