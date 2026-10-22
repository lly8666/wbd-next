//! PLAN024: Windows M4-independent, real original-TLS-derived 2/4-lane
//! Rust GameAdapter ownership, AEAD/PN, de-dup and exact Stop fence.
//! This is the private native crypto/record boundary only: transferring a
//! record into a Go buffer is NOT a kernel copy, OS Applied or product PASS.
//! The public Go owner must still supply independently verified real TLS
//! sessions and its own Wintun drivers for every lane.
use super::*;
use crate::v4_game_lane::GameAdapter;
use wbd_types::{MonoNs,LaneKey,TunnelKey};

pub(super) struct WinGameGroup {
    adapter:GameAdapter,
    handles:Vec<u64>,
    generation:u32,
    epoch:[u8;16],
    tick:u64,
}
#[repr(C)]
#[derive(Clone,Copy)]
pub struct WbdWindowsGameRecordV4{
    pub lane:u32,
    pub length:u32,
    pub pn:u64,
    pub logical_id:u64,
    pub wire:[u8;1536],
}
pub(super) fn join(
    r:&mut Registry,handles:&[u64],server:bool,
)->Result<u64,i32>{
    if !matches!(handles.len(),2|4)||r.game_groups.len()>=MAX_SESSIONS/2{
        return Err(INVALID)
    }
    let mut ids=handles.to_vec();
    ids.sort_unstable();ids.dedup();
    if ids.len()!=handles.len(){return Err(INVALID)}
    // All lanes must be independently committed by original Go TLS, with
    // distinct live kernel Wintun holds. No cold248 input arrives here.
    let mut scope=None;
    for h in &ids {
        let e=r.entries.get(h).ok_or(UNKNOWN)?;
        if e.phase!=PH_ACTIVE||e.role_server!=server||
            e.game_group.is_some()||e.feature7!=true||
            e.game_cold.is_none()||
            !e.device.is_some_and(|d|!d.quiesced){
            return Err(BAD_STAGE)
        }
        let cold=e.game_cold.as_ref().ok_or(BAD_STAGE)?;
        let identity=cold.identity();
        if identity.go_lane_id==0||
            usize::from(identity.go_lane_id)>handles.len()||
            identity.logical_epoch!=e.authenticated_epoch{
            return Err(INVALID)
        }
        if let Some(prior)=scope {
            if prior!=identity.logical_epoch{return Err(INVALID)}
        }else{scope=Some(identity.logical_epoch)}
    }
    // Transferring the sole cold object consumes this generation's future
    // group-install authority. A failed independent-lane crypto constructor
    // is terminal for those lane sessions; no fallback/retry key duplication.
    let cold=ids.iter().map(|h|
        r.entries.get_mut(h).and_then(|e|e.game_cold.take()).ok_or(BAD_STAGE)
    ).collect::<Result<Vec<_>,_>>()?;
    let generation=r.generation;
    let next=generation.checked_add(1).ok_or(FULL)?;
    let group=(u64::from(generation)<<32)|0x474Du64;
    if r.game_groups.contains_key(&group){return Err(FULL)}
    let adapter=GameAdapter::from_private_original_go_tls(
        cold,server,TunnelKey{slot:14,generation},generation,
    ).map_err(|_|INVALID)?;
    r.generation=next;
    for h in &ids {
        r.entries.get_mut(h).ok_or(UNKNOWN)?.game_group=Some(group);
    }
    r.game_groups.insert(group,WinGameGroup{
        adapter,handles:ids,generation,
        epoch:scope.ok_or(INVALID)?,tick:0,
    });
    Ok(group)
}
fn stopped_group(r:&mut Registry,h:u64)->i32{
    let Some(g)=r.game_groups.get(&h)else{return UNKNOWN};
    if g.handles.iter().any(|lane|r.entries.get(lane).is_none_or(|e|
        e.game_group!=Some(h)||e.phase!=PH_ACTIVE||
        !e.device.is_some_and(|d|d.quiesced))){
        return STOP_INCOMPLETE
    }
    let Some(mut game)=r.game_groups.remove(&h)else{return UNKNOWN};
    game.adapter.stop();
    for lane in game.handles {
        if let Some(e)=r.entries.get_mut(&lane){e.game_group=None}
    }
    OK
}
pub(super) fn offer_records(
    r:&mut Registry,h:u64,payload:&[u8],max:usize,
)->Result<Vec<WbdWindowsGameRecordV4>,i32>{
    if payload.len()<20||payload.len()>1200||payload[0]>>4!=4||
        payload[0]&15<5||max<2||max>4{
        return Err(INVALID)
    }
    let game=r.game_groups.get_mut(&h).ok_or(UNKNOWN)?;
    if max<game.handles.len(){return Err(INVALID)}
    if game.handles.iter().any(|lane|r.entries.get(lane).is_none_or(|e|
        e.game_group!=Some(h)||e.phase!=PH_ACTIVE||
        !e.device.is_some_and(|d|!d.quiesced))){
        return Err(BAD_STAGE)
    }
    game.tick=game.tick.checked_add(2).ok_or(FULL)?;
    let now=MonoNs(game.tick);
    game.adapter.offer(payload,now).map_err(|_|INVALID)?;
    let mut staged=Vec::new();
    let copied=game.adapter.drain(MonoNs(game.tick+1),|lane,id,pn,wire|{
        if wire.len()>1536{return false}
        let mut record=WbdWindowsGameRecordV4{
            lane:lane.slot,length:wire.len() as u32,pn,
            logical_id:id.0,wire:[0;1536]
        };
        record.wire[..wire.len()].copy_from_slice(wire);
        staged.push(record);
        true // copied to this bounded temporary, NOT to a kernel driver
    });
    if copied!=game.handles.len()||staged.len()!=copied{
        return Err(BAD_STAGE)
    }
    Ok(staged)
}
pub(super) fn receive_record(
    r:&mut Registry,h:u64,lane:u32,wire:&[u8],
)->Result<Option<Vec<u8>>,i32>{
    if wire.len()<32||wire.len()>1536{return Err(INVALID)}
    let game=r.game_groups.get_mut(&h).ok_or(UNKNOWN)?;
    if lane==0||usize::try_from(lane).ok().is_none_or(|v|v>game.handles.len()){
        return Err(INVALID)
    }
    if game.handles.iter().any(|id|r.entries.get(id).is_none_or(|e|
        e.game_group!=Some(h)||e.phase!=PH_ACTIVE||
        !e.device.is_some_and(|d|!d.quiesced))){
        return Err(BAD_STAGE)
    }
    let key=LaneKey{
        tunnel:TunnelKey{slot:14,generation:game.generation},
        slot:lane,generation:game.generation,
    };
    game.adapter.receive(key,wire.to_vec()).map_err(|_|INVALID)
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v4_game_join(
    handles:*const u64,count:usize,server:u32,out:*mut u64,
)->i32{
    if handles.is_null()||out.is_null()||!matches!(count,2|4)||server>1{
        return INVALID
    }
    let raw=unsafe{std::slice::from_raw_parts(handles,count)};
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    match join(&mut r,raw,server==1){
        Ok(group)=>{unsafe{out.write(group)};OK},
        Err(e)=>e,
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v4_game_stage(
    group:u64,ipv4:*const u8,len:usize,
    out:*mut WbdWindowsGameRecordV4,capacity:u32,count:*mut u32,
)->i32{
    if ipv4.is_null()||out.is_null()||count.is_null()||
        len<20||len>1200||capacity<2||capacity>4{return INVALID}
    let data=unsafe{std::slice::from_raw_parts(ipv4,len)};
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    match offer_records(&mut r,group,data,capacity as usize){
        Ok(records)=>{
            for (i,rec) in records.iter().enumerate(){
                unsafe{out.add(i).write(*rec)}
            }
            unsafe{count.write(records.len() as u32)}
            OK
        },
        Err(e)=>e,
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v4_game_receive(
    group:u64,lane:u32,wire:*const u8,len:usize,
    out:*mut u8,capacity:usize,used:*mut usize,
)->i32{
    if wire.is_null()||out.is_null()||used.is_null()||
        len<32||len>1536||capacity<1200||capacity>65535{return INVALID}
    let bytes=unsafe{std::slice::from_raw_parts(wire,len)};
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    match receive_record(&mut r,group,lane,bytes){
        Ok(Some(plain)) if plain.len()<=capacity=>{
            unsafe{
                std::ptr::copy_nonoverlapping(plain.as_ptr(),out,plain.len());
                used.write(plain.len())
            }
            OK
        },
        Ok(None)=>{unsafe{used.write(0)};OK},
        _=>INVALID,
    }
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_owner_v4_game_stop(group:u64)->i32{
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    stopped_group(&mut r,group)
}
