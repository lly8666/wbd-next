//! Actual bounded FEC RX proof against real TX GF256/parity wire.
use crate::fec_rx::{FecRxOwner,Config,Direction,Scope,RxError,HEAVY_TTL_MS,COMPACT_TTL_MS};
use crate::fec_tx::FecTxOwner;
fn cfg(bytes:usize,compact:usize)->Config{
 Config{epoch:7,direction:Direction::ClientToServer,max_wire:1500,
  max_heavy_bytes:bytes,max_heavy_blocks:8,max_compact_blocks:compact,first_id_ext:1}
}
fn id(n:u64)->Scope{Scope{epoch:7,direction:Direction::ClientToServer,id_ext:n}}
fn wire(n:u64,profile:u8,items:&[&[u8]])->(Vec<Vec<u8>>,Vec<Vec<u8>>){
 let mut tx=FecTxOwner::new(n,100_000).unwrap();
 let mut source=Vec::new();let mut parity=Vec::new();
 for item in items{
  let mut batch=tx.submit(item,0,profile,1500,false).unwrap();
  source.append(&mut batch.systematic);parity.append(&mut batch.parity);
 }
 parity.append(&mut tx.flush_all(32).unwrap().parity);
 (source,parity)
}
#[test]
fn r1_rx_source_immediate_without_final_duplicate_cannot_extend_heavy(){
 let (s,p)=wire(1,4,&[b"first",b"second"]);
 let mut rx=FecRxOwner::new(cfg(1024,16)).unwrap();
 assert_eq!(rx.push_after_auth(&s[0],id(1),100).unwrap().systematic,
  vec![(0,b"first".to_vec())]);
 assert!(rx.push_after_auth(&s[0],id(1),2999).unwrap().systematic.is_empty());
 rx.expire(3099);assert_eq!(rx.stats().heavy,1);
 rx.expire(3100);assert_eq!((rx.stats().heavy,rx.stats().compact),(0,1));
 assert!(rx.push_after_auth(&p[0],id(1),3101).unwrap().recovered.is_empty());
 assert_eq!(rx.push_after_auth(&s[1],id(1),3102).unwrap().systematic,
  vec![(1,b"second".to_vec())]);
 assert!(rx.push_after_auth(&s[1],id(1),3103).unwrap().systematic.is_empty());
 assert_eq!(rx.stats().systematic,2);
}
#[test]
fn r1_rx_parity_first_final_e2_exact_go_k2_no_redelivery(){
 let (s,p)=wire(1,4,&[&[1,2,3],&[0xa0,0xb1,0xc2,0xd3,0xe4]]);
 let mut rx=FecRxOwner::new(cfg(1024,16)).unwrap();
 assert!(rx.push_after_auth(&p[1],id(1),1).unwrap().recovered.is_empty());
 let got=rx.push_after_auth(&p[0],id(1),2).unwrap();
 assert_eq!(got.recovered,vec![(0,vec![1,2,3]),(1,vec![0xa0,0xb1,0xc2,0xd3,0xe4])]);
 assert_eq!((rx.stats().heavy,rx.stats().compact),(0,1));
 assert!(rx.push_after_auth(&s[0],id(1),3).unwrap().systematic.is_empty());
 assert_eq!((rx.stats().systematic,rx.stats().recovered),(0,2));
}
#[test]
fn r1_rx_first_systematic_then_only_missing_e2_and_very_late_no_duplicate(){
 let (s,p)=wire(1,4,&[b"A",b"BC",b"DEF"]);
 let mut rx=FecRxOwner::new(cfg(1024,16)).unwrap();
 assert_eq!(rx.push_after_auth(&s[0],id(1),0).unwrap().systematic,
  vec![(0,b"A".to_vec())]);
 assert!(rx.push_after_auth(&p[0],id(1),1).unwrap().recovered.is_empty());
 let got=rx.push_after_auth(&p[1],id(1),2).unwrap();
 assert_eq!(got.recovered,vec![(1,b"BC".to_vec()),(2,b"DEF".to_vec())]);
 assert!(rx.push_after_auth(&s[2],id(1),3).unwrap().systematic.is_empty());
 assert_eq!((rx.stats().systematic,rx.stats().recovered),(1,2));
}
#[test]
fn r1_rx_malformed_final_metadata_mixed_profile_and_duplicate_body_fail_closed(){
 let (s,p)=wire(1,4,&[b"abc",b"zzzz"]);
 let mut rx=FecRxOwner::new(cfg(1024,16)).unwrap();
 rx.push_after_auth(&s[0],id(1),1).unwrap();
 let mut bad=p[0].clone();bad[17]=4;
 assert_eq!(rx.push_after_auth(&bad,id(1),2),Err(RxError::Metadata));
 assert_eq!(rx.push_after_auth(&p[0],id(1),3),Err(RxError::Metadata));
 let (next,_)=wire(2,4,&[b"abc",b"dd"]);
 rx.push_after_auth(&next[0],id(2),4).unwrap();
 let mut profile=next[0].clone();profile[10]=8;
 assert_eq!(rx.push_after_auth(&profile,id(2),5),Err(RxError::Metadata));
 let (third,_)=wire(3,4,&[b"abc",b"dd"]);
 rx.push_after_auth(&third[0],id(3),6).unwrap();
 let mut conflict=third[0].clone();*conflict.last_mut().unwrap()^=1;
 assert_eq!(rx.push_after_auth(&conflict,id(3),7),Err(RxError::Conflict));
 assert_eq!(rx.stats().conflicts,3);
 assert_eq!(rx.stats().systematic,3);
}
#[test]
fn r1_rx_pressure_compacts_recovery_work_but_keeps_first_delivery(){
 let (a,ap)=wire(1,4,&[b"first",b"other"]);
 let (b,_)=wire(2,4,&[b"later"]);
 let mut rx=FecRxOwner::new(cfg(7,16)).unwrap();
 rx.push_after_auth(&a[0],id(1),1).unwrap();
 rx.push_after_auth(&b[0],id(2),2).unwrap();
 assert!(rx.stats().heavy_bytes<=7);
 assert_eq!(rx.stats().compact,1);
 assert!(rx.push_after_auth(&ap[0],id(1),3).unwrap().recovered.is_empty());
 assert_eq!(rx.push_after_auth(&a[1],id(1),4).unwrap().systematic,
  vec![(1,b"other".to_vec())]);
 assert!(rx.push_after_auth(&a[1],id(1),5).unwrap().systematic.is_empty());
}
#[test]
fn r1_rx_explicit_floor_on_compact_capacity_and_ten_second_expiry(){
 let (a,_)=wire(1,4,&[b"old"]);
 let (b,_)=wire(2,4,&[b"new"]);
 let mut rx=FecRxOwner::new(cfg(32,1)).unwrap();
 rx.push_after_auth(&a[0],id(1),0).unwrap();
 rx.expire(HEAVY_TTL_MS);
 rx.push_after_auth(&b[0],id(2),3001).unwrap();
 rx.expire(6001);
 assert!(rx.stats().floor.unwrap_or(0)>=1);
 assert_eq!(rx.push_after_auth(&a[0],id(1),6002),Err(RxError::Retired));
 rx.expire(6001+COMPACT_TTL_MS);
 assert!(rx.stats().floor.unwrap_or(0)>=2);
 assert_eq!(rx.push_after_auth(&b[0],id(2),20_000),Err(RxError::Retired));
}
#[test]
fn r1_rx_scope_wrong_epoch_id_and_bad_wire_no_state_mutation(){
 let (s,_)=wire(1,4,&[b"hello"]);
 let mut rx=FecRxOwner::new(cfg(1024,16)).unwrap();
 let mut wrong=id(1);wrong.epoch=8;
 assert_eq!(rx.push_after_auth(&s[0],wrong,1),Err(RxError::WrongScope));
 assert_eq!(rx.push_after_auth(&s[0],id(2),1),Err(RxError::WrongScope));
 let mut bad=s[0].clone();bad[0]=0;
 assert!(matches!(rx.push_after_auth(&bad,id(1),1),Err(RxError::Wire(_))));
 assert_eq!((rx.stats().heavy,rx.stats().compact,rx.stats().floor),(0,0,Some(0)));
 assert_eq!(rx.push_after_auth(&s[0],id(1),2).unwrap().systematic,
  vec![(0,b"hello".to_vec())]);
}
#[test]
fn r1_rx_real_rs_full_erasure_six_profiles_streaming_late(){
 for r in [4u8,8,10,12,16,20]{
  let k=usize::from(r);
  let sources=(0..k).map(|i|(0..(i%7+1))
   .map(|j|(i*9+j*3) as u8).collect::<Vec<u8>>()).collect::<Vec<_>>();
  let refs=sources.iter().map(Vec::as_slice).collect::<Vec<_>>();
  let (systematic,parity)=wire(1,r,&refs);
  let mut rx=FecRxOwner::new(cfg(30_000,16)).unwrap();
  let mut recovered=Vec::new();
  for p in parity.iter().rev(){
   recovered.extend(rx.push_after_auth(p,id(1),1).unwrap().recovered);
  }
  recovered.sort_by_key(|(i,_)|*i);
  assert_eq!(recovered,sources.iter().enumerate()
   .map(|(i,x)|(i as u8,x.clone())).collect::<Vec<_>>());
  for s in &systematic{
   assert!(rx.push_after_auth(s,id(1),2).unwrap().systematic.is_empty());
  }
 }
}
