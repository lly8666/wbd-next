//! PLAN029 bounded *startup* padding on original authenticated Normal
//! Tunnel LINK records. Each eligible TCP/UDP flow has one randomly chosen
//! 20..=30-record / 2..=3-second envelope. The first exhausted condition wins.
//! No per-flow byte budget or percentage cap. No timers or Direct sockets.
use std::collections::{HashMap,VecDeque};
use crate::v4_client_split::FlowKey;

const MAX_TRACKED:usize=256;
const MAX_RECORD_PAD:usize=500;
const FLOW_IDLE_MS:u64=120_000;
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) enum StartupMode{Off,Tls,Flows}
struct Seen {
    first_ms:u64,last_ms:u64,window_ms:u16,
    max_records:u8,count:u8,state:u64,
}
pub(crate) struct TunnelStartupPadding {
    mode:StartupMode,
    seen:HashMap<FlowKey,Seen>,
    rotation:VecDeque<FlowKey>,
    state:u64,
}
fn next_random(x:&mut u64)->u64 {
    // Per-original-owner generation noncryptographic randomness only.
    // Cipher, AEAD nonce and protected PN do not depend on this PRNG.
    let mut v=(*x).max(1);
    v^=v<<13;v^=v>>7;v^=v<<17;*x=v;v
}
fn candidate(packet:&[u8],tls_only:bool)->Option<FlowKey> {
    if packet.len()<28||packet[0]>>4!=4{return None}
    let ihl=usize::from(packet[0]&15)*4;
    if ihl<20||ihl+8>packet.len()||
       u16::from_be_bytes([packet[2],packet[3]]) as usize!=packet.len()||
       (u16::from_be_bytes([packet[6],packet[7]])&0x1fff)!=0{
        return None
    }
    let proto=packet[9];
    if proto!=6&&proto!=17{return None}
    let base=if proto==6 {
        if packet.len()<ihl+20{return None}
        let hdr=usize::from(packet[ihl+12]>>4)*4;
        if hdr<20||ihl+hdr>=packet.len(){return None}
        ihl+hdr
    }else{
        let len=u16::from_be_bytes([packet[ihl+4],packet[ihl+5]]) as usize;
        if len!=packet.len()-ihl||len<=8{return None}
        ihl+8
    };
    if tls_only&&!(proto==6&&packet.len()>=base+5&&
       packet[base]==22&&packet[base+1]==3&&packet[base+2]<=4) {
        return None
    }
    Some(FlowKey{
        source:u32::from_be_bytes([packet[12],packet[13],packet[14],packet[15]]),
        destination:u32::from_be_bytes([packet[16],packet[17],packet[18],packet[19]]),
        source_port:u16::from_be_bytes([packet[ihl],packet[ihl+1]]),
        destination_port:u16::from_be_bytes([packet[ihl+2],packet[ihl+3]]),
        protocol:proto,
    })
}
impl TunnelStartupPadding {
    pub(crate) fn new(mode:StartupMode,authenticated_seed:u64)->Self {
        Self{mode,seen:HashMap::new(),rotation:VecDeque::new(),
            state:authenticated_seed.max(1)}
    }
    pub(crate) fn len(&self)->usize{self.seen.len()}
    pub(crate) fn mode_name(&self)->&'static str {
        match self.mode{StartupMode::Off=>"off",StartupMode::Tls=>"tls",
            StartupMode::Flows=>"flows"}
    }
    // Only the original Tunnel M1 owner calls this with actual record room
    // AFTER classification. Direct must not invoke it. Both record count
    // and elapsed window are measured from the FIRST eligible proposal,
    // even if the random result is zero. A 0-byte proposal never delays
    // any business data. No per-flow accumulation or re-seal on replay.
    pub(crate) fn propose(&mut self,packet:&[u8],now_ms:u64,
        current_wire_room:usize)->usize {
        if self.mode==StartupMode::Off||current_wire_room==0{return 0}
        let Some(key)=candidate(packet,self.mode==StartupMode::Tls)
            else{return 0};
        if !self.seen.contains_key(&key){
            if self.seen.len()>=MAX_TRACKED{return 0}
            let seed=next_random(&mut self.state);
            let mut entropy=seed;
            let max_records=20+(next_random(&mut entropy)%11) as u8;
            let window_ms=2000+(next_random(&mut entropy)%1001) as u16;
            self.seen.insert(key,Seen{
                first_ms:now_ms,last_ms:now_ms,window_ms,max_records,
                count:0,state:entropy,
            });
            self.rotation.push_back(key);
        }
        let Some(flow)=self.seen.get_mut(&key)else{return 0};
        flow.last_ms=now_ms;
        if now_ms.saturating_sub(flow.first_ms)>u64::from(flow.window_ms)||
            flow.count>=flow.max_records{return 0}
        flow.count+=1;
        let max=current_wire_room.min(MAX_RECORD_PAD);
        (next_random(&mut flow.state) as usize)%(max+1)
    }
    // Existing original TX due-tick, never a dedicated timer, rotates at
    // most eight known flows. Spent flows are retained until real idle:
    // long-lived traffic cannot restart 2..3-second padding every 30s.
    pub(crate) fn expire_coarse(&mut self,now_ms:u64){
        for _ in 0..8{
            let Some(key)=self.rotation.pop_front()else{break};
            let Some(v)=self.seen.get(&key)else{continue};
            if now_ms.saturating_sub(v.last_ms)>=FLOW_IDLE_MS{
                self.seen.remove(&key);
            }else{self.rotation.push_back(key)}
        }
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    fn udp(port:u16)->Vec<u8>{
        let mut p=vec![0u8;44];p[0]=0x45;
        p[2..4].copy_from_slice(&44u16.to_be_bytes());
        p[9]=17;p[12..16].copy_from_slice(&[10,66,0,2]);
        p[16..20].copy_from_slice(&[203,0,113,77]);
        p[20..22].copy_from_slice(&port.to_be_bytes());
        p[22..24].copy_from_slice(&443u16.to_be_bytes());
        p[24..26].copy_from_slice(&24u16.to_be_bytes());p
    }
    #[test]
    fn off_never_allocates_or_changes_prng(){
        let mut p=TunnelStartupPadding::new(StartupMode::Off,123);
        for _ in 0..2048{assert_eq!(p.propose(&udp(101),0,500),0)}
        assert_eq!(p.len(),0);assert_eq!(p.state,123);
    }
    #[test]
    fn randomized_first_20_to_30_records_without_byte_budget(){
        let mut observed=std::collections::BTreeSet::new();
        let mut above_old_2k=false;
        for seed in 1..=128{
            let packet=udp(4040);
            let mut p=TunnelStartupPadding::new(StartupMode::Flows,seed);
            let mut total=0usize;
            for _ in 0..64{total+=p.propose(&packet,100,500);}
            let key=candidate(&packet,false).unwrap();
            let v=&p.seen[&key];
            assert!((20..=30).contains(&v.max_records));
            assert!((2000..=3000).contains(&v.window_ms));
            assert_eq!(v.count,v.max_records);
            let max_records=v.max_records;
            assert!(total<=usize::from(max_records)*500);
            assert_eq!(p.propose(&packet,101,500),0);
            observed.insert(max_records);
            above_old_2k|=total>2048;
        }
        assert!(observed.len()>=9,"random startup record cap not 20..30");
        assert!(above_old_2k,"must not restore old 2KiB total padding quota");
    }
    #[test]
    fn random_two_to_three_second_window_ends_and_never_restarts_live_flow(){
        let packet=udp(4041);
        for seed in 1..=128{
            let mut p=TunnelStartupPadding::new(StartupMode::Flows,seed);
            let _=p.propose(&packet,1000,500);
            let key=candidate(&packet,false).unwrap();
            let window=u64::from(p.seen[&key].window_ms);
            assert_eq!(p.seen[&key].count,1);
            // Not past the deadline, but still bounded by max_records.
            let _=p.propose(&packet,1000+window,500);
            assert_eq!(p.seen[&key].count,2);
            assert_eq!(p.propose(&packet,1000+window+1,500),0);
            assert_eq!(p.seen[&key].count,2);
            p.expire_coarse(1000+window+50_000);
            assert_eq!(p.len(),1,"spent live flow must not restart");
            assert_eq!(p.propose(&packet,999_999,500),0);
        }
    }
    #[test]
    fn actual_mtu_room_and_fragment_and_tls_mode(){
        let mut p=TunnelStartupPadding::new(StartupMode::Flows,77);
        let packet=udp(221);assert_eq!(p.propose(&packet,1,0),0);
        for i in 0..10{assert!(p.propose(&packet,i,13)<=13)}
        let mut fragment=udp(334);fragment[7]=1;
        assert_eq!(p.propose(&fragment,5,500),0);
        let mut tls=TunnelStartupPadding::new(StartupMode::Tls,17);
        assert_eq!(tls.propose(&packet,5,500),0);
    }
    #[test]
    fn fixed_256_flow_table_bounded_and_coarse_idle_reclaims(){
        let mut p=TunnelStartupPadding::new(StartupMode::Flows,7);
        for port in 1..=256{p.propose(&udp(port),0,500);}
        assert_eq!(p.len(),256);
        assert_eq!(p.propose(&udp(257),0,500),0);
        p.expire_coarse(120_001);
        assert!(p.len()<256);
        assert!(p.len()<=MAX_TRACKED);
    }
}
