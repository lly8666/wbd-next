//! PLAN027A shared bounded RFC791 IPv4 slow path, not a LINK format.
//! Reuses the IP endpoints' reassembly; no per-session reassembly table.
 //! Cold/exception-only allocation. Ordinary packets never enter here.
#![forbid(unsafe_code)]

#[derive(Debug,Clone,Copy,PartialEq,Eq)]
pub enum FragmentError {
    Malformed, BadChecksum, DfSet, AlreadyFragmented, NoFragmentNeeded,
    TooSmall, TooManyFragments, NotEligibleIcmp,
}

fn be16(data:&[u8],at:usize)->u16{
    u16::from_be_bytes([data[at],data[at+1]])
}
fn checksum(data:&[u8])->u16{
    let mut sum=0u32;
    for pair in data.chunks_exact(2){
        sum+=u32::from(u16::from_be_bytes([pair[0],pair[1]]));
    }
    if data.len()%2==1{sum+=u32::from(data[data.len()-1])<<8}
    while sum>>16!=0{sum=(sum&0xffff)+(sum>>16)}
    !(sum as u16)
}
fn parse_ipv4(packet:&[u8])->Result<(usize,u16),FragmentError>{
    if packet.len()<20||packet.len()>65_535||packet[0]>>4!=4{
        return Err(FragmentError::Malformed)
    }
    let ihl=usize::from(packet[0]&15)*4;
    if !(20..=60).contains(&ihl)||ihl>packet.len()||
        usize::from(be16(packet,2))!=packet.len()||
        packet[8]==0 {
        return Err(FragmentError::Malformed)
    }
    if checksum(&packet[..ihl])!=0{return Err(FragmentError::BadChecksum)}
    let flags=be16(packet,6);
    if flags&0x8000!=0{return Err(FragmentError::Malformed)}
    Ok((ihl,flags))
}
fn later_fragment_options(original:&[u8])->Result<Vec<u8>,FragmentError>{
    let mut copied=Vec::new();
    let mut at=0usize;
    while at<original.len(){
        match original[at]{
            0=>break, // EOL; remaining bytes are padding, not copied
            1=>at+=1, // NOP belongs only to the original first header
            kind=>{
                if at+2>original.len(){return Err(FragmentError::Malformed)}
                let count=usize::from(original[at+1]);
                if count<2||at+count>original.len(){
                    return Err(FragmentError::Malformed)
                }
                if kind&0x80!=0{copied.extend_from_slice(&original[at..at+count])}
                at+=count
            },
        }
    }
    while copied.len()%4!=0{copied.push(0)}
    if copied.len()>40{return Err(FragmentError::Malformed)}
    Ok(copied)
}
/// Split a single valid unfragmented DF0 IPv4 packet after a real TUN read.
/// Packets <= MTU are outside this exception API; DF1/previously fragmented
/// inputs are never silently converted into normal Game/FEC business.
pub fn fragment_ipv4_df0(packet:&[u8],mtu:usize,max_fragments:usize)
    ->Result<Vec<Vec<u8>>,FragmentError>
{
    let (first_ihl,flags)=parse_ipv4(packet)?;
    if flags&0x4000!=0{return Err(FragmentError::DfSet)}
    if flags&0x3fff!=0{return Err(FragmentError::AlreadyFragmented)}
    if packet.len()<=mtu{return Err(FragmentError::NoFragmentNeeded)}
    if mtu<68||mtu<first_ihl+8||max_fragments==0{
        return Err(FragmentError::TooSmall)
    }
    let copied=later_fragment_options(&packet[20..first_ihl])?;
    let next_ihl=20+copied.len();
    if mtu<next_ihl+8{return Err(FragmentError::TooSmall)}
    let payload=&packet[first_ihl..];
    let mut parts=Vec::with_capacity(4);
    let mut offset=0usize;
    while offset<payload.len(){
        let first=offset==0;
        let hlen=if first{first_ihl}else{next_ihl};
        let room=mtu-hlen;
        let last=payload.len()-offset<=room;
        let chunk=if last{payload.len()-offset}else{room&!7};
        if chunk==0||(!last&&chunk<8){return Err(FragmentError::TooSmall)}
        if parts.len()==max_fragments{return Err(FragmentError::TooManyFragments)}
        if offset/8>0x1fff{return Err(FragmentError::Malformed)}
        let mut frame=vec![0u8;hlen+chunk];
        frame[..20].copy_from_slice(&packet[..20]);
        if first{
            frame[20..first_ihl].copy_from_slice(&packet[20..first_ihl]);
        }else{
            frame[20..next_ihl].copy_from_slice(&copied);
        }
        frame[0]=(4<<4)|((hlen/4) as u8);
        frame[2..4].copy_from_slice(&((hlen+chunk) as u16).to_be_bytes());
        // Preserve original DF0 identification, not "repair" PN or LINK ID.
        let fragment_flags=(offset/8) as u16|if last{0}else{0x2000};
        frame[6..8].copy_from_slice(&fragment_flags.to_be_bytes());
        frame[10..12].fill(0);
        let header_checksum=checksum(&frame[..hlen]);
        frame[10..12].copy_from_slice(&header_checksum.to_be_bytes());
        frame[hlen..].copy_from_slice(&payload[offset..offset+chunk]);
        parts.push(frame);
        offset+=chunk;
    }
    if parts.len()<2{return Err(FragmentError::NoFragmentNeeded)}
    Ok(parts)
}
/// Build an RFC1191 Type3/Code4 response to an already-consumed oversized
/// DF packet. The owner must supply its own trusted router source IPv4 and
/// bounded control credit, not invent it from the remote peer/ciphertext.
/// This pure encoder is NOT an OS delivery receipt.
pub fn icmp_fragmentation_needed(original:&[u8],router_ip:[u8;4],inner_mtu:u16)
    ->Result<Vec<u8>,FragmentError>
{
    let (hlen,flags)=parse_ipv4(original)?;
    if flags&0x4000==0||flags&0x3fff!=0||
        inner_mtu<68||original.len()<=usize::from(inner_mtu){
        return Err(FragmentError::NotEligibleIcmp)
    }
    let src=&original[12..16];
    let dst=&original[16..20];
    if src==[0,0,0,0]||src==[255,255,255,255]||
       src[0]>=224||dst[0]>=224||dst==[255,255,255,255]||
       router_ip==[0,0,0,0]||router_ip[0]>=224{
        return Err(FragmentError::NotEligibleIcmp)
    }
    // No ICMP error caused by another ICMP error (RFC1812).
    if original[9]==1 && hlen<original.len() &&
        matches!(original[hlen],3|4|5|11|12) {
        return Err(FragmentError::NotEligibleIcmp)
    }
    let quote_len=(hlen+8).min(original.len());
    let total=20+8+quote_len;
    let mut reply=vec![0u8;total];
    reply[0]=0x45;
    reply[2..4].copy_from_slice(&(total as u16).to_be_bytes());
    reply[4..6].copy_from_slice(&be16(original,4).wrapping_add(1).to_be_bytes());
    reply[8]=64;
    reply[9]=1;
    reply[12..16].copy_from_slice(&router_ip);
    reply[16..20].copy_from_slice(src);
    reply[20]=3;reply[21]=4;
    reply[26..28].copy_from_slice(&inner_mtu.to_be_bytes());
    reply[28..].copy_from_slice(&original[..quote_len]);
    let c=checksum(&reply[20..]);
    reply[22..24].copy_from_slice(&c.to_be_bytes());
    let c=checksum(&reply[..20]);
    reply[10..12].copy_from_slice(&c.to_be_bytes());
    Ok(reply)
}
#[cfg(test)]
mod tests{
    use super::*;
    fn packet(payload:usize,df:bool,options:&[u8])->Vec<u8>{
        let hlen=20+options.len();
        assert!(options.len()%4==0);
        let mut data=vec![0u8;hlen+payload];
        data[0]=0x40|((hlen/4) as u8);
        data[2..4].copy_from_slice(&((hlen+payload) as u16).to_be_bytes());
        data[4..6].copy_from_slice(&0x2244u16.to_be_bytes());
        data[6..8].copy_from_slice(&(if df{0x4000u16}else{0}).to_be_bytes());
        data[8]=64;data[9]=17;
        data[12..16].copy_from_slice(&[10,8,0,1]);
        data[16..20].copy_from_slice(&[10,8,0,2]);
        data[20..hlen].copy_from_slice(options);
        for (i,byte) in data[hlen..].iter_mut().enumerate(){*byte=(i%251) as u8;}
        let header_checksum=checksum(&data[..hlen]);
        data[10..12].copy_from_slice(&header_checksum.to_be_bytes());
        data
    }
    #[test]
    fn df0_exact_fragment_offsets_options_and_unmodified_udp_payload(){
        let opts=[0x82,4,0xaa,0xbb, 0x44,4,0xcc,0xdd];
        let input=packet(3000,false,&opts);
        let fragments=fragment_ipv4_df0(&input,576,32).unwrap();
        assert_eq!(fragments.len(),6);
        let mut recovered=Vec::new();
        for (i,p) in fragments.iter().enumerate(){
            let hlen=usize::from(p[0]&15)*4;
            assert!(p.len()<=576);
            assert_eq!(checksum(&p[..hlen]),0);
            assert_eq!(be16(p,4),0x2244);
            assert_eq!(usize::from(be16(p,6)&0x1fff)*8,recovered.len());
            if i+1!=fragments.len(){
                assert!(be16(p,6)&0x2000!=0);
                assert_eq!((p.len()-hlen)%8,0);
            }else{assert_eq!(be16(p,6)&0x2000,0)}
            if i==0{assert_eq!(&p[20..hlen],&opts)}
            else{assert_eq!(&p[20..hlen],&opts[..4])}
            recovered.extend_from_slice(&p[hlen..]);
        }
        assert_eq!(recovered,&input[28..]);
        assert_eq!(fragment_ipv4_df0(&input,576,4),Err(FragmentError::TooManyFragments));
        assert_eq!(fragment_ipv4_df0(&packet(100,false,&[]),576,32),
                   Err(FragmentError::NoFragmentNeeded));
    }
    #[test]
    fn df1_uses_correct_icmp3_code4_quote_and_pmtu_and_blocks_error_loop(){
        let input=packet(2600,true,&[]);
        assert_eq!(fragment_ipv4_df0(&input,1200,32),Err(FragmentError::DfSet));
        let reply=icmp_fragmentation_needed(&input,[10,8,0,254],1200).unwrap();
        assert_eq!((&reply[12..16],&reply[16..20]),(&[10,8,0,254][..],&[10,8,0,1][..]));
        assert_eq!((&reply[20..22],be16(&reply,26)),(&[3,4][..],1200));
        assert_eq!(checksum(&reply[..20]),0);
        assert_eq!(checksum(&reply[20..]),0);
        assert_eq!(&reply[28..],&input[..28]);
        let mut fragmented=input.clone();
        fragmented[6..8].copy_from_slice(&0x4001u16.to_be_bytes());
        fragmented[10..12].fill(0);
        let header_checksum=checksum(&fragmented[..20]);
        fragmented[10..12].copy_from_slice(&header_checksum.to_be_bytes());
        assert_eq!(icmp_fragmentation_needed(&fragmented,[10,8,0,254],1200),
                   Err(FragmentError::NotEligibleIcmp));
    }
    #[test]
    fn malformed_header_checksum_and_tampered_options_are_rejected(){
        let mut input=packet(2000,false,&[]);
        input[2]=0;
        assert_eq!(fragment_ipv4_df0(&input,1200,32),Err(FragmentError::Malformed));
        input=packet(2000,false,&[]);
        input[8]=1;
        assert_eq!(fragment_ipv4_df0(&input,1200,32),Err(FragmentError::BadChecksum));
        input=packet(2000,false,&[0x82,1,0,0]);
        assert_eq!(fragment_ipv4_df0(&input,1200,32),Err(FragmentError::Malformed));
    }
}
