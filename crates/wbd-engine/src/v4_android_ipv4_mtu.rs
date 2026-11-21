//! Original Android Fixed M4 IPv4 slow path, also Host-testable.
//! No new protocol, crypto, socket or background worker.
fn word(b:&[u8])->u16{u16::from_be_bytes([b[0],b[1]])}
pub(crate) fn checksum(b:&[u8])->u16{
    let mut sum=0u32;
    let mut pairs=b.chunks_exact(2);
    for x in &mut pairs{sum+=u32::from(word(x))}
    if let Some(&last)=pairs.remainder().first(){sum+=u32::from(last)<<8}
    while sum>0xffff{sum=(sum&0xffff)+(sum>>16)}
    !(sum as u16)
}
pub(crate) fn header_len(p:&[u8])->Option<usize>{
    if p.len()<20||p.len()>65_535||p[0]>>4!=4{return None}
    let h=usize::from(p[0]&15)*4;
    if !(20..=60).contains(&h)||h>p.len()||
       usize::from(word(&p[2..4]))!=p.len(){return None}
    Some(h)
}
// RFC791 copy-bit options only on subsequent fragments; first keeps all.
fn copied_options(p:&[u8],h:usize,out:&mut[u8;40])->Option<usize>{
    let (mut pos,mut used)=(20,0);
    while pos<h{
        let t=p[pos];
        if t==0{break}
        if t==1{pos+=1;continue}
        if pos+1>=h{return None}
        let size=usize::from(p[pos+1]);
        if size<2||pos+size>h{return None}
        if t&0x80!=0{
            out.get_mut(used..used+size)?
                .copy_from_slice(&p[pos..pos+size]);
            used+=size;
        }
        pos+=size;
    }
    let padded=(used+3)&!3;
    out.get_mut(used..padded)?.fill(0);
    Some(padded)
}
pub(crate) fn can_fragment(p:&[u8])->bool{
    let Some(h)=header_len(p)else{return false};
    let f=word(&p[6..8]);
    if f&0x4000!=0||h==p.len()||
       (f&0x2000!=0&&(p.len()-h)%8!=0){return false}
    copied_options(p,h,&mut [0;40]).is_some()
}
/// End measures bytes consumed from THIS packet's IP payload. An already
/// fragmented input retains original ID, absolute offset and MF on its tail.
pub(crate) fn fragment(
    p:&[u8],offset:usize,limit:usize,out:&mut[u8]
)->Option<(usize,usize,bool)>{
    if !can_fragment(p){return None}
    let h=header_len(p)?;
    if offset%8!=0||offset>=p.len()-h{return None}
    let f=word(&p[6..8]);
    let mut opts=[0u8;40];
    let opt_len=copied_options(p,h,&mut opts)?;
    let out_h=if offset==0{h}else{20+opt_len};
    let room=limit.min(out.len()).checked_sub(out_h)?;
    if room<8{return None}
    let remain=p.len()-h-offset;
    let bytes=if remain>room{room&!7}else{remain};
    if bytes==0{return None}
    let end=offset.checked_add(bytes)?;
    let absolute=usize::from(f&0x1fff).checked_add(offset/8)?;
    if absolute>0x1fff{return None}
    let more=end<p.len()-h||f&0x2000!=0;
    if more&&bytes%8!=0{return None}
    let n=out_h+bytes;
    out[..20].copy_from_slice(&p[..20]);
    if offset==0{
        out[20..h].copy_from_slice(&p[20..h]);
    }else{
        out[20..out_h].copy_from_slice(&opts[..opt_len]);
        out[0]=0x40|(out_h/4) as u8;
    }
    out[2..4].copy_from_slice(&(n as u16).to_be_bytes());
    out[6..8].copy_from_slice(&(
        (if more{0x2000u16}else{0})|absolute as u16
    ).to_be_bytes());
    out[10..12].fill(0);
    let sum=checksum(&out[..out_h]);
    out[10..12].copy_from_slice(&sum.to_be_bytes());
    out[out_h..n].copy_from_slice(&p[h+offset..h+end]);
    Some((n,end,end==p.len()-h))
}
/// Local ICMPv4 Destination Unreachable / Fragmentation Needed (3/4).
/// The original app sees it through the SAME owned TUN; not peer M3 DATA.
pub(crate) fn fragmentation_needed(
    original:&[u8],mtu:usize,out:&mut[u8]
)->Option<usize>{
    let h=header_len(original)?;
    if word(&original[6..8])&0x4000==0||
       !(68..=65_535).contains(&mtu)||original[16]>=224||
       original[12]==0{return None}
    if original[9]==1&&original.len()>h&&
       matches!(original[h],3|4|5|11|12){return None}
    let quote=(h+8).min(original.len());
    let total=28+quote;
    if out.len()<total{return None}
    out[..total].fill(0);
    out[0]=0x45;
    out[2..4].copy_from_slice(&(total as u16).to_be_bytes());
    out[8]=64;out[9]=1;
    out[12..16].copy_from_slice(&original[16..20]);
    out[16..20].copy_from_slice(&original[12..16]);
    out[20]=3;out[21]=4;
    out[26..28].copy_from_slice(&(mtu as u16).to_be_bytes());
    out[28..total].copy_from_slice(&original[..quote]);
    let icmp=checksum(&out[20..total]);
    out[22..24].copy_from_slice(&icmp.to_be_bytes());
    let ip=checksum(&out[..20]);
    out[10..12].copy_from_slice(&ip.to_be_bytes());
    Some(total)
}

#[cfg(test)]
mod tests{
    use super::*;
    fn ip(len:usize,ihl:usize,flags:u16)->Vec<u8>{
        let mut p=vec![0u8;len];
        p[0]=0x40|(ihl/4) as u8;
        p[2..4].copy_from_slice(&(len as u16).to_be_bytes());
        p[4..6].copy_from_slice(&0x1234u16.to_be_bytes());
        p[6..8].copy_from_slice(&flags.to_be_bytes());
        p[8]=64;p[9]=17;
        p[12..16].copy_from_slice(&[10,66,0,2]);
        p[16..20].copy_from_slice(&[1,1,1,1]);
        for i in ihl..len{p[i]=(i%251) as u8}
        p
    }
    #[test]
    fn b16_ordinary_df0_fragments_restore_all_ipv4_payload(){
        let source=ip(4020,20,0);
        let mut scratch=[0u8;1350];
        let mut all=Vec::new();
        let (mut offset,mut count)=(0,0);
        loop{
            let (n,end,done)=fragment(&source,offset,1350,&mut scratch).unwrap();
            assert!(n<=1350);
            assert_eq!(checksum(&scratch[..20]),0);
            let flags=word(&scratch[6..8]);
            assert_eq!(usize::from(flags&0x1fff)*8,offset);
            assert_eq!(flags&0x2000!=0,!done);
            all.extend_from_slice(&scratch[20..n]);
            count+=1;offset=end;
            if done{break}
        }
        assert!(count>1);
        assert_eq!(all,source[20..]);
    }
    #[test]
    fn b16_df1_returns_icmp_pmtu_not_a_fragment(){
        let source=ip(4020,20,0x4000);
        let mut scratch=[0u8;1350];
        assert!(!can_fragment(&source));
        assert!(fragment(&source,0,1350,&mut scratch).is_none());
        let n=fragmentation_needed(&source,1375,&mut scratch).unwrap();
        assert_eq!(&scratch[20..22],&[3,4]);
        assert_eq!(word(&scratch[26..28]),1375);
        assert_eq!(&scratch[12..20],&[1,1,1,1,10,66,0,2]);
        assert_eq!(&scratch[28..n],&source[..28]);
        assert_eq!(checksum(&scratch[..20]),0);
        assert_eq!(checksum(&scratch[20..n]),0);
    }
    #[test]
    fn b16_ipv4_options_copy_bit_first_and_later_fragments(){
        let mut source=ip(4028,28,0);
        source[20..28].copy_from_slice(&[0x82,4,0xaa,0xbb,0x44,4,0xcc,0xdd]);
        let mut scratch=[0u8;1340];
        let (n,end,done)=fragment(&source,0,1340,&mut scratch).unwrap();
        assert!(!done);
        assert_eq!(scratch[0],0x47);
        assert_eq!(&scratch[20..28],&source[20..28]);
        assert_eq!(checksum(&scratch[..28]),0);
        let (n2,_,_)=fragment(&source,end,1340,&mut scratch).unwrap();
        assert_eq!(scratch[0],0x46);
        assert_eq!(&scratch[20..24],&[0x82,4,0xaa,0xbb]);
        assert_eq!(checksum(&scratch[..24]),0);
        assert!(n<=1340&&n2<=1340);
    }
    #[test]
    fn b16_existing_fragment_offset_mf_survives_refragment(){
        let source=ip(3020,20,0x200a); // 3000B aligned, base offset 10
        let mut scratch=[0u8;1300];
        let mut offset=0;
        let mut count=0;
        loop{
            let (n,end,done)=fragment(&source,offset,1300,&mut scratch).unwrap();
            let flags=word(&scratch[6..8]);
            assert_eq!(usize::from(flags&0x1fff),10+offset/8);
            assert_ne!(flags&0x2000,0);
            assert_eq!(checksum(&scratch[..20]),0);
            assert!(n<=1300);
            offset=end;count+=1;
            if done{break}
        }
        assert_eq!(offset,3000);
        assert!(count>=3);
    }
    #[test]
    fn b16_bad_option_length_is_not_fragmented(){
        let mut source=ip(3028,28,0);
        source[20..28].copy_from_slice(&[0x82,1,0,0,0,0,0,0]);
        assert!(!can_fragment(&source));
        assert!(fragment(&source,0,1340,&mut [0u8;1340]).is_none());
    }
}
