//! PLAN029 bounded startup-padding budget for original authenticated
//! Tunnel DATA. Only the old Rust M1 LINK seal may consume the returned
//! padding: this module never emits a packet, creates a thread/timer, or
//! touches Direct sockets. It deliberately cannot authorize TLS changes.
use std::collections::{HashMap,VecDeque};
use crate::v4_client_split::FlowKey;

const MAX_TRACKED:usize=256;
const MAX_RECORDS:u8=12;
const MAX_FLOW_PAD:u16=2048;
const MAX_RECORD_PAD:usize=256;
const FLOW_IDLE_MS:u64=120_000;
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) enum StartupMode{Off,Tls,Flows}

struct Seen{
    first_ms:u64,last_ms:u64,window_ms:u16,
    count:u8,business:u32,padded:u16,
    state:u64,
}
pub(crate) struct TunnelStartupPadding{
    mode:StartupMode,
    seen:HashMap<FlowKey,Seen>,
    rotation:VecDeque<FlowKey>,
    state:u64,
}
fn next_random(x:&mut u64)->u64{
    // One keyed per-generation PRNG seed is supplied by authenticated
    // owner; never used as cipher, TLS or connection entropy.
    let mut v=(*x).max(1);
    v^=v<<13;v^=v>>7;v^=v<<17;*x=v;v
}
fn candidate(packet:&[u8],tls_only:bool)->Option<(FlowKey,usize)>{
    if packet.len()<28||packet[0]>>4!=4{return None}
    let ihl=usize::from(packet[0]&15)*4;
    if ihl<20||ihl+8>packet.len()||
        u16::from_be_bytes(packet[2..4].try_into().ok()?) as usize!=packet.len()||
        (u16::from_be_bytes(packet[6..8].try_into().ok()?)&0x1fff)!=0{
        return None
    }
    let proto=packet[9];
    if proto!=6&&proto!=17{return None}
    let base=if proto==6{
        if packet.len()<ihl+20{return None}
        let hdr=usize::from(packet[ihl+12]>>4)*4;
        if hdr<20||ihl+hdr>=packet.len(){return None}
        ihl+hdr
    }else{
        let len=u16::from_be_bytes(packet[ihl+4..ihl+6].try_into().ok()?) as usize;
        if len!=packet.len()-ihl||len<=8{return None}
        ihl+8
    };
    if tls_only&&!(proto==6&&packet.len()>=base+5&&
       packet[base]==22&&packet[base+1]==3&&
       packet[base+2]<=4){return None}
    Some((FlowKey{
        source:u32::from_be_bytes(packet[12..16].try_into().ok()?),
        destination:u32::from_be_bytes(packet[16..20].try_into().ok()?),
        source_port:u16::from_be_bytes(packet[ihl..ihl+2].try_into().ok()?),
        destination_port:u16::from_be_bytes(packet[ihl+2..ihl+4].try_into().ok()?),
        protocol:proto,
    },packet.len()-base))
}
impl TunnelStartupPadding{
    pub(crate) fn new(mode:StartupMode,authenticated_seed:u64)->Self{
        Self{mode,seen:HashMap::new(),rotation:VecDeque::new(),
            state:authenticated_seed.max(1)}
    }
    pub(crate) fn len(&self)->usize{self.seen.len()}
    // Caller invokes only AFTER classifying Tunnel and computing actual
    // M1 LINK record room. Off is a single branch: no clock, parse, table,
    // PRNG, or allocations; Direct must never invoke this API.
    pub(crate) fn propose(&mut self,packet:&[u8],now_ms:u64,
        current_wire_room:usize)->usize{
        if self.mode==StartupMode::Off||current_wire_room==0{return 0}
        let Some((key,payload))=candidate(packet,self.mode==StartupMode::Tls)
            else{return 0};
        if !self.seen.contains_key(&key){
            if self.seen.len()>=MAX_TRACKED{return 0}
            let seed=next_random(&mut self.state);
            let window=1000+(seed%1001) as u16;
            self.seen.insert(key,Seen{first_ms:now_ms,last_ms:now_ms,
                window_ms:window,count:0,business:0,padded:0,state:seed});
            self.rotation.push_back(key);
        }
        let Some(flow)=self.seen.get_mut(&key)else{return 0};
        flow.last_ms=now_ms;
        if now_ms.saturating_sub(flow.first_ms)>u64::from(flow.window_ms)||
            flow.count>=MAX_RECORDS{return 0}
        flow.count+=1;
        flow.business=flow.business.saturating_add(payload as u32);
        let allowed=(flow.business/10).saturating_sub(u32::from(flow.padded)) as usize;
        let max=current_wire_room.min(MAX_RECORD_PAD)
            .min(usize::from(MAX_FLOW_PAD-flow.padded)).min(allowed);
        if max==0{return 0}
        let n=(next_random(&mut flow.state) as usize)%(max+1);
        flow.padded+=n as u16;n
    }
    // Existing original TX owner calls at its coarse due tick, never per
    // packet. Rotate max 8 known flows; long live flows retain their done
    // state until actual idle, so no repeating 30s startup pattern.
    pub(crate) fn expire_coarse(&mut self,now_ms:u64){
        for _ in 0..8{
            let Some(key)=self.rotation.pop_front()else{break};
            let Some(v)=self.seen.get(&key)else{continue};
            if now_ms.saturating_sub(v.last_ms)>=FLOW_IDLE_MS{
                self.seen.remove(&key);
            }else{self.rotation.push_back(key);}
        }
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    fn udp(src_port:u16)->Vec<u8>{
        let mut p=vec![0u8;44];p[0]=0x45;
        p[2..4].copy_from_slice(&44u16.to_be_bytes());
        p[9]=17;p[12..16].copy_from_slice(&[10,66,0,2]);
        p[16..20].copy_from_slice(&[203,0,113,77]);
        p[20..22].copy_from_slice(&src_port.to_be_bytes());
        p[22..24].copy_from_slice(&443u16.to_be_bytes());
        p[24..26].copy_from_slice(&24u16.to_be_bytes());p
    }
    #[test]
    fn off_never_allocates_or_fills_and_direct_not_called(){
        let mut p=TunnelStartupPadding::new(StartupMode::Off,123);
        for _ in 0..300{assert_eq!(p.propose(&udp(1),0,300),0)}
        assert_eq!(p.len(),0);
    }
    #[test]
    fn flow_has_12_records_2k_cap_10pct_and_no_restart_without_idle(){
        let mut p=TunnelStartupPadding::new(StartupMode::Flows,13);
        let packet=udp(11);
        let mut total=0;
        for _ in 0..100{
            let n=p.propose(&packet,1,500);
            assert!(n<=256);
            total+=n;
        }
        assert!(total<=12*(packet.len()-28)/10);
        assert!(total<=2048);
        assert_eq!(p.len(),1);
        assert_eq!(p.propose(&packet,30_000,300),0);
        p.expire_coarse(30_000);
        assert_eq!(p.len(),1);
        p.expire_coarse(160_001);
        assert_eq!(p.len(),0);
    }
    #[test]
    fn hard_256_only_suppresses_padding_never_business_or_growth(){
        let mut p=TunnelStartupPadding::new(StartupMode::Flows,13);
        for port in 1..=256{p.propose(&udp(port),0,512);}
        assert_eq!(p.len(),256);
        assert_eq!(p.propose(&udp(257),0,512),0);
        p.expire_coarse(120_001);
        assert!(p.len()<256);
        assert!(p.len()<=MAX_TRACKED);
    }
    #[test]
    fn no_fragment_no_empty_udp_no_tls_guess(){
        let mut p=TunnelStartupPadding::new(StartupMode::Tls,99);
        assert_eq!(p.propose(&udp(11),0,256),0);
        assert_eq!(p.len(),0);
        let mut fragment=udp(11);
        fragment[7]=1;
        assert_eq!(TunnelStartupPadding::new(StartupMode::Flows,2)
            .propose(&fragment,0,256),0);
    }
}
