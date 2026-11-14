//! PLAN029 Windows kernel-TCP Direct-only NAT seam, distinct from ordinary
//! Tunnel TCP. The Windows TCP listener owns handshake/retransmission; Rust
//! only rewrites the Direct packet's IPv4/TCP 4-tuple to the local listener
//! and forwards accepted native socket bytes to one physical-source-bound
//! peer. This is NOT a generic user-space TCP stack or a new packet reader.
//! Installation/OS routing and real kernel listener acceptance are required
//! before product activation; this module itself never calls Win32.

use std::collections::HashMap;

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) enum TcpNatError{
    InvalidPacket,WrongLease,WrongReverse,NoSyn,Capacity,
    PortExhausted,NoAssociation,UnsupportedFragment,MalformedTcp,
    FragmentCollision,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq,Hash)]
pub(crate) struct TcpNatKey{
    pub client:u32,pub source_port:u16,
    pub presented:u32,pub target_port:u16,
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) struct TcpNatEntry{
    pub key:TcpNatKey,
    pub real_dst:u32,
    pub proxy_port:u16,
    pub last_seen_ms:u64,
}
/// NAT source address is ONE unassigned synthetic IPv4 with ONE OS-owned
/// Wintun /32 route. All selected Direct flows share that IP, separated by
/// per-generation NAT source ports. No /32 per CN domain or remote host.
pub(crate) struct DirectTcpNat{
    lease4:u32,
    synthetic4:u32,
    listener_port:u16,
    hard_cap:usize,
    forward:HashMap<TcpNatKey,u16>,
    reverse:HashMap<u16,TcpNatEntry>,
    next_port:u16,
    port_min:u16,port_max:u16,
}
const NAT_PORT_MIN:u16=32768;
const NAT_PORT_MAX:u16=49151; // 16,384 Direct-only owned ports
const DNS_PORT_MIN:u16=49152;
const DNS_PORT_MAX:u16=64000; // independent bounded DNS tickets
const TCP_SYN:u8=0x02;
const TCP_ACK:u8=0x10;

struct ParsedTcp{
    ihl:usize,offset:u16,more_fragments:bool,
    src:u32,dst:u32,src_port:u16,dst_port:u16,flags:u8,
}
fn be16(d:&[u8])->u16{u16::from_be_bytes([d[0],d[1]])}
fn be32(d:&[u8])->u32{u32::from_be_bytes([d[0],d[1],d[2],d[3]])}
fn parse_packet(d:&[u8])->Result<ParsedTcp,TcpNatError>{
    if d.len()<20||d.len()>65535||d[0]>>4!=4||d[9]!=6 {
        return Err(TcpNatError::InvalidPacket)
    }
    let ihl=usize::from(d[0]&15)*4;
    if ihl<20||ihl>d.len()||be16(&d[2..4]) as usize!=d.len(){
        return Err(TcpNatError::InvalidPacket)
    }
    let frag=be16(&d[6..8]);
    if frag&0x8000!=0{return Err(TcpNatError::InvalidPacket)}
    let offset=frag&0x1fff;
    let mf=frag&0x2000!=0;
    if offset!=0{return Err(TcpNatError::UnsupportedFragment)}
    if d.len()<ihl+20{return Err(TcpNatError::MalformedTcp)}
    let thl=usize::from(d[ihl+12]>>4)*4;
    if thl<20||ihl+thl>d.len() || (mf&&(d.len()-ihl)%8!=0){
        return Err(TcpNatError::MalformedTcp)
    }
    Ok(ParsedTcp{
        ihl,offset,more_fragments:mf,
        src:be32(&d[12..16]),dst:be32(&d[16..20]),
        src_port:be16(&d[ihl..ihl+2]),
        dst_port:be16(&d[ihl+2..ihl+4]),
        flags:d[ihl+13],
    })
}
fn checksum(d:&[u8])->u16{
    let mut sum=0u32;
    let mut chunks=d.chunks_exact(2);
    for c in &mut chunks{sum+=u32::from(be16(c))}
    if let Some(&last)=chunks.remainder().first(){sum+=u32::from(last)<<8}
    while sum>>16!=0{sum=(sum&0xffff)+(sum>>16)}
    !(sum as u16)
}
/// RFC1624 incremental one's-complement checksum update. Does not scan
/// TCP payload even when the application sends large DATA segments, and
/// retains the TCP checksum over an original fragmented datagram (first
/// fragment only). An invalid existing checksum is not silently accepted
/// by the Windows TCP kernel.
fn adjust_checksum(original:u16,old:&[u16;6],new:&[u16;6])->u16{
    let mut sum=u32::from(!original);
    for (&a,&b) in old.iter().zip(new){
        sum+=u32::from(!a)+u32::from(b);
        sum=(sum&0xffff)+(sum>>16);
    }
    while sum>>16!=0{sum=(sum&0xffff)+(sum>>16)}
    !(sum as u16)
}
fn words(src:u32,dst:u32,sport:u16,dport:u16)->[u16;6]{
    [(src>>16) as u16,src as u16,(dst>>16) as u16,dst as u16,
        sport,dport]
}
fn rewrite_tcp(d:&[u8],header:&ParsedTcp,
    src:u32,dst:u32,sport:u16,dport:u16,out:&mut[u8])
    ->Result<usize,TcpNatError>{
    if out.len()<d.len(){return Err(TcpNatError::InvalidPacket)}
    out[..d.len()].copy_from_slice(d);
    let o=&mut out[..d.len()];
    let pos=header.ihl;
    let old=words(header.src,header.dst,header.src_port,header.dst_port);
    let new=words(src,dst,sport,dport);
    let csum=be16(&o[pos+16..pos+18]);
    let corrected=adjust_checksum(csum,&old,&new);
    o[12..16].copy_from_slice(&src.to_be_bytes());
    o[16..20].copy_from_slice(&dst.to_be_bytes());
    o[pos..pos+2].copy_from_slice(&sport.to_be_bytes());
    o[pos+2..pos+4].copy_from_slice(&dport.to_be_bytes());
    o[pos+16..pos+18].copy_from_slice(&corrected.to_be_bytes());
    o[10]=0;o[11]=0;
    let ip_sum=checksum(&o[..header.ihl]);
    o[10..12].copy_from_slice(&ip_sum.to_be_bytes());
    Ok(d.len())
}
impl DirectTcpNat{
    pub(crate) fn new(lease4:u32,synthetic4:u32,listener_port:u16,
        hard_cap:usize)->Result<Self,TcpNatError>{
        if lease4==0||synthetic4==0||lease4==synthetic4||
           listener_port==0||hard_cap==0||hard_cap>16384{
            return Err(TcpNatError::InvalidPacket)
        }
        Self::new_range(lease4,synthetic4,listener_port,hard_cap,
            NAT_PORT_MIN,NAT_PORT_MAX)
    }
    pub(crate) fn new_dns(lease4:u32,synthetic4:u32,listener_port:u16)
        ->Result<Self,TcpNatError>{
        Self::new_range(lease4,synthetic4,listener_port,256,
            DNS_PORT_MIN,DNS_PORT_MAX)
    }
    fn new_range(lease4:u32,synthetic4:u32,listener_port:u16,
        hard_cap:usize,low:u16,high:u16)->Result<Self,TcpNatError>{
        if lease4==0||synthetic4==0||lease4==synthetic4||
           listener_port==0||hard_cap==0||
           hard_cap>usize::from(high-low)+1{return Err(TcpNatError::InvalidPacket)}
        Ok(Self{lease4,synthetic4,listener_port,hard_cap,
            forward:HashMap::new(),reverse:HashMap::new(),next_port:low,
            port_min:low,port_max:high})
    }
    pub(crate) fn len(&self)->usize{self.forward.len()}
    pub(crate) fn by_nat_port(&self,p:u16)->Option<TcpNatEntry>{
        self.reverse.get(&p).copied()
    }
    // Original observed application's local address must already be
    // verified by current authenticated native Wintun owner. Only a new
    // SYN may allocate a NAT port. The same original 4-tuple is fixed.
    pub(crate) fn to_listener(&mut self,packet:&[u8],real_dst:u32,
        now_ms:u64,out:&mut[u8])->Result<(usize,TcpNatEntry),TcpNatError>{
        let p=parse_packet(packet)?;
        if out.len()<packet.len(){return Err(TcpNatError::InvalidPacket)}
        if p.src!=self.lease4{return Err(TcpNatError::WrongLease)}
        let key=TcpNatKey{client:p.src,source_port:p.src_port,
            presented:p.dst,target_port:p.dst_port};
        let port=match self.forward.get(&key){
            Some(p)=>*p,
            None=>{
                if p.flags&TCP_SYN==0||p.flags&TCP_ACK!=0{
                    return Err(TcpNatError::NoSyn)
                }
                if self.forward.len()>=self.hard_cap{
                    return Err(TcpNatError::Capacity)
                }
                let mut free=None;
                for _ in 0..=(self.port_max-self.port_min){
                    let port=self.next_port;
                    self.next_port=if port==self.port_max{
                        self.port_min
                    }else{port+1};
                    if !self.reverse.contains_key(&port){free=Some(port);break}
                }
                let Some(port)=free else{return Err(TcpNatError::PortExhausted)};
                self.forward.insert(key,port);
                self.reverse.insert(port,TcpNatEntry{key,real_dst,
                    proxy_port:port,last_seen_ms:now_ms});
                port
            }
        };
        let entry=self.reverse.get(&port).copied()
            .ok_or(TcpNatError::NoAssociation)?;
        if entry.real_dst!=real_dst{return Err(TcpNatError::NoAssociation)}
        let len=rewrite_tcp(packet,&p,self.synthetic4,self.lease4,
            port,self.listener_port,out)?;
        Ok((len,entry))
    }
    /// Only packets emitted by the kernel TCP listener to our one synthetic
    /// peer + issued NAT port may become client-visible replies. A matched
    /// SYN-ACK comes back as the original presented remote endpoint.
    pub(crate) fn to_app(&self,packet:&[u8],out:&mut[u8])
        ->Result<(usize,TcpNatEntry),TcpNatError>{
        let p=parse_packet(packet)?;
        if p.src!=self.lease4||p.src_port!=self.listener_port||
           p.dst!=self.synthetic4{return Err(TcpNatError::WrongReverse)}
        let entry=self.reverse.get(&p.dst_port).copied()
            .ok_or(TcpNatError::NoAssociation)?;
        let len=rewrite_tcp(packet,&p,entry.key.presented,
            entry.key.client,entry.key.target_port,entry.key.source_port,out)?;
        Ok((len,entry))
    }
    /// For an ACCEPT from the kernel listener, the source tuple must be
    /// exactly the synthetic peer and allocated NAT port. This directs the
    /// Rust physical TCP connection to the REAL IPv4 (never the FakeIP).
    pub(crate) fn accepted(&self,peer:u32,port:u16)->Option<TcpNatEntry>{
        if peer!=self.synthetic4{return None}
        self.by_nat_port(port)
    }
    pub(crate) fn retire(&mut self,key:TcpNatKey)->bool{
        let Some(port)=self.forward.remove(&key)else{return false};
        self.reverse.remove(&port);
        true
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    fn ip(a:u8,b:u8,c:u8,d:u8)->u32{u32::from_be_bytes([a,b,c,d])}
    fn check_tcp_integrity(d:&[u8]){
        let p=parse_packet(d).unwrap();
        assert_eq!(checksum(&d[..p.ihl]),0,"IPv4 checksum corrupt");
        let mut pseudo=[0u8;12];
        pseudo[..4].copy_from_slice(&p.src.to_be_bytes());
        pseudo[4..8].copy_from_slice(&p.dst.to_be_bytes());
        pseudo[9]=6;
        pseudo[10..12].copy_from_slice(&((d.len()-p.ihl) as u16).to_be_bytes());
        let mut wire=Vec::from(pseudo);
        wire.extend_from_slice(&d[p.ihl..]);
        assert_eq!(checksum(&wire),0,"TCP checksum corrupt");
    }
    fn packet(src:u32,dst:u32,sport:u16,dport:u16,flags:u8,data:&[u8])->Vec<u8>{
        let n=40+data.len();let mut d=vec![0u8;n];
        d[0]=0x45;d[2..4].copy_from_slice(&(n as u16).to_be_bytes());
        d[8]=64;d[9]=6;
        d[12..16].copy_from_slice(&src.to_be_bytes());
        d[16..20].copy_from_slice(&dst.to_be_bytes());
        d[20..22].copy_from_slice(&sport.to_be_bytes());
        d[22..24].copy_from_slice(&dport.to_be_bytes());
        d[24..28].copy_from_slice(&0x01234567u32.to_be_bytes());
        d[28..32].copy_from_slice(&0x89abcdefu32.to_be_bytes());
        d[32]=0x50;d[33]=flags;d[34..36].copy_from_slice(&65535u16.to_be_bytes());
        d[40..].copy_from_slice(data);
        let mut pseudo=[0u8;12];
        pseudo[..4].copy_from_slice(&src.to_be_bytes());
        pseudo[4..8].copy_from_slice(&dst.to_be_bytes());
        pseudo[9]=6;
        pseudo[10..12].copy_from_slice(&((n-20) as u16).to_be_bytes());
        let mut all=Vec::from(pseudo);
        all.extend_from_slice(&d[20..]);
        d[36..38].copy_from_slice(&checksum(&all).to_be_bytes());
        let ipcs=checksum(&d[..20]);d[10..12].copy_from_slice(&ipcs.to_be_bytes());
        check_tcp_integrity(&d);d
    }
    #[test]
    fn plan029_dns_tcp_nat_quota_separate_from_full_direct_and_inverse_identity(){
        let lease=ip(10,66,0,2);
        let synthetic=ip(198,19,7,9);
        let mut direct=DirectTcpNat::new(lease,synthetic,46000,1).unwrap();
        let mut dns=DirectTcpNat::new_dns(lease,synthetic,46000).unwrap();
        let mut buf=[0u8;128];
        let first=packet(lease,ip(198,18,4,5),52000,443,TCP_SYN,&[]);
        assert!(direct.to_listener(&first,ip(172,16,3,4),1,&mut buf).is_ok());
        assert_eq!(direct.to_listener(&packet(lease,ip(203,0,113,1),
            52001,443,TCP_SYN,&[]),ip(203,0,113,1),2,&mut buf),
            Err(TcpNatError::Capacity));
        let question=packet(lease,ip(8,8,8,8),52002,53,TCP_SYN,&[]);
        let (_,entry)=dns.to_listener(&question,ip(8,8,8,8),2,&mut buf).unwrap();
        assert!((DNS_PORT_MIN..=DNS_PORT_MAX).contains(&entry.proxy_port));
        assert!(direct.by_nat_port(entry.proxy_port).is_none());
        assert!(dns.accepted(synthetic,entry.proxy_port).is_some());
        let reply=packet(lease,synthetic,46000,entry.proxy_port,
            TCP_SYN|TCP_ACK,&[]);
        let (_,back)=dns.to_app(&reply,&mut buf).unwrap();
        assert_eq!(back.key.presented,ip(8,8,8,8));
        assert_eq!(be16(&buf[20..22]),53);
        check_tcp_integrity(&buf[..40]);
    }
    #[test]
    fn plan029_tcp_kernel_nat_one_owned_synthetic_peer_reverse_syn_ack(){
        let client=ip(198,18,87,77);
        let fake=ip(198,18,87,88);
        let real=ip(172,26,1,50);
        let synthetic=ip(198,19,0,1);
        let mut nat=DirectTcpNat::new(client,synthetic,40001,2).unwrap();
        let original=packet(client,fake,58001,443,TCP_SYN,&[]);
        let mut out=vec![0u8;1500];
        let (n,entry)=nat.to_listener(&original,real,1,&mut out).unwrap();
        assert_eq!(n,40);
        assert_eq!(entry.key.presented,fake);
        assert_eq!(entry.real_dst,real);
        assert_eq!(be32(&out[12..16]),synthetic);
        assert_eq!(be32(&out[16..20]),client);
        assert_eq!(be16(&out[22..24]),40001);
        assert_eq!(be16(&out[20..22]),entry.proxy_port);
        check_tcp_integrity(&out[..n]);
        assert_eq!(nat.accepted(synthetic,entry.proxy_port),Some(entry));
        assert_eq!(nat.accepted(fake,entry.proxy_port),None);
        let reply=packet(client,synthetic,40001,entry.proxy_port,
            TCP_SYN|TCP_ACK,&[]);
        let (count,returned)=nat.to_app(&reply,&mut out).unwrap();
        assert_eq!(returned,entry);
        assert_eq!(be32(&out[12..16]),fake);
        assert_eq!(be32(&out[16..20]),client);
        assert_eq!(be16(&out[20..22]),443);
        assert_eq!(be16(&out[22..24]),58001);
        check_tcp_integrity(&out[..count]);
        // Real CDN IP never becomes an association for a non-CN domain:
        // the NAT key always includes the presented original destination.
        assert!(nat.retire(entry.key));
        assert!(!nat.retire(entry.key));
        assert_eq!(nat.len(),0);
    }
    #[test]
    fn plan029_tcp_native_only_direct_cap_does_not_reclassify_tunnel(){
        let client=ip(198,18,87,77);let target=ip(203,0,113,4);
        let mut nat=DirectTcpNat::new(client,ip(198,19,0,1),40001,1).unwrap();
        let mut out=[0u8;1500];
        let a=packet(client,target,58001,443,TCP_SYN,&[]);
        let b=packet(client,target,58002,443,TCP_SYN,&[]);
        let (_,entry)=nat.to_listener(&a,target,1,&mut out).unwrap();
        assert_eq!(nat.to_listener(&b,target,2,&mut out),
            Err(TcpNatError::Capacity));
        assert_eq!(nat.len(),1);
        assert_eq!(nat.to_listener(&a,target+1,3,&mut out),
            Err(TcpNatError::NoAssociation));
        assert_eq!(nat.len(),1);
        assert_eq!(nat.to_listener(&b,target,3,&mut out),
            Err(TcpNatError::Capacity));
        let no_syn=packet(client,target,58099,443,TCP_ACK,&[]);
        assert_eq!(nat.to_listener(&no_syn,target,2,&mut out),Err(TcpNatError::NoSyn));
        let small=packet(client,target,58077,443,TCP_SYN,&[]);
        assert_eq!(nat.to_listener(&small,target,2,&mut [0u8;10]),
            Err(TcpNatError::InvalidPacket));
        assert_eq!(nat.len(),1); // no shadow allocated on failed output
        assert!(nat.retire(entry.key));
        assert!(nat.to_listener(&b,target,3,&mut out).is_ok());
    }
    #[test]
    fn plan029_tcp_nat_cannot_adopt_foreign_reverse_or_guess_unissued_port(){
        let client=ip(198,18,87,77);let target=ip(198,18,87,88);
        let mut nat=DirectTcpNat::new(client,ip(198,19,0,1),40001,1).unwrap();
        let mut out=[0u8;1500];
        let source=packet(client,target,58001,443,TCP_SYN,&[]);
        let (_,entry)=nat.to_listener(&source,ip(172,26,1,1),1,&mut out).unwrap();
        assert_eq!(nat.to_app(&packet(client,ip(198,19,0,1),40001,
            entry.proxy_port+1,TCP_SYN|TCP_ACK,&[]),&mut out),
            Err(TcpNatError::NoAssociation));
        assert_eq!(nat.to_app(&packet(client,ip(198,18,87,77),40001,
            entry.proxy_port,TCP_SYN|TCP_ACK,&[]),&mut out),
            Err(TcpNatError::WrongReverse));
        assert_eq!(nat.accepted(ip(8,8,8,8),entry.proxy_port),None);
        assert_eq!(nat.len(),1);
    }
}
