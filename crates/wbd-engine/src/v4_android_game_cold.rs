//! B39 original-Go authenticated Game2/4 physical lane canonicalization.
//! Cold only: no FakeTCP/TLS replacement, M3/PN allocator, or M4 worker.
#![forbid(unsafe_code)]
use crate::v4_protected_handoff::GoFlow;

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) struct OriginalGameColdLane{
    pub(crate) lane:u8,
    pub(crate) flow:GoFlow,
    pub(crate) tx_seq:u64,
    pub(crate) rx_seq:u32,
}

// Initial Game2/4 requires one remote 443 listener, separate ORIGINAL Go
// FakeTCP local ports, all consecutive on the same physical IPv4 route.
// Reordering uses original lane IDs, not arrival time, handle or TCP ports.
// Later Game4 hot replacements do NOT call this initial group normalizer.
pub(crate) fn canonical_original_game_lanes(
    lanes:&[OriginalGameColdLane]
)->Option<Vec<OriginalGameColdLane>>{
    let n=lanes.len();
    if !matches!(n,2|4){return None}
    let first=lanes.first()?.flow;
    if first.server_port==0||first.client_port==0{return None}
    let mut ordered=vec![None;n];
    for l in lanes{
        let id=usize::from(l.lane);
        if id==0||id>n||l.tx_seq==0||
           l.flow.client_ip!=first.client_ip||
           l.flow.server_ip!=first.server_ip||
           l.flow.server_port!=first.server_port||
           l.flow.client_port==0||
           ordered[id-1].replace(*l).is_some(){
            return None
        }
    }
    let result=ordered.into_iter().collect::<Option<Vec<_>>>()?;
    let base=result[0].flow.client_port;
    if result.iter().enumerate().any(|(i,l)|
        base.checked_add(i as u16)!=Some(l.flow.client_port)){
        return None
    }
    Some(result)
}

#[cfg(test)]
mod tests{
    use super::*;
    fn lane(id:u8,port:u16)->OriginalGameColdLane{
        OriginalGameColdLane{lane:id,
            flow:GoFlow{client_ip:[192,0,2,4],server_ip:[198,51,100,8],
                client_port:port,server_port:443},
            tx_seq:1234+u64::from(id),rx_seq:0}
    }
    #[test]
    fn android_game_cold_original_two_tls_lanes_use_slot_not_arrival(){
        let sorted=canonical_original_game_lanes(&[
            lane(2,41002),lane(1,41001)]).unwrap();
        assert_eq!(sorted.iter().map(|l|l.lane).collect::<Vec<_>>(),vec![1,2]);
        assert_eq!(sorted[0].flow.client_port,41001);
        assert_eq!(sorted[1].flow.server_port,443);
        assert_eq!(sorted[1].rx_seq,0,"valid TCP wrap boundary");
    }
    #[test]
    fn android_game_cold_original_game4_distinct_local_ports(){
        let sorted=canonical_original_game_lanes(&[
            lane(4,48004),lane(2,48002),lane(1,48001),lane(3,48003)
        ]).unwrap();
        assert_eq!(sorted.iter().map(|l|l.lane).collect::<Vec<_>>(),
            vec![1,2,3,4]);
        assert_eq!(sorted[3].flow.client_port,48004);
    }
    #[test]
    fn android_game_cold_rejects_duplicate_missing_and_cross_scope_lanes(){
        assert!(canonical_original_game_lanes(&[lane(1,41001)]).is_none());
        assert!(canonical_original_game_lanes(&[lane(1,41001),lane(1,41002)]).is_none());
        assert!(canonical_original_game_lanes(&[lane(1,41001),lane(2,41001)]).is_none());
        assert!(canonical_original_game_lanes(&[lane(1,41001),lane(2,41003)]).is_none());
        assert!(canonical_original_game_lanes(&[lane(1,65535),lane(2,1)]).is_none());
        let mut diff=lane(2,41002);diff.flow.server_port=444;
        assert!(canonical_original_game_lanes(&[lane(1,41001),diff]).is_none());
        let mut diff=lane(2,41002);diff.flow.server_ip=[198,51,100,9];
        assert!(canonical_original_game_lanes(&[lane(1,41001),diff]).is_none());
        let mut diff=lane(2,41002);diff.flow.client_ip=[192,0,2,5];
        assert!(canonical_original_game_lanes(&[lane(1,41001),diff]).is_none());
        let mut diff=lane(2,41002);diff.tx_seq=0;
        assert!(canonical_original_game_lanes(&[lane(1,41001),diff]).is_none());
    }
}
