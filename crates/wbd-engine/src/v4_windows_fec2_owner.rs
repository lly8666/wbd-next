//! PLAN024 Windows original-Go feature7 M2/M3 source/repair transport:
//! actual M1 immutable record/PN sealer, same unique M3 receive bitmap
//! and existing M3 RS16 authenticated first delivery. No caller-provided
//! settings/ABI flag is an authenticated Go M2 Applied receipt, OS Apply,
//! native kernel submission or complete Fixed/Auto product qualification.
use super::*;
use crate::v4_fec2_live_rx::{Fec2LiveRx,VerifiedReceiveEpoch};
use wbd_codec::fec_v2;

#[repr(C)]
#[derive(Clone,Copy)]
pub struct WbdWindowsFec2FirstDeliveryV4 {
    pub block_id:u64,
    pub index:u32,
    pub length:u32,
    pub recovered:u32,
    pub frame:[u8;2048],
}
fn frame_scope(e:&Entry)->VerifiedReceiveEpoch{
    VerifiedReceiveEpoch{
        generation:e.generation,
        epoch:e.authenticated_epoch,
        negotiated_features:7,
        direction_s2c:!e.role_server,
    }
}
pub(super) fn seal_symbol(
    r:&Registry,h:u64,epoch:[u8;16],luid:u64,ifindex:u32,
    kind:u8,frame:&[u8],out:&mut [u8],
)->Result<(usize,u32,u64),i32>{
    let lane=r.entries.get(&h).ok_or(UNKNOWN)?;
    let mut e=lane.lock().map_err(|_|BAD_STAGE)?;
    seal_symbol_entry(&mut e,epoch,luid,ifindex,kind,frame,out)
}
fn seal_symbol_entry(e:&mut Entry,epoch:[u8;16],luid:u64,ifindex:u32,
    kind:u8,frame:&[u8],out:&mut [u8]
)->Result<(usize,u32,u64),i32>{
    if !v3_ready(e,epoch,luid,ifindex)||!matches!(kind,2|3)||
       frame.len()<10||frame.len()>2048||out.len()<frame.len()+31{
       return Err(INVALID)
    }
    if !e.feature7||e.game_group.is_some(){return Err(INVALID)}
    let budget=normal_off_windows_budget(&e)?;
    if frame.len()>budget.record_payload_mtu{return Err(INVALID)}
    let valid=match kind {
        2=>fec_v2::parse_source(frame,budget.record_payload_mtu).is_ok(),
        3=>fec_v2::parse_repair(frame,budget.record_payload_mtu).is_ok(),
        _=>false,
    };
    if !valid{return Err(INVALID)}
    let mut slab=e.arena.allocate().map_err(|_|FULL)?;
    slab.writable()[14..14+frame.len()].copy_from_slice(frame);
    let (pn,seq,used)=e.owner.seal_fec2_product_one(
        slab,frame.len(),kind,budget,0,epoch,MonoNs(0)
    ).map_err(|_|BAD_STAGE)?;
    let batch=e.owner.drain_tx(MonoNs(0),Vec::with_capacity(1))
        .map_err(|_|BAD_STAGE)?;
    let accepted=(||{
        let ready=e.owner.checked_tx_ready(&batch).map_err(|_|BAD_STAGE)?;
        if ready.len()!=1||ready[0].record.bytes().len()!=used ||
           used>out.len(){return Err(BAD_STAGE)}
        out[..used].copy_from_slice(ready[0].record.bytes());
        Ok((used,seq,pn))
    })();
    let _=batch.recycle();
    accepted
}
pub(super) fn open_symbol(
    r:&Registry,h:u64,epoch:[u8;16],luid:u64,ifindex:u32,
    seq:u32,wire:&[u8],
)->Result<Vec<WbdWindowsFec2FirstDeliveryV4>,i32>{
    let lane=r.entries.get(&h).ok_or(UNKNOWN)?;
    let mut e=lane.lock().map_err(|_|BAD_STAGE)?;
    open_symbol_entry(&mut e,epoch,luid,ifindex,seq,wire)
}
fn open_symbol_entry(e:&mut Entry,epoch:[u8;16],luid:u64,ifindex:u32,
    seq:u32,wire:&[u8],
)->Result<Vec<WbdWindowsFec2FirstDeliveryV4>,i32>{
    if !v3_ready(e,epoch,luid,ifindex)||
       wire.len()<=FIXED_WIRE_OVERHEAD||wire.len()>2048{
       return Err(INVALID)
    }
    if !e.feature7||e.game_group.is_some(){return Err(INVALID)}
    let scope=frame_scope(&e);
    if e.fec2_rx.is_none(){
        let limit=normal_off_windows_budget(&e)?.record_wire_mtu;
        e.fec2_rx=Some(Fec2LiveRx::from_authenticated_scope(scope,limit)
            .map_err(|_|INVALID)?);
    }
    let mut slab=e.arena.allocate().map_err(|_|FULL)?;
    slab.writable()[..wire.len()].copy_from_slice(wire);
    let unfolded=m0_tcp_unwrap(&e,seq,wire.len())?;
    e.owner.offer_after_active(slab,0..wire.len(),unfolded,MonoNs(0))
        .map_err(|_|INVALID)?;
    let mut result=Vec::new();
    let mut failed=false;
    // Split the actual Entry fields, not the MutexGuard deref, so Rust
    // guarantees one unique RX owner and distinct bounded RS16 decoder.
    let entry:&mut Entry=e;
    let decoder=entry.fec2_rx.as_mut().ok_or(BAD_STAGE)?;
    let (storage,report)=entry.owner.drain_windows_authenticated_fec2(
        MonoNs(0),Vec::with_capacity(1),|_pn,kind,plain|{
            match decoder.accept_authenticated(scope,kind,plain,MonoNs(0)){
                Ok(deliveries)=>{
                    for d in deliveries {
                        if d.frame.len()>2048||result.len()>=16{
                            failed=true;break
                        }
                        let mut out=WbdWindowsFec2FirstDeliveryV4{
                            block_id:d.block_id,index:u32::from(d.index),
                            length:d.frame.len() as u32,
                            recovered:u32::from(d.recovered),
                            frame:[0;2048],
                        };
                        out.frame[..d.frame.len()].copy_from_slice(&d.frame);
                        result.push(out);
                    }
                },
                Err(_)=>failed=true,
            }
        }
    ).map_err(|_|BAD_STAGE)?;
    drop(storage);
    if failed||report.rejected!=0||report.link_ready!=1||
        report.control_ready!=0{return Err(INVALID)}
    e.rx_unwrapped_high=e.rx_unwrapped_high.max(unfolded+wire.len() as u64);
    Ok(result)
}
fn epoch(ptr:*const u8,len:usize)->Option<[u8;16]>{
    v3_epoch(ptr,len)
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v4_fec2_seal(
    h:u64,ep:*const u8,ep_len:usize,luid:u64,ifindex:u32,
    kind:u32,payload:*const u8,len:usize,out:*mut u8,capacity:usize,
    used:*mut usize,seq:*mut u32,pn:*mut u64,
)->i32{
    if payload.is_null()||out.is_null()||used.is_null()||
       seq.is_null()||pn.is_null()||len<10||len>2048||
       capacity<len+31||capacity>65535||!matches!(kind,2|3){
       return INVALID
    }
    let Some(exact)=epoch(ep,ep_len)else{return INVALID};
    let src=payload as usize;let dst=out as usize;
    if src.checked_add(len).is_none_or(|end|
        dst<end&&src<dst.saturating_add(capacity)){return INVALID}
    let input=unsafe{std::slice::from_raw_parts(payload,len)};
    let buffer=unsafe{std::slice::from_raw_parts_mut(out,capacity)};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    match seal_symbol_entry(&mut e,exact,luid,ifindex,kind as u8,input,buffer){
        Ok((n,s,p))=>{unsafe{used.write(n);seq.write(s);pn.write(p)};OK},
        Err(e)=>e,
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v4_fec2_open(
    h:u64,ep:*const u8,ep_len:usize,luid:u64,ifindex:u32,
    seq:u32,wire:*const u8,len:usize,
    deliveries:*mut WbdWindowsFec2FirstDeliveryV4,capacity:u32,
    count:*mut u32,
)->i32{
    if wire.is_null()||deliveries.is_null()||count.is_null()||
       len<=FIXED_WIRE_OVERHEAD||len>2048||capacity==0||capacity>16{
       return INVALID
    }
    let Some(exact)=epoch(ep,ep_len)else{return INVALID};
    let input=unsafe{std::slice::from_raw_parts(wire,len)};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    match open_symbol_entry(&mut e,exact,luid,ifindex,seq,input){
        Ok(out) if out.len()<=capacity as usize=>{
            for (i,record) in out.iter().enumerate(){
                unsafe{deliveries.add(i).write(*record)}
            }
            unsafe{count.write(out.len() as u32)}
            OK
        },
        _=>INVALID,
    }
}

#[cfg(test)]
mod tests{
    use super::*;
    use wbd_codec::fec_v2::{Rs16,Profile,BackendChoice};
    fn cold(server:bool)->[u8;COLD_V4_LEN]{
        let mut a=[0;COLD_V4_LEN];
        a[..4].copy_from_slice(b"WBCO");
        a[4..6].copy_from_slice(&1u16.to_be_bytes());
        a[6..8].copy_from_slice(&(COLD_V4_LEN as u16).to_be_bytes());
        a[8]=u8::from(server);a[9]=1;a[10]=1;
        a[12..28].fill(1);a[28..44].fill(2);a[44..60].fill(3);
        a[60..62].copy_from_slice(&1400u16.to_be_bytes());
        a[62..64].copy_from_slice(&1400u16.to_be_bytes());
        a[64..96].fill(4);a[96..172].fill(5);a[172..].fill(6);a
    }
    fn cmd()->[u8;HANDOFF_V1_LEN]{
        let mut a=[0;HANDOFF_V1_LEN];
        a[..4].copy_from_slice(b"WBGH");
        a[4..6].copy_from_slice(&2u16.to_be_bytes());
        a[6..8].copy_from_slice(&(HANDOFF_V1_LEN as u16).to_be_bytes());
        a[8..12].copy_from_slice(&[10,25,0,2]);a[12..16].copy_from_slice(&[10,25,0,1]);
        a[16..18].copy_from_slice(&41001u16.to_be_bytes());
        a[18..20].copy_from_slice(&443u16.to_be_bytes());
        a[20..24].copy_from_slice(&500u32.to_be_bytes());
        a[24..26].copy_from_slice(&1360u16.to_be_bytes());a[26]=1;
        a[27..29].copy_from_slice(&7u16.to_be_bytes());a
    }
    fn setup(r:&mut Registry,server:bool,luid:u64,index:u32)->u64{
        let h=allocate(r,&cold(server),&cmd(),server).unwrap();
        assert_eq!(commit(r,h,0,0,600),OK);
        assert_eq!(bind_wintun(r,h,[2;16],luid,index),OK);
        assert!(set_path_mtu(r,h,[2;16],luid,index,1400).is_ok());
        h
    }
    fn data(byte:u8)->Vec<u8>{
        let mut p=vec![0u8;40];p[0]=0x45;p[2..4].copy_from_slice(&40u16.to_be_bytes());
        p[8]=64;p[9]=17;p[20..].fill(byte);p
    }
    fn send(r:&mut Registry,h:u64,luid:u64,ifindex:u32,kind:u8,plain:&[u8])
        ->(Vec<u8>,u32,u64){
        let mut out=[0u8;800];
        let (n,seq,pn)=seal_symbol(r,h,[2;16],luid,ifindex,kind,plain,&mut out)
            .expect("genuine original Rust M1 immutable M3 FEC AEAD");
        (out[..n].to_vec(),seq,pn)
    }
    #[test]
    fn m0_windows_native_fec2_original_owner_aead_first_delivery_rs16_and_stop(){
        let mut r=Registry{
            generation:1,entries:BTreeMap::new(),game_groups:BTreeMap::new(),
        };
        let client=setup(&mut r,false,101,11);
        let server=setup(&mut r,true,102,12);
        let budget=normal_off_windows_budget(&r.entries[&client].lock().unwrap()).unwrap();
        let a=data(1);let b=data(2);
        let source=fec_v2::source_owned(1,0,&a,budget.record_payload_mtu).unwrap();
        assert_eq!(seal_symbol(&mut r,client,[9;16],101,11,2,&source,&mut [0;800]),
            Err(INVALID));
        assert_eq!(seal_symbol(&mut r,client,[2;16],101,11,1,&source,&mut [0;800]),
            Err(INVALID));
        let (wire,seq,pn)=send(&mut r,client,101,11,2,&source);
        assert_eq!(pn,0);
        let delivered=open_symbol(&mut r,server,[2;16],102,12,seq,&wire).unwrap();
        assert_eq!(delivered.len(),1);
        assert_eq!(&delivered[0].frame[..delivered[0].length as usize],a.as_slice());
        assert_eq!(delivered[0].recovered,0);
        assert!(open_symbol(&mut r,server,[2;16],102,12,seq,&wire).is_err());
        let s1=fec_v2::source_owned(2,1,&b,budget.record_payload_mtu).unwrap();
        let (wire1,seq1,_)=send(&mut r,client,101,11,2,&s1);
        let actual=open_symbol(&mut r,server,[2;16],102,12,seq1,&wire1).unwrap();
        assert_eq!(actual.len(),1);
        assert_eq!(&actual[0].frame[..actual[0].length as usize],b.as_slice());
        let codec=Rs16::new();
        let (repair,_)=codec.encode_owned(2,&[&a,&b],Profile::Strong,0,1,
            budget.record_payload_mtu,BackendChoice::Scalar).unwrap();
        let (sealed,repair_seq,_)=send(&mut r,client,101,11,3,&repair[0]);
        let recovered=open_symbol(&mut r,server,[2;16],102,12,repair_seq,&sealed).unwrap();
        assert_eq!(recovered.len(),1);
        assert_eq!(&recovered[0].frame[..recovered[0].length as usize],a.as_slice());
        assert_eq!(recovered[0].recovered,1);
        let mut corrupt=sealed;*corrupt.last_mut().unwrap()^=1;
        assert!(open_symbol(&mut r,server,[2;16],102,12,repair_seq+128,&corrupt).is_err());
        assert_eq!(quiesce_wintun(&mut r,client,[2;16],101,11),OK);
        assert_eq!(quiesce_wintun(&mut r,server,[2;16],102,12),OK);
        assert_eq!(stop(&mut r,client),OK);
        assert_eq!(stop(&mut r,server),OK);
        assert_eq!(release(&mut r,client),OK);
        assert_eq!(release(&mut r,server),OK);
        assert_eq!(PRODUCT_APPLIED,0);
    }
}
