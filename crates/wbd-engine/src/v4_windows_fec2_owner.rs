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
    pub frame:[u8;512],
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
    r:&mut Registry,h:u64,epoch:[u8;16],luid:u64,ifindex:u32,
    kind:u8,frame:&[u8],out:&mut [u8],
)->Result<(usize,u32,u64),i32>{
    if !v3_ready(r,h,epoch,luid,ifindex)||!matches!(kind,2|3)||
       frame.len()<10||frame.len()>512||out.len()<frame.len()+31{
       return Err(INVALID)
    }
    let e=r.entries.get_mut(&h).ok_or(UNKNOWN)?;
    if !e.feature7||e.game_group.is_some(){return Err(INVALID)}
    let budget=normal_off_windows_budget(e)?;
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
    r:&mut Registry,h:u64,epoch:[u8;16],luid:u64,ifindex:u32,
    seq:u32,wire:&[u8],
)->Result<Vec<WbdWindowsFec2FirstDeliveryV4>,i32>{
    if !v3_ready(r,h,epoch,luid,ifindex)||
       wire.len()<=FIXED_WIRE_OVERHEAD||wire.len()>543{
       return Err(INVALID)
    }
    let e=r.entries.get_mut(&h).ok_or(UNKNOWN)?;
    if !e.feature7||e.game_group.is_some(){return Err(INVALID)}
    let scope=frame_scope(e);
    if e.fec2_rx.is_none(){
        let limit=normal_off_windows_budget(e)?.record_wire_mtu;
        e.fec2_rx=Some(Fec2LiveRx::from_authenticated_scope(scope,limit)
            .map_err(|_|INVALID)?);
    }
    let mut slab=e.arena.allocate().map_err(|_|FULL)?;
    slab.writable()[..wire.len()].copy_from_slice(wire);
    e.owner.offer_after_active(slab,0..wire.len(),u64::from(seq),MonoNs(0))
        .map_err(|_|INVALID)?;
    let mut result=Vec::new();
    let mut failed=false;
    let decoder=e.fec2_rx.as_mut().ok_or(BAD_STAGE)?;
    let (storage,report)=e.owner.drain_windows_authenticated_fec2(
        MonoNs(0),Vec::with_capacity(1),|_pn,kind,plain|{
            match decoder.accept_authenticated(scope,kind,plain,MonoNs(0)){
                Ok(deliveries)=>{
                    for d in deliveries {
                        if d.frame.len()>512||result.len()>=16{
                            failed=true;break
                        }
                        let mut out=WbdWindowsFec2FirstDeliveryV4{
                            block_id:d.block_id,index:u32::from(d.index),
                            length:d.frame.len() as u32,
                            recovered:u32::from(d.recovered),
                            frame:[0;512],
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
       seq.is_null()||pn.is_null()||len<10||len>512||
       capacity<len+31||capacity>65535||!matches!(kind,2|3){
       return INVALID
    }
    let Some(exact)=epoch(ep,ep_len)else{return INVALID};
    let src=payload as usize;let dst=out as usize;
    if src.checked_add(len).is_none_or(|end|
        dst<end&&src<dst.saturating_add(capacity)){return INVALID}
    let input=unsafe{std::slice::from_raw_parts(payload,len)};
    let buffer=unsafe{std::slice::from_raw_parts_mut(out,capacity)};
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    match seal_symbol(&mut r,h,exact,luid,ifindex,kind as u8,input,buffer){
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
       len<=FIXED_WIRE_OVERHEAD||len>543||capacity==0||capacity>16{
       return INVALID
    }
    let Some(exact)=epoch(ep,ep_len)else{return INVALID};
    let input=unsafe{std::slice::from_raw_parts(wire,len)};
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    match open_symbol(&mut r,h,exact,luid,ifindex,seq,input){
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
