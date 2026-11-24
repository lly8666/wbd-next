//! Original H2372 IPv4 flow identity, shared by Linux pending admission
//! and Windows bounded ready-batch service. No extra flow map or timer.
pub(crate) fn flow_key(ip:&[u8])->Option<[u8;13]>{
    if ip.len()<24||ip[0]>>4!=4||!matches!(ip[9],6|17){return None}
    let h=usize::from(ip[0]&15)*4;
    if h<20||ip.len()<h+4||u16::from_be_bytes([ip[6],ip[7]])&0x3fff!=0{return None}
    let mut k=[0;13];
    k[0]=ip[9];k[1..9].copy_from_slice(&ip[12..20]);
    k[9..13].copy_from_slice(&ip[h..h+4]);
    Some(k)
}

// Wintun owns the unread ring, so only already-ready packets can be
// reordered. At a full service quantum, interleave flows by occurrence
// rank; preserve each flow's FIFO. No drop, waiting, allocation or priority
// by protocol/port. Unknown/fragment traffic retains its original slots.
#[cfg(any(target_os="windows",test))]
pub(crate) fn ready_order<const N:usize>(keys:[Option<[u8;13]>;N],count:usize)
    ->[usize;N]{
    let mut order=std::array::from_fn(|i|i);
    if count!=N{return order}
    let mut rank=[0usize;N];
    for i in 0..N{
        if let Some(k)=keys[i]{
            rank[i]=keys[..i].iter().filter(|v|**v==Some(k)).count();
        }
    }
    // Stable insertion over known slots only; sparse first occurrences
    // precede the second occurrence of any busy flow.
    for i in 1..N{
        if keys[i].is_none(){continue}
        let item=order[i];
        let mut j=i;
        while let Some(prev)=(0..j).rev().find(|&k|keys[k].is_some()){
            if rank[order[prev]]<=rank[item]{break}
            order[j]=order[prev];j=prev;
        }
        order[j]=item;
    }
    order
}
#[cfg(test)]
mod tests{
    use super::*;
    #[test]
    fn fair_ready_full_keeps_fifo_and_unknown_slots(){
        let a=Some([1;13]);let b=Some([2;13]);let c=Some([3;13]);
        assert_eq!(ready_order([a,a,a,b,a,c],6),[0,3,5,1,2,4]);
        assert_eq!(ready_order([a,a,None,b,a,c],6),[0,3,2,5,1,4]);
        assert_eq!(ready_order([a,a,a,b,a,c],4),[0,1,2,3,4,5]);
    }
    #[test]
    fn fair_ready_key_distinguishes_ports_and_fragments(){
        let mut a=[0u8;40];a[0]=0x45;a[9]=6;a[12]=10;a[16]=20;
        let mut b=a;b[21]=1;
        assert_ne!(flow_key(&a),flow_key(&b));
        b[6]=0x20;assert_eq!(flow_key(&b),None);
    }
}
