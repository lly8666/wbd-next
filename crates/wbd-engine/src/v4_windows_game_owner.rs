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
    lanes:Vec<Arc<Mutex<Entry>>>,
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
        let lane=r.entries.get(h).ok_or(UNKNOWN)?;
        let e=lane.lock().map_err(|_|BAD_STAGE)?;
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
        r.entries.get(h).ok_or(BAD_STAGE).and_then(|lane|lane.lock().map_err(|_|BAD_STAGE).and_then(|mut e|e.game_cold.take().ok_or(BAD_STAGE)))
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
        r.entries.get(h).ok_or(UNKNOWN)?.lock().map_err(|_|BAD_STAGE)?.game_group=Some(group);
    }
    let lanes=ids.iter().map(|h|r.entries.get(h).cloned().ok_or(UNKNOWN))
        .collect::<Result<Vec<_>,_>>()?;
    r.game_groups.insert(group,Arc::new(Mutex::new(WinGameGroup{
        adapter,handles:ids,lanes,generation,
        epoch:scope.ok_or(INVALID)?,tick:0,
    })));
    Ok(group)
}
fn stopped_group(r:&mut Registry,h:u64)->i32{
    let Some(group)=r.game_groups.get(&h)else{return UNKNOWN};
    let Ok(mut game)=group.lock()else{return BAD_STAGE};
    if game.lanes.iter().any(|lane|lane.lock().ok().is_none_or(|e|
        e.game_group!=Some(h)||e.phase!=PH_ACTIVE||
        !e.device.is_some_and(|d|d.quiesced))){return STOP_INCOMPLETE}
    game.adapter.stop();
    for lane in &game.lanes{
        let Ok(mut e)=lane.lock()else{return STOP_INCOMPLETE};
        e.game_group=None;
    }
    drop(game);
    r.game_groups.remove(&h);
    OK
}
pub(super) fn offer_records(
    r:&Registry,h:u64,payload:&[u8],max:usize,
)->Result<Vec<WbdWindowsGameRecordV4>,i32>{
    let group=r.game_groups.get(&h).ok_or(UNKNOWN)?;
    let mut game=group.lock().map_err(|_|BAD_STAGE)?;
    offer_group(&mut game,h,payload,max)
}
fn offer_group(
    game:&mut WinGameGroup,h:u64,payload:&[u8],max:usize,
)->Result<Vec<WbdWindowsGameRecordV4>,i32>{
    if payload.len()<20||payload.len()>1200||payload[0]>>4!=4||
        payload[0]&15<5||max<2||max>4||max<game.handles.len(){
        return Err(INVALID)
    }
    if game.lanes.iter().any(|lane|lane.lock().ok().is_none_or(|e|
        e.game_group!=Some(h)||e.phase!=PH_ACTIVE||
        !e.device.is_some_and(|d|!d.quiesced))){return Err(BAD_STAGE)}
    game.tick=game.tick.checked_add(2).ok_or(FULL)?;
    let now=MonoNs(game.tick);
    game.adapter.offer(payload,now).map_err(|_|INVALID)?;
    let mut staged=Vec::with_capacity(game.handles.len());
    let copied=game.adapter.drain(MonoNs(game.tick+1),|lane,id,pn,wire|{
        if wire.len()>1536{return false}
        let mut record=WbdWindowsGameRecordV4{
            lane:lane.slot,length:wire.len() as u32,pn,
            logical_id:id.0,wire:[0;1536]
        };
        record.wire[..wire.len()].copy_from_slice(wire);
        staged.push(record);
        true // bounded staging copy, NOT a kernel copy or Applied grant
    });
    if copied!=game.handles.len()||staged.len()!=copied{
        return Err(BAD_STAGE)
    }
    Ok(staged)
}
pub(super) fn receive_record(
    r:&Registry,h:u64,lane:u32,wire:&[u8],
)->Result<Option<Vec<u8>>,i32>{
    let group=r.game_groups.get(&h).ok_or(UNKNOWN)?;
    let mut game=group.lock().map_err(|_|BAD_STAGE)?;
    receive_group(&mut game,h,lane,wire)
}
fn receive_group(
    game:&mut WinGameGroup,h:u64,lane:u32,wire:&[u8],
)->Result<Option<Vec<u8>>,i32>{
    if wire.len()<32||wire.len()>1536||
       lane==0||usize::try_from(lane).ok().is_none_or(|v|v>game.handles.len()){
       return Err(INVALID)
    }
    if game.lanes.iter().any(|member|member.lock().ok().is_none_or(|e|
        e.game_group!=Some(h)||e.phase!=PH_ACTIVE||
        !e.device.is_some_and(|d|!d.quiesced))){return Err(BAD_STAGE)}
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
    let owned={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(owned)=r.game_groups.get(&group)else{return UNKNOWN};
        Arc::clone(owned)
    };
    let Ok(mut game)=owned.lock()else{return BAD_STAGE};
    match offer_group(&mut game,group,data,capacity as usize){
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
    let owned={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(owned)=r.game_groups.get(&group)else{return UNKNOWN};
        Arc::clone(owned)
    };
    let Ok(mut game)=owned.lock()else{return BAD_STAGE};
    match receive_group(&mut game,group,lane,bytes){
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

#[cfg(all(test,feature="fec2_product_record"))]
mod tests{
    use super::*;
    fn cold(server:bool,lane:u8)->[u8;COLD_V4_LEN]{
        let mut a=[0;COLD_V4_LEN];
        a[..4].copy_from_slice(b"WBCO");
        a[4..6].copy_from_slice(&1u16.to_be_bytes());
        a[6..8].copy_from_slice(&(COLD_V4_LEN as u16).to_be_bytes());
        a[8]=u8::from(server);a[9]=lane;a[10]=1;
        a[12..28].fill(1);a[28..44].fill(2);
        a[44..60].fill(lane+3);
        a[60..62].copy_from_slice(&1400u16.to_be_bytes());
        a[62..64].copy_from_slice(&1400u16.to_be_bytes());
        a[64..96].fill(4);
        a[96..172].fill(lane+5);
        a[172..].fill(lane+20);
        a
    }
    fn cmd()->[u8;HANDOFF_V1_LEN]{
        let mut a=[0;HANDOFF_V1_LEN];
        a[..4].copy_from_slice(b"WBGH");
        a[4..6].copy_from_slice(&2u16.to_be_bytes());
        a[6..8].copy_from_slice(&(HANDOFF_V1_LEN as u16).to_be_bytes());
        a[8..12].copy_from_slice(&[10,25,0,2]);
        a[12..16].copy_from_slice(&[10,25,0,1]);
        a[16..18].copy_from_slice(&41001u16.to_be_bytes());
        a[18..20].copy_from_slice(&443u16.to_be_bytes());
        a[20..24].copy_from_slice(&500u32.to_be_bytes());
        a[24..26].copy_from_slice(&1360u16.to_be_bytes());
        a[26]=1;
        a[27..29].copy_from_slice(&7u16.to_be_bytes());
        a
    }
    fn setup(r:&mut Registry,n:usize,server:bool)->Vec<u64>{
        let mut hs=Vec::new();
        for lane in 1..=n{
            let h=allocate(r,&cold(server,lane as u8),&cmd(),server)
                .expect("feature7 original TLS owner candidate");
            assert_eq!(commit(r,h,0,0,600),OK);
            assert_eq!(bind_wintun(r,h,[2;16],101+lane as u64,11+lane as u32),OK);
            hs.push(h);
        }
        hs
    }
    #[test]
    fn m0_windows_native_game_two_four_original_owner_aead_no_hol_and_stop(){
        for n in [2,4]{
            let mut r=Registry{
                generation:1,entries:BTreeMap::new(),
                game_groups:BTreeMap::new(),
            };
            let client=setup(&mut r,n,false);
            let server=setup(&mut r,n,true);
            assert_eq!(join(&mut r,&client[..1],false),Err(INVALID));
            assert_eq!(join(&mut r,&[client[0],client[0]],false),Err(INVALID));
            let c=join(&mut r,&client,false).expect("client native M4 group");
            let s=join(&mut r,&server,true).expect("server native M4 group");
            assert_ne!(c,s);
            assert_eq!(join(&mut r,&client,false),Err(BAD_STAGE));
            assert_eq!(stop(&mut r,client[0]),STOP_INCOMPLETE);
            let mut ipv4=[0u8;40];ipv4[0]=0x45;
            ipv4[2..4].copy_from_slice(&40u16.to_be_bytes());
            ipv4[8]=64;ipv4[9]=17;ipv4[20..].fill(0x6a);
            let records=offer_records(&mut r,c,&ipv4,n).unwrap();
            assert_eq!(records.len(),n);
            assert!(records.iter().all(|a|a.length>31));
            assert!(records.windows(2).all(|pair|pair[0].wire!=pair[1].wire));
            // A stalled first lane cannot block an independently
            // authenticated later-lane first delivery.
            let lane2=&records[1];
            assert_eq!(receive_record(&mut r,s,lane2.lane,
                &lane2.wire[..lane2.length as usize]).unwrap(),
                Some(ipv4.to_vec()));
            // Replayed authenticated PN may not deliver a second packet.
            assert!(receive_record(&mut r,s,lane2.lane,
                &lane2.wire[..lane2.length as usize]).is_err());
            let records=offer_records(&mut r,c,&ipv4,n).unwrap();
            let lane_last=records.last().unwrap();
            let mut corrupt=lane_last.wire[..lane_last.length as usize].to_vec();
            *corrupt.last_mut().unwrap()^=1;
            assert_eq!(receive_record(&mut r,s,lane_last.lane,&corrupt),Err(INVALID));
            assert_eq!(receive_record(&mut r,s,lane_last.lane,
                &lane_last.wire[..lane_last.length as usize]).unwrap(),
                Some(ipv4.to_vec()));
            assert_eq!(stopped_group(&mut r,c),STOP_INCOMPLETE);
            for h in client.iter().chain(server.iter()){
                let dev=r.entries[h].lock().unwrap().device.unwrap();
                assert_eq!(quiesce_wintun(&mut r,*h,[2;16],dev.luid,dev.ifindex),OK);
            }
            assert_eq!(stopped_group(&mut r,c),OK);
            assert_eq!(stopped_group(&mut r,s),OK);
            assert_eq!(stopped_group(&mut r,c),UNKNOWN);
            for h in client.iter().chain(server.iter()){
                assert_eq!(stop(&mut r,*h),OK);
                assert_eq!(release(&mut r,*h),OK);
            }
            assert!(r.game_groups.is_empty());
            assert_eq!(PRODUCT_APPLIED,0);
        }
    }
}
