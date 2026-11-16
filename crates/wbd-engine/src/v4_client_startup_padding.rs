//! PLAN029 independent 0..500B per eligible encrypted Tunnel LINK record.
//! Only original authenticated Normal M1 may consume proposals;
//! no per-flow budget, timer, socket, Direct write or extra thread.
const MAX_RECORD_PAD:usize=500;
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) enum StartupMode{Off,Tls,Flows}
pub(crate) struct TunnelStartupPadding{mode:StartupMode,state:u64}
fn next_random(x:&mut u64)->u64{
 let mut v=(*x).max(1);v^=v<<13;v^=v>>7;v^=v<<17;*x=v;v
}
fn candidate(packet:&[u8],tls_only:bool)->bool{
    if packet.len()<28||packet[0]>>4!=4{return false}
    let ihl=usize::from(packet[0]&15)*4;
    if ihl<20||ihl+8>packet.len()||
        u16::from_be_bytes([packet[2],packet[3]]) as usize!=packet.len()||
        (u16::from_be_bytes([packet[6],packet[7]])&0x1fff)!=0{
        return false
    }
    let proto=packet[9];
    if proto!=6&&proto!=17{return false}
    let base=if proto==6{
        if packet.len()<ihl+20{return false}
        let hdr=usize::from(packet[ihl+12]>>4)*4;
        if hdr<20||ihl+hdr>=packet.len(){return false}
        ihl+hdr
    }else{
        let len=u16::from_be_bytes([packet[ihl+4],packet[ihl+5]]) as usize;
        if len!=packet.len()-ihl||len<=8{return false}
        ihl+8
    };
    if tls_only&&!(proto==6&&packet.len()>=base+5&&
       packet[base]==22&&packet[base+1]==3&&
       packet[base+2]<=4){return false}
    true
}
impl TunnelStartupPadding{
 pub(crate) fn new(mode:StartupMode,authenticated_seed:u64)->Self{
  Self{mode,state:authenticated_seed.max(1)}
 }
 pub(crate) fn mode_name(&self)->&'static str{
  match self.mode{StartupMode::Off=>"off",StartupMode::Tls=>"tls",StartupMode::Flows=>"flows"}
 }
 // Only caller-supplied real M1 record MTU room limits per-record fill.
 // Keep legacy now arg; no per-flow or time accounting/allocations.
 pub(crate) fn propose(&mut self,packet:&[u8],_now_ms:u64,room:usize)->usize{
  if self.mode==StartupMode::Off||room==0{return 0}
  if !candidate(packet,self.mode==StartupMode::Tls){return 0}
  let maximum=room.min(MAX_RECORD_PAD);
  (next_random(&mut self.state) as usize)%(maximum+1)
 }
 pub(crate) fn expire_coarse(&mut self,_now_ms:u64){}
}
#[cfg(test)]
mod tests{
 use super::*;
 fn udp()->Vec<u8>{
  let mut p=vec![0u8;44];p[0]=0x45;
  p[2..4].copy_from_slice(&44u16.to_be_bytes());p[9]=17;
  p[12..16].copy_from_slice(&[10,66,0,2]);p[16..20].copy_from_slice(&[203,0,113,77]);
  p[20..22].copy_from_slice(&2345u16.to_be_bytes());
  p[22..24].copy_from_slice(&443u16.to_be_bytes());
  p[24..26].copy_from_slice(&24u16.to_be_bytes());p
 }
 #[test]
 fn off_never_spends_random_or_padding(){let mut p=TunnelStartupPadding::new(StartupMode::Off,123);
  for _ in 0..2048{assert_eq!(p.propose(&udp(),0,500),0)}
 }
 #[test]
 fn all_records_keep_randomizing_after_old_2k_and_12record_budgets(){
  let mut p=TunnelStartupPadding::new(StartupMode::Flows,13);
  let pkt=udp();let(mut low,mut high,mut total)=(500usize,0usize,0usize);
  for i in 0..8192{
   let n=p.propose(&pkt,i*10000,500);
   low=low.min(n);high=high.max(n);total+=n;
   assert!(n<=500);
  }
  assert_eq!(low,0);assert_eq!(high,500);
  assert!(total>100*2048,"old per-flow ceiling must not suppress subsequent records");
  p.expire_coarse(1_000_000);
  assert!(p.propose(&pkt,1_000_001,500)<=500);
 }
 #[test]
 fn per_record_mtu_room_and_dns_safety(){
  let mut p=TunnelStartupPadding::new(StartupMode::Flows,25);
  assert_eq!(p.propose(&udp(),0,0),0);
  for _ in 0..1000{assert!(p.propose(&udp(),0,13)<=13)}
  let mut fragment=udp();fragment[7]=1;
  assert_eq!(p.propose(&fragment,0,500),0);
  let mut tls=TunnelStartupPadding::new(StartupMode::Tls,15);
  assert_eq!(tls.propose(&udp(),0,500),0);
 }
}
