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
    // Coherently advance the shared M1 owner clock used by DATA, parity
    // and original Rust M2 control; never offer source at synthetic t=0.
    let now=m2_clock();
    let (pn,seq,used)=e.owner.seal_fec2_product_one(
        slab,frame.len(),kind,budget,0,epoch,now
    ).map_err(|_|BAD_STAGE)?;
    let scratch=std::mem::take(&mut e.tx_scratch);
    let batch=match e.owner.drain_tx(now,scratch){
        Ok(batch)=>batch,
        Err((_,scratch))=>{e.tx_scratch=scratch;return Err(BAD_STAGE)}
    };
    let accepted=(||{
        let ready=e.owner.checked_tx_ready(&batch).map_err(|_|BAD_STAGE)?;
        if ready.len()!=1||ready[0].record.bytes().len()!=used ||
           used>out.len(){return Err(BAD_STAGE)}
        if kind==2{
            if let Some(m)=e.m2.as_mut(){
                let record=&ready[0].record;
                if record.metadata().pn!=RecordPn(pn) ||
                    record.metadata().seq.0 as u32!=seq ||
                    m.pending.insert(RecordPn(pn),record.clone()).is_some(){
                    return Err(BAD_STAGE)
                }
            }
        }
        out[..used].copy_from_slice(ready[0].record.bytes());
        Ok((used,seq,pn))
    })();
    e.tx_scratch=batch.recycle();
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
pub(super) fn open_symbol_entry(e:&mut Entry,epoch:[u8;16],luid:u64,ifindex:u32,
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
    // Linux M1 uses a single monotonic timestamp for offer and drain.
    // The Windows FEC2 path formerly offered at zero, then drained at a
    // clock advanced during TLS/NPF setup, expiring genuine new frames.
    let now=m2_clock();
    e.owner.offer_after_active(slab,0..wire.len(),unfolded,now)
        .map_err(|_|INVALID)?;
    let mut result=Vec::new();
    let mut failed=false;
    let mut unique_data_pn=None;
    let mut unique_receipt=None;
    // Split the actual Entry fields, not the MutexGuard deref, so Rust
    // guarantees one unique RX owner and distinct bounded RS16 decoder.
    let entry:&mut Entry=e;
    let decoder=entry.fec2_rx.as_mut().ok_or(BAD_STAGE)?;
    let rx_storage=std::mem::take(&mut entry.rx_scratch);
    let draining=entry.owner.drain_windows_authenticated_fec2(
        now,rx_storage,|pn,kind,plain|{
            unique_data_pn=Some(pn);
            match decoder.accept_authenticated(scope,kind,plain,now){
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
        },|pn,receipt|{unique_receipt=Some((pn,receipt))}
    );
    let (storage,report)=match draining{
        Ok(v)=>v,
        Err((_,scratch))=>{entry.rx_scratch=scratch;return Err(BAD_STAGE)}
    };
    entry.rx_scratch=storage;
    if failed||report.rejected!=0||
        report.link_ready.saturating_add(report.control_ready)!=1 {
        return Err(INVALID)
    }
    if let Some((pn,receipt))=unique_receipt{
        if e.m2.is_some(){m2_authenticated_kind1_entry(e,pn,&receipt)?;}
        else{return Err(BAD_STAGE)}
    }
    if let Some(pn)=unique_data_pn{
        if let Some(m)=e.m2.as_mut(){
            m.feedback.on_authenticated_data(RecordPn(pn),m2_clock());
        }
    }
    e.rx_unwrapped_high=e.rx_unwrapped_high.max(unfolded+wire.len() as u64);
    Ok(result)
}
// The exact shared RS16 encoder is used for Windows parity; NO parallel
// Go/C-ABI Reed-Solomon implementation or fake M2 policy ACK. Caller must
// hold the original authenticated current Rust feature7 owner and real
// process-created Wintun interface. This returns only an UNSEALED repair
// symbol. Production caller must M3-seal it as kind3 with a fresh PN.
fn encode_repair_entry(
    e:&Entry,epoch:[u8;16],luid:u64,ifindex:u32,
    block_id:u64,profile:u32,row:u32,frames:&[&[u8]],out:&mut [u8],
)->Result<usize,i32>{
    use wbd_codec::fec_v2::{Rs16,Profile,BackendChoice};
    if !v3_ready(e,epoch,luid,ifindex)||!e.feature7||
        e.game_group.is_some()||block_id==0||
        !(1..=16).contains(&frames.len())||profile>6||row>=16 {
        return Err(INVALID)
    }
    let budget=normal_off_windows_budget(e)?.record_payload_mtu;
    let policy=Profile::ALL[profile as usize];
    let original_max=wbd_codec::fec_v2::max_original_for_record_budget(budget)
        .map_err(|_|INVALID)?;
    if frames.iter().any(|frame|frame.len()<20||
        frame.len()>original_max||frame[0]>>4!=4||frame[0]&15<5){
        return Err(INVALID)
    }
    let required=12usize+2usize+frames.iter().map(|f|f.len()).max().ok_or(INVALID)?;
    if required>budget||out.len()<required{return Err(INVALID)}
    let mut writable=[&mut out[..required]];
    Rs16::new().encode_into(block_id,frames,policy,row as usize,
        &mut writable,budget,BackendChoice::Scalar).map_err(|_|INVALID)?;
    Ok(required)
}

// Packed separate frame vector: 16 fixed 2048B slots and a separate
// 16-entry length array, no caller-controlled stride/pointer arithmetic.
// 32KiB is bounded and never held beyond this call. The C ABI does not
// accept any key/epoch except the one already stored in Rust by original Go.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v4_fec2_encode_repair(
    h:u64,ep:*const u8,ep_len:usize,luid:u64,ifindex:u32,
    block_id:u64,profile:u32,row:u32,
    slots:*const u8,lengths:*const u32,k:u32,
    dst:*mut u8,cap:usize,used:*mut usize,
)->i32{
    if slots.is_null()||lengths.is_null()||dst.is_null()||
        used.is_null()||k==0||k>16||cap<34||cap>2048 {
        return INVALID
    }
    let Some(epoch)=v3_epoch(ep,ep_len)else{return INVALID};
    let bytes=unsafe{std::slice::from_raw_parts(slots,k as usize*2048)};
    let sizes=unsafe{std::slice::from_raw_parts(lengths,k as usize)};
    if sizes.iter().any(|&v|v<20||v>2048){return INVALID}
    let frames=bytes.chunks_exact(2048).zip(sizes).map(|(slot,&n)|
        &slot[..n as usize]).collect::<Vec<_>>();
    let dst_start=dst as usize;
    let src_start=slots as usize;
    let sizes_start=lengths as usize;
    if src_start.checked_add(k as usize*2048).is_none_or(|end|
           dst_start<end&&src_start<dst_start.saturating_add(cap))||
       sizes_start.checked_add(k as usize*4).is_none_or(|end|
           dst_start<end&&sizes_start<dst_start.saturating_add(cap)){
       return INVALID
    }
    let lane={
        let Ok(reg)=registry().lock()else{return BAD_STAGE};
        let Some(e)=reg.entries.get(&h)else{return UNKNOWN};
        Arc::clone(e)
    };
    let Ok(e)=lane.lock()else{return BAD_STAGE};
    let output=unsafe{std::slice::from_raw_parts_mut(dst,cap)};
    match encode_repair_entry(&e,epoch,luid,ifindex,block_id,
        profile,row,&frames,output){
        Ok(n)=>{unsafe{used.write(n)};OK},
        Err(err)=>err,
    }
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
        Ok(_)=>INVALID,
        Err(status)=>status,
    }
}


#[repr(C)]
#[derive(Clone,Copy)]
pub struct WindowsFixedParityRow {
    pub used:u32,pub seq:u32,pub pn:u64,pub wire:[u8;2048],
}
#[repr(C)]
#[derive(Clone,Copy)]
pub struct WindowsFixedParityBatch {
    pub count:u32,pub reserved:u32,pub rows:[WindowsFixedParityRow;4],
}
fn empty_parity_row()->WindowsFixedParityRow{
    WindowsFixedParityRow{used:0,seq:0,pn:0,wire:[0;2048]}
}
pub(super) fn stage_fixed_source_entry(e:&mut Entry,epoch:[u8;16],luid:u64,
    ifindex:u32,frame:&[u8],out:&mut [u8]
)->Result<(usize,u32,u64),i32>{
    if !v3_ready(e,epoch,luid,ifindex)||!e.feature7||e.m2.is_none()||
        frame.len()<20||frame[0]>>4!=4||frame[0]&15<5{
        return Err(BAD_STAGE)
    }
    let budget=normal_off_windows_budget(e)?;
    if frame.len()>budget.record_payload_mtu.saturating_sub(14)||
        out.len()<frame.len()+41{return Err(INVALID)}
    // Fallible Arena allocation MUST precede taking the only FEC stream:
    // capacity errors cannot discard profile/revision for this generation.
    let mut input=e.arena.allocate().map_err(|_|FULL)?;
    input.writable()[14..14+frame.len()].copy_from_slice(frame);
    let mut stream=e.fec2_tx.take().ok_or(BAD_STAGE)?;
    // Linux FixedStream is the sole revision source of truth. The old
    // Windows ==1 placeholder silently rejected every Auto/FEC policy
    // transition despite carrying a correctly authenticated ticket.
    let active_revision=stream.revision();
    let mut result=None;
    let mut error=None;
    let offered=stream.offer_source(
        input,14..14+frame.len(),m2_clock(),|ticket,plain|{
            let attempt=(||->Result<(usize,u32,u64),i32>{
                if ticket.revision!=active_revision{return Err(BAD_STAGE)}
                let mut source=[0u8;2048];
                let used=fec_v2::source_into(
                    ticket.block_id,ticket.index,plain,budget.record_payload_mtu,&mut source
                ).map_err(|_|INVALID)?;
                seal_symbol_entry(e,epoch,luid,ifindex,2,&source[..used],out)
            })();
            match attempt{
                Ok(v)=>{result=Some(v);true},
                Err(err)=>{error=Some(err);false},
            }
        }
    );
    e.fec2_tx=Some(stream);
    if let Some(err)=error{return Err(err)}
    let accepted=offered.map_err(|_|BAD_STAGE)?;
    if !accepted.source_enqueued{return Err(BAD_STAGE)}
    result.ok_or(BAD_STAGE)
}
pub(super) fn stage_fixed_parity_entry(e:&mut Entry,epoch:[u8;16],luid:u64,
    ifindex:u32
)->Result<WindowsFixedParityBatch,i32>{
    use crate::v4_fixed_stream::DriverProof;
    if !v3_ready(e,epoch,luid,ifindex)||!e.feature7||e.m2.is_none(){
        return Err(BAD_STAGE)
    }
    let mut stream=e.fec2_tx.take().ok_or(BAD_STAGE)?;
    let active_revision=stream.revision();
    let previous_revision=stream.prior_parity_revision();
    let mut out=WindowsFixedParityBatch{
        count:0,reserved:0,rows:[empty_parity_row();4],
    };
    let mut err=None;
    let result=stream.poll_parity(m2_clock(),|parity,_block,_row,revision|{
        if (revision!=active_revision&&Some(revision)!=previous_revision)
            || out.count>=4{
            err=Some(BAD_STAGE);return DriverProof::NotSent
        }
        let item=&mut out.rows[out.count as usize];
        match seal_symbol_entry(e,epoch,luid,ifindex,3,parity,&mut item.wire){
            Ok((used,seq,pn))=>{
                item.used=used as u32;item.seq=seq;item.pn=pn;
                out.count+=1;DriverProof::Staged
            }
            Err(code)=>{err=Some(code);DriverProof::NotSent}
        }
    });
    e.fec2_tx=Some(stream);
    if let Some(code)=err{return Err(code)}
    result.map_err(|_|BAD_STAGE)?;
    Ok(out)
}
// Original-Go TLS-bound initial Fixed/Auto profile. Linux's exact
// FixedStream starts at revision1 with an explicitly selected profile.
// No source, staged ciphertext, M2 feedback, or parity may exist yet.
fn fixed_initial_profile_entry(e:&mut Entry,epoch:[u8;16],luid:u64,
    ifindex:u32,profile:u8)->Result<(),i32>{
    if profile>6{return Err(INVALID)}
    if !v3_ready(e,epoch,luid,ifindex)||!e.feature7||
        e.game_group.is_some(){return Err(BAD_STAGE)}
    let m=e.m2.as_ref().ok_or(BAD_STAGE)?;
    if !m.pending.is_empty()||m.shadow.outstanding()!=0||
        m.feedback_pending.is_some()||m.fec_copied_source!=0||
        m.fec_copied_parity!=0||m.fec_reverse_reports!=0{
        return Err(BAD_STAGE)
    }
    let tx=e.fec2_tx.as_ref().ok_or(BAD_STAGE)?;
    if tx.revision().0!=1||tx.next_deadline().is_some()||
       tx.report().outstanding_jobs!=0{return Err(BAD_STAGE)}
    let budget=normal_off_windows_budget(e)?;
    let new=crate::v4_fixed_stream::FixedStream::new(
        profile,1,budget.record_payload_mtu
    ).ok_or(BAD_STAGE)?;
    if let Some(mut old)=e.fec2_tx.replace(new){old.stop()}
    Ok(())
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v8_fixed_select_initial(
    h:u64,ep:*const u8,ep_len:usize,luid:u64,ifindex:u32,
    profile:u32,
)->i32{
    if profile>6{return INVALID}
    let Some(epoch)=v3_epoch(ep,ep_len)else{return INVALID};
    let entry={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(entry)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(entry)
    };
    let Ok(mut e)=entry.lock()else{return BAD_STAGE};
    match fixed_initial_profile_entry(&mut e,epoch,luid,ifindex,profile as u8){
        Ok(())=>OK,Err(code)=>code,
    }
}
// Same Linux FixedStream quiescent profile/revision transition, scoped to
// the original Go-credential-TLS Rust generation and the original M4
// Wintun hold. Does NOT grant Windows product mode/GUI Applied. A new
// revision must produce fresh kernel-copy source/parity and mature M2
// evidence; old revision counters cannot qualify the new one.
fn fixed_change_revision_entry(e:&mut Entry,epoch:[u8;16],luid:u64,
    ifindex:u32,profile:u8,revision:u64)->Result<(),i32>{
    if profile>6||revision==0{return Err(INVALID)}
    if !v3_ready(e,epoch,luid,ifindex)||!e.feature7||
        e.game_group.is_some()||e.m2.is_none(){return Err(BAD_STAGE)}
    let now=m2_clock();
    let route=e.m2.as_ref().ok_or(BAD_STAGE)?.route;
    let fresh=wbd_recovery::MatureFirstSend::new(
        route,wbd_recovery::MaturityConfig{max_live_data:524_288},now
    ).map_err(|_|BAD_STAGE)?;
    e.fec2_tx.as_mut().ok_or(BAD_STAGE)?
        .quiescent_change(profile,revision,now)
        .map_err(|err|match err{
            crate::v4_fixed_stream::StreamError::StaleRevision |
            crate::v4_fixed_stream::StreamError::Invalid=>INVALID,
            _=>BAD_STAGE,
        })?;
    let m=e.m2.as_mut().ok_or(BAD_STAGE)?;
    m.mature=Some(fresh);
    m.fec_copied_source=0;
    m.fec_copied_parity=0;
    m.auto_reverse_base=m.auto_reverse_base
        .saturating_add(m.fec_reverse_reports);
    m.fec_reverse_reports=0;
    m.fec_positive_2s=0;
    m.fec_covered_2s=0;
    m.fec_censored=false;
    m.fec_last_capacity_at=None;
    Ok(())
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v8_fixed_change_revision(
    h:u64,ep:*const u8,ep_len:usize,luid:u64,ifindex:u32,
    profile:u32,revision:u64,
)->i32{
    if profile>6||revision==0{return INVALID}
    let Some(epoch)=v3_epoch(ep,ep_len)else{return INVALID};
    let entry={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(entry)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(entry)
    };
    let Ok(mut e)=entry.lock()else{return BAD_STAGE};
    match fixed_change_revision_entry(&mut e,epoch,luid,ifindex,
        profile as u8,revision){
        Ok(())=>OK,Err(code)=>code,
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v8_fixed_stage_source(
    h:u64,ep:*const u8,ep_len:usize,luid:u64,ifindex:u32,
    plain:*const u8,n:usize,out:*mut u8,cap:usize,
    used:*mut usize,seq:*mut u32,pn:*mut u64
)->i32{
    if plain.is_null()||out.is_null()||used.is_null()||seq.is_null()||
        pn.is_null()||n<20||n>2048||cap<n+41||cap>2048{return INVALID}
    let Some(epoch)=v3_epoch(ep,ep_len)else{return INVALID};
    if (plain as usize).checked_add(n).is_none_or(|end|
        (out as usize)<end&&(plain as usize)<(out as usize).saturating_add(cap)){
        return INVALID
    }
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(entry)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(entry)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    let src=unsafe{std::slice::from_raw_parts(plain,n)};
    let output=unsafe{std::slice::from_raw_parts_mut(out,cap)};
    match stage_fixed_source_entry(&mut e,epoch,luid,ifindex,src,output){
        Ok((length,s,p))=>{unsafe{used.write(length);seq.write(s);pn.write(p)};OK},
        Err(code)=>code,
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v8_fixed_parity_due(
    h:u64,ep:*const u8,ep_len:usize,luid:u64,ifindex:u32,
    out:*mut WindowsFixedParityBatch,size:u32
)->i32{
    if out.is_null()||size!=std::mem::size_of::<WindowsFixedParityBatch>() as u32{
        return INVALID
    }
    let Some(epoch)=v3_epoch(ep,ep_len)else{return INVALID};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(entry)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(entry)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    match stage_fixed_parity_entry(&mut e,epoch,luid,ifindex){
        Ok(value)=>{unsafe{out.write(value)};OK},Err(code)=>code
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v8_fixed_parity_result(
    h:u64,ep:*const u8,ep_len:usize,luid:u64,ifindex:u32,
    copied:u32,not_sent:u32,uncertain:u32
)->i32{
    if copied+not_sent+uncertain==0||copied+not_sent+uncertain>4{
        return INVALID
    }
    let Some(epoch)=v3_epoch(ep,ep_len)else{return INVALID};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(entry)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(entry)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    if !v3_ready(&e,epoch,luid,ifindex)||!e.feature7{return BAD_STAGE}
    let Some(ref mut tx)=e.fec2_tx else{return BAD_STAGE};
    if tx.settle_staged(copied as u8,not_sent as u8,uncertain as u8).is_err(){
        return BAD_STAGE
    }
    if copied>0{
        let Some(ref mut m)=e.m2 else{return BAD_STAGE};
        m.fec_copied_parity=m.fec_copied_parity.saturating_add(copied as u64);
    }
    OK
}
// Exact Linux Auto 30-field native M2 quality layout, not a second
// Windows loss estimator. Only mature original first-send M2 observations
// and actual-k completed FEC2 groups enter these cumulative counters.
fn accumulate_original_auto_quality(
    m:&mut WindowsOriginalM2,poll:wbd_recovery::MaturityPoll,
    capacity_censored:u64,
){
    for (part,window) in [poll.window_2s,poll.window_8s].iter().enumerate(){
        let offset=part*5;
        for (i,value) in [
            window.first_sent,window.unambiguous_positive,
            window.covered_missing,window.repaired_or_ambiguous,
            window.uncovered,
        ].iter().enumerate(){
            m.auto_quality[offset+i]=m.auto_quality[offset+i].saturating_add(*value);
        }
    }
    m.auto_quality[10]=m.auto_reverse_base
        .saturating_add(m.fec_reverse_reports);
    m.auto_quality[11]=m.auto_quality[11].max(capacity_censored);
    m.auto_quality[12]=m.auto_quality[12].saturating_add(
        poll.window_8s.positive_confirmation_lag_ns);
    m.auto_quality[13]=m.auto_quality[13].saturating_add(
        poll.window_8s.positive_confirmation_samples);
}

fn original_m2_recent_capacity(at:Option<MonoNs>,now:MonoNs)->bool{
    // Affected 8-second quality cohorts remain UNKNOWN. Once they mature,
    // a later clean window can qualify without erasing cumulative censorship.
    at.is_some_and(|at|now.0.saturating_sub(at.0)<8_000_000_000)
}

// One Linux MatureFirstSend expiry batch is 64 independent deadlines, but
// each real M4 DATA needs TWO: 2s and 8s. Windows' 100ms readback previously
// consumed only 64 per tick (<=320 DATA/s); real Npcap had >660 DATA/s.
// Reuse the SAME mature owner and its 64-entry bounded batch until the
// already-due records are exhausted. No Go timer/FEC estimator, shadow
// resampling, 512-source threshold or native kernel result is changed.
fn drain_original_auto_mature_due(
    m:&mut WindowsOriginalM2,now:MonoNs,
)->Result<(),i32>{
    // Every call is one time/budget-limited owner turn. No long historical
    // drain can hold the Entry mutex while incoming DATA waits.
    let started=Instant::now();
    let mut handled=0usize;
    loop {
        if handled>=256 || started.elapsed()>=std::time::Duration::from_micros(200) {
            return Ok(());
        }
        let (poll,capacity_censored)={
            let mature=m.mature.as_mut().ok_or(BAD_STAGE)?;
            let poll=mature.on_due(now).map_err(|_|BAD_STAGE)?;
            let capacity_censored=mature.counters().capacity_censored;
            (poll,capacity_censored)
        };
        m.fec_positive_2s=m.fec_positive_2s.saturating_add(
            poll.window_2s.unambiguous_positive);
        m.fec_covered_2s=m.fec_covered_2s.saturating_add(
            poll.window_2s.covered());
        // MatureFirstSend reports cumulative capacity forever. Keep the
        // count cumulative for source-backed Auto history, but gate current
        // Fixed quality only during its actual 8s uncertain cohort.
        if capacity_censored>m.auto_quality[11]{
            m.fec_last_capacity_at=Some(now);
        }
        let has_due=poll.next_deadline.is_some_and(|deadline|deadline.0<=now.0);
        let progressed=poll.processed>0;
        handled=handled.saturating_add(poll.processed);
        accumulate_original_auto_quality(m,poll,capacity_censored);
        if !has_due{return Ok(())}
        if !progressed{return Err(BAD_STAGE)}
    }
}
#[repr(C)]
pub struct WindowsFEC2AutoQuality {
    pub version:u32,pub size:u32,pub revision:u64,
    pub counters:[u64;30],
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v8_fec2_auto_quality(
    h:u64,ep:*const u8,ep_len:usize,luid:u64,ifindex:u32,
    out:*mut WindowsFEC2AutoQuality,size:u32,
)->i32{
    if out.is_null()||size!=std::mem::size_of::<WindowsFEC2AutoQuality>() as u32{
        return INVALID
    }
    let Some(epoch)=v3_epoch(ep,ep_len)else{return INVALID};
    let entry={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(entry)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(entry)
    };
    let Ok(mut e)=entry.lock()else{return BAD_STAGE};
    if !v3_ready(&e,epoch,luid,ifindex)||!e.feature7||e.game_group.is_some(){
        return BAD_STAGE
    }
    let (revision,histogram)={
        let Some(tx)=e.fec2_tx.as_ref()else{return BAD_STAGE};
        let report=tx.report();
        let mut h=[0u64;16];
        for (i,slot) in h.iter_mut().enumerate(){
            for class in report.classes {
                *slot=slot.saturating_add(class.k_hist[i+1]);
            }
        }
        (tx.revision().0,h)
    };
    let Some(m)=e.m2.as_mut()else{return BAD_STAGE};
    if drain_original_auto_mature_due(m,m2_clock()).is_err(){return BAD_STAGE}
    for (i,k) in histogram.into_iter().enumerate(){
        m.auto_quality[14+i]=k;
    }
    unsafe{out.write(WindowsFEC2AutoQuality{
        version:1,size,revision,counters:m.auto_quality,
    })};OK
}
#[repr(C)]
pub struct WindowsFixedMatureReadback {
    pub version:u32,pub size:u32,pub applied:u32,pub censored:u32,
    pub copied_source:u64,pub copied_parity:u64,
    pub reverse_reports:u64,pub positive_2s:u64,pub covered_2s:u64,
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v8_fixed_mature_readback(
    h:u64,ep:*const u8,ep_len:usize,luid:u64,ifindex:u32,
    out:*mut WindowsFixedMatureReadback,size:u32
)->i32{
    if out.is_null()||size!=std::mem::size_of::<WindowsFixedMatureReadback>() as u32{
        return INVALID
    }
    let Some(epoch)=v3_epoch(ep,ep_len)else{return INVALID};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(entry)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(entry)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    if !v3_ready(&e,epoch,luid,ifindex)||!e.feature7{return BAD_STAGE}
    let Some(m)=e.m2.as_mut()else{return BAD_STAGE};
    if drain_original_auto_mature_due(m,m2_clock()).is_err(){return BAD_STAGE}
    let recently_censored=original_m2_recent_capacity(
        m.fec_last_capacity_at,m2_clock());
    let censored=m.fec_censored||recently_censored;
    let applied=!censored && m.fec_copied_source>0&&
        m.fec_copied_parity>0&&m.fec_positive_2s>0&&
        m.fec_covered_2s>0&&m.fec_reverse_reports>0;
    unsafe{out.write(WindowsFixedMatureReadback{
        version:1,size,applied:u32::from(applied),
        censored:u32::from(censored),
        copied_source:m.fec_copied_source,copied_parity:m.fec_copied_parity,
        reverse_reports:m.fec_reverse_reports,positive_2s:m.fec_positive_2s,
        covered_2s:m.fec_covered_2s,
    })};OK
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
    fn m0_windows_auto_capacity_unknown_is_recent_only_without_lying_about_history(){
        let before=Some(MonoNs(2_000_000_000));
        assert!(!original_m2_recent_capacity(None,MonoNs(3_000_000_000)));
        assert!(original_m2_recent_capacity(before,MonoNs(9_999_999_999)));
        assert!(!original_m2_recent_capacity(before,MonoNs(10_000_000_000)));
        // A future timestamp is never proof that capacity censorship expired.
        assert!(original_m2_recent_capacity(before,MonoNs(1_000_000_000)));
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
        // The public Windows runner spends real seconds on WSL2, original
        // credential TLS, Npcap and Wintun before the first reverse DATA.
        // A fresh authentic M1 RX queue offer must not inherit startup age.
        let _=m2_clock();
        std::thread::sleep(std::time::Duration::from_millis(2200));
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
    #[test]
    fn m0_windows_shared_rs16_original_owner_encode_repair_recovers_missing_source(){
        let mut registry=Registry{
            generation:1,entries:BTreeMap::new(),game_groups:BTreeMap::new(),
        };
        let c=setup(&mut registry,false,401,41);
        let peer=setup(&mut registry,true,402,42);
        let a=data(0x11);
        let mut b=data(0x22);b.extend(vec![0x23;130]);
        let b_len=b.len() as u16;
        b[2..4].copy_from_slice(&b_len.to_be_bytes());
        let budget=normal_off_windows_budget(
            &registry.entries[&c].lock().unwrap()).unwrap();
        let source=fec_v2::source_owned(88,0,&a,budget.record_payload_mtu).unwrap();
        let (record,seq,_)=send(&mut registry,c,401,41,2,&source);
        let first=open_symbol(&mut registry,peer,[2;16],402,42,seq,&record).unwrap();
        assert_eq!(first.len(),1);
        assert_eq!(first[0].recovered,0);
        let frames=[a.as_slice(),b.as_slice()];
        let mut symbol=[0u8;2048];
        let count={
            let entry=registry.entries[&c].lock().unwrap();
            assert_eq!(encode_repair_entry(&entry,[3;16],401,41,
                88,3,0,&frames,&mut symbol),Err(INVALID));
            assert_eq!(encode_repair_entry(&entry,[2;16],99,41,
                88,3,0,&frames,&mut symbol),Err(INVALID));
            encode_repair_entry(&entry,[2;16],401,41,
                88,3,0,&frames,&mut symbol).unwrap()
        };
        assert_eq!(fec_v2::parse_repair(&symbol[..count],budget.record_payload_mtu)
            .unwrap().actual_k,2);
        let (parity,repair_seq,_)=send(&mut registry,c,401,41,3,&symbol[..count]);
        let delivered=open_symbol(&mut registry,peer,[2;16],402,42,
            repair_seq,&parity).unwrap();
        assert_eq!(delivered.len(),1);
        assert_eq!(delivered[0].recovered,1);
        assert_eq!(&delivered[0].frame[..delivered[0].length as usize],b.as_slice());
        assert!(open_symbol(&mut registry,peer,[2;16],402,42,
            repair_seq,&parity).is_err());
        assert_eq!(quiesce_wintun(&mut registry,c,[2;16],401,41),OK);
        assert_eq!(quiesce_wintun(&mut registry,peer,[2;16],402,42),OK);
        assert_eq!(stop(&mut registry,c),OK);
        assert_eq!(stop(&mut registry,peer),OK);
        assert_eq!(release(&mut registry,c),OK);
        assert_eq!(release(&mut registry,peer),OK);
        assert_eq!(PRODUCT_APPLIED,0);
    }

    #[test]
    fn m0_windows_fec2_source_arena_full_keeps_stream_and_recovers_same_epoch(){
        let mut r=Registry{generation:131,entries:BTreeMap::new(),
            game_groups:BTreeMap::new()};
        let h=setup(&mut r,false,911,91);
        let ep=[2;16];
        {
            let mut e=r.entries[&h].lock().unwrap();
            m2_arm_entry(&mut e,ep,911,91).unwrap();
            let revision=e.fec2_tx.as_ref().unwrap().revision();
            let mut held=Vec::new();
            while let Ok(slab)=e.arena.allocate(){held.push(slab);}
            assert!(!held.is_empty());
            assert_eq!(stage_fixed_source_entry(
                &mut e,ep,911,91,&data(7),&mut [0u8;2048]),Err(FULL));
            assert_eq!(e.fec2_tx.as_ref().unwrap().revision(),revision);
            drop(held);
            let (n,seq,pn)=stage_fixed_source_entry(
                &mut e,ep,911,91,&data(8),&mut [0u8;2048])
                .expect("released arena must restore original fixed owner");
            assert!(n>51);
            m2_kernel_firstsend_entry(&mut e,ep,911,91,pn,seq,n,1)
                .expect("actual first-send settlement on recovered owner");
        }
        assert_eq!(quiesce_wintun(&mut r,h,ep,911,91),OK);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(release(&mut r,h),OK);
    }
    #[test]
    fn m0_windows_fresh_firstsend_outlives_optional_m2_shadow_full(){
        let mut r=Registry{generation:200,entries:BTreeMap::new(),
            game_groups:BTreeMap::new()};
        let h=setup(&mut r,false,991,99);
        let ep=[2;16];
        {
            let mut e=r.entries[&h].lock().unwrap();
            m2_arm_entry(&mut e,ep,991,99).unwrap();
            for i in 0..(MAX_M2_FIXED_FROZEN+4) {
                let mut out=[0u8;2048];
                let (n,seq,pn)=v3_seal_entry(
                    &mut e,ep,991,99,&data((i%250) as u8),&mut out)
                    .expect("fresh seal must not depend on optional repair occupancy");
                let cached=m2_kernel_firstsend_entry(
                    &mut e,ep,991,99,pn,seq,n,1)
                    .expect("actual NPF copy must not fail due to repair-cache cap");
                assert!(cached as usize<=MAX_M2_FIXED_FROZEN);
            }
            assert_eq!(e.m2.as_ref().unwrap().shadow.outstanding(),
                MAX_M2_FIXED_FROZEN);
            assert!(e.m2.as_ref().unwrap().pending.is_empty());
        }
    }
    #[test]
    fn m0_windows_fixed_source_then_true_kind1_control_then_parity_seq_is_contiguous(){
        // Reproduces the source/control/parity interleaving of the historic
        // natural Auto 428-byte control mismatch at original Rust M1.
        // This is a deterministic *unit*, not proof of the failing NPF run.
        let mut r=Registry{generation:911,entries:BTreeMap::new(),
            game_groups:BTreeMap::new()};
        let h=setup(&mut r,false,811,81);
        let ep=[2;16];
        let mut last=600u32;
        {
            let mut e=r.entries[&h].lock().unwrap();
            m2_arm_entry(&mut e,ep,811,81).unwrap();
            // Authenticated reverse M2 data can precede this new outbound
            // full FEC block. Make its real 20ms feedback timer mature
            // BEFORE the block is sealed, so parity doesn't expire while
            // the test sleeps (real original worker would poll meanwhile).
            e.m2.as_mut().unwrap().feedback.on_authenticated_data(
                RecordPn(711),m2_clock());
        }
        std::thread::sleep(std::time::Duration::from_millis(21));
        {
            let mut e=r.entries[&h].lock().unwrap();
            for i in 0..16u8 {
                let mut wire=[0u8;2048];
                let (n,seq,pn)=stage_fixed_source_entry(
                    &mut e,ep,811,81,&data(i+1),&mut wire).unwrap();
                assert_eq!(seq,last);
                last=seq.wrapping_add(n as u32);
                m2_kernel_firstsend_entry(&mut e,ep,811,81,pn,seq,n,1)
                    .expect("exact typed copy of freshly sealed M1 DATA");
            }
        }
        let (control_seq,control_len,control_pn)={
            let mut e=r.entries[&h].lock().unwrap();
            let mut wire=[0u8;2048];
            let (n,seq,pn)=m2_next_feedback_entry(
                &mut e,ep,811,81,&mut wire).unwrap().unwrap();
            assert_eq!(seq,last,"M2 kind1 must not skip prior source");
            m2_finish_feedback_entry(&mut e,ep,811,81,pn,1).unwrap();
            (seq,n,pn)
        };
        assert!(control_len>FIXED_WIRE_OVERHEAD && control_pn>=16);
        last=control_seq.wrapping_add(control_len as u32);
        {
            let mut e=r.entries[&h].lock().unwrap();
            let parity=stage_fixed_parity_entry(&mut e,ep,811,81)
                .expect("deferred shared FEC quantum after M2 control");
            assert!(parity.count>0 && parity.count<=4);
            for row in &parity.rows[..parity.count as usize] {
                assert_eq!(row.seq,last,"parity must follow control exactly");
                last=last.wrapping_add(row.used);
            }
            e.fec2_tx.as_mut().unwrap().settle_staged(
                parity.count as u8,0,0).unwrap();
        }
        assert_eq!(quiesce_wintun(&mut r,h,ep,811,81),OK);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(release(&mut r,h),OK);
    }

    #[test]
    fn m0_windows_fixed6_frozen_linux_stream_same_block_parity_npf_maturity_fence(){
        // Native Windows scoped crypto+M1/M2 unit; not a genuine NPF syscall
        // or two-OS product run. The latter must remain separately NOT_RUN.
        let mut r=Registry{generation:800,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let tx=setup(&mut r,false,731,73);
        let rx=setup(&mut r,true,732,74);
        let ep=[2;16];
        {
            let mut e=r.entries[&tx].lock().unwrap();
            m2_arm_entry(&mut e,ep,731,73).expect("only protected feature7 and bound device may arm");
            assert_eq!(e.fec2_tx.as_ref().unwrap().revision().0,1);
        }
        let mut shared_block=None;
        let mut last_end=600u32;
        for i in 0..16u8{
            let plain=data(i.saturating_add(1));
            let (record,seq,pn)={
                let mut e=r.entries[&tx].lock().unwrap();
                let mut bytes=[0u8;2048];
                let (used,seq,pn)=stage_fixed_source_entry(
                    &mut e,ep,731,73,&plain,&mut bytes
                ).expect("W168 full-block source");
                assert_eq!(seq,last_end);
                let outstanding=m2_kernel_firstsend_entry(
                    &mut e,ep,731,73,pn,seq,used,1
                ).expect("real native driver callback shape, unit simulated");
                assert_eq!(outstanding,u32::from(i)+1);
                last_end=seq+used as u32;
                (bytes[..used].to_vec(),seq,pn)
            };
            assert_eq!(pn,u64::from(i));
            let delivered=open_symbol(&mut r,rx,ep,732,74,seq,&record).unwrap();
            assert_eq!(delivered.len(),1);
            let actual=&delivered[0];
            assert_eq!(actual.index,u32::from(i));
            assert_eq!(&actual.frame[..actual.length as usize],plain.as_slice());
            match shared_block{
                None=>shared_block=Some(actual.block_id),
                Some(old)=>assert_eq!(old,actual.block_id,"single frozen M1 block not source0/new-ID")
            }
        }
        let parity={
            let mut e=r.entries[&tx].lock().unwrap();
            stage_fixed_parity_entry(&mut e,ep,731,73).expect("frozen W168 staged parity quantum")
        };
        assert_eq!(parity.count,4);
        let mut prev=last_end;
        for row in &parity.rows[..parity.count as usize]{
            assert!(row.used>51);
            assert_eq!(row.seq,prev,"independent original immutable M1 sequence");
            prev=prev.wrapping_add(row.used);
            assert!(row.pn>=16,"parity burns its own authentic M3 PN");
        }
        {
            let mut e=r.entries[&tx].lock().unwrap();
            e.fec2_tx.as_mut().unwrap().settle_staged(4,0,0).unwrap();
            let m=e.m2.as_mut().unwrap();
            m.fec_copied_parity=4;
            assert_eq!(m.fec_copied_source,16);
            assert_eq!(m.fec_reverse_reports,0);
            assert_eq!(m.fec_positive_2s,0,"no invented APPLIED on local copy");
        }
        assert_eq!(quiesce_wintun(&mut r,tx,ep,731,73),OK);
        assert_eq!(quiesce_wintun(&mut r,rx,ep,732,74),OK);
        assert_eq!(stop(&mut r,tx),OK);
        assert_eq!(stop(&mut r,rx),OK);
        assert_eq!(release(&mut r,tx),OK);
        assert_eq!(release(&mut r,rx),OK);
    }


    #[test]
    fn m0_windows_auto_mature_667pps_drains_all_real_2s8s_deadlines(){
        // Original Rust M2 has TWO independent maturations per real DATA,
        // each shared batch stays 64. A delayed Windows readback must not
        // throttle 667/s actual kernel source throughput down to 320/s.
        let mut r=Registry{generation:986,entries:BTreeMap::new(),
            game_groups:BTreeMap::new()};
        let h=setup(&mut r,false,953,95);
        let epoch=[2;16];
        {
            let mut e=r.entries[&h].lock().unwrap();
            m2_arm_entry(&mut e,epoch,953,95).unwrap();
            let lane=e.owner.normal_firstsend_identity().unwrap().0;
            let m=e.m2.as_mut().unwrap();
            let start=m2_clock();
            for pn in 0..700u64{
                m.mature.as_mut().unwrap().on_first_send(
                    lane,wbd_recovery::FirstSendKind::Data,
                    wbd_recovery::FirstSendOutcome::Accepted{
                        pn:RecordPn(pn),wire_bytes:135
                    },
                    MonoNs(start.0+pn*1_500_000)
                ).unwrap();
            }
            let due=MonoNs(start.0+9_200_000_000);
            // One real owner turn is intentionally capped at 256 due
            // deadlines / 200us. A delayed 9.2s backlog must catch up
            // over bounded subsequent turns, never monopolize fresh DATA.
            for _ in 0..16{
                drain_original_auto_mature_due(m,due).unwrap();
                if m.auto_quality[0]==700 && m.auto_quality[5]==700{break}
            }
            assert_eq!(m.auto_quality[0],700,
                "all actual first-source 2s deadlines must mature");
            assert_eq!(m.auto_quality[5],700,
                "all actual first-source 8s deadlines must mature");
            assert_eq!(m.auto_quality[9],700,
                "without genuine M3 feedback, every sample is UNKNOWN");
            assert_eq!(m.fec_positive_2s,0,
                "kernel-first-send alone must never grant an M2 Applied");
            // A second readback at the same owner time is idempotent.
            drain_original_auto_mature_due(m,due).unwrap();
            assert_eq!(m.auto_quality[5],700);
            // Test advances only the pure M2 clock by 9.2s. The native
            // Wintun/Stop owner retains real wall time; relinquish this
            // synthetic clock before verifying production Stop.
            m.mature=None;
        }
        assert_eq!(quiesce_wintun(&mut r,h,epoch,953,95),OK);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(release(&mut r,h),OK);
    }

    #[test]
    fn m0_windows_fec2_revision_change_uses_linux_quiescent_and_new_m2_maturity(){
        let mut r=Registry{generation:987,entries:BTreeMap::new(),
            game_groups:BTreeMap::new()};
        let h=setup(&mut r,false,951,95);
        let ep=[2;16];
        {
            let mut e=r.entries[&h].lock().unwrap();
            m2_arm_entry(&mut e,ep,951,95).unwrap();
            assert_eq!(e.fec2_tx.as_ref().unwrap().revision().0,1);
            assert_eq!(fixed_initial_profile_entry(&mut e,ep,951,95,7),Err(INVALID));
            assert_eq!(fixed_initial_profile_entry(&mut e,ep,951,95,5),Ok(()));
            assert_eq!(e.fec2_tx.as_ref().unwrap().revision().0,1);
            assert_eq!(fixed_change_revision_entry(&mut e,ep,951,95,7,2),Err(INVALID));
            assert_eq!(fixed_change_revision_entry(&mut e,ep,951,95,2,1),Err(INVALID));
            // Simulate an actual M3-authenticated kind1 original event
            // before the new profile revision, not an outer TCP ACK.
            e.m2.as_mut().unwrap().fec_reverse_reports=3;
            assert_eq!(fixed_change_revision_entry(&mut e,ep,951,95,2,2),Ok(()));
            assert_eq!(e.fec2_tx.as_ref().unwrap().revision().0,2);
            let m=e.m2.as_ref().unwrap();
            assert_eq!(m.fec_copied_source,0);
            assert_eq!(m.fec_copied_parity,0);
            assert_eq!(m.fec_positive_2s,0);
            assert_eq!(m.fec_reverse_reports,0);
            assert_eq!(m.auto_reverse_base,3);
            // Real public Applied remains UNKNOWN: a new revision's
            // TLS-bound sender has NOT yet received M4 or mature M2 proof.
            let mut out=[0u8;2048];
            let frame=data(11);
            let (used,seq,pn)=stage_fixed_source_entry(
                &mut e,ep,951,95,&frame,&mut out
            ).expect("non-1 authenticated revision source must remain live");
            assert!(used>51);
            assert_eq!(seq,600);
            assert_eq!(pn,0);
            assert_eq!(m2_kernel_firstsend_entry(
                &mut e,ep,951,95,pn,seq,used,1),Ok(1));
            assert_eq!(e.m2.as_ref().unwrap().fec_copied_source,1);
            assert_eq!(e.m2.as_ref().unwrap().fec_copied_parity,0);
        }
        assert_eq!(quiesce_wintun(&mut r,h,ep,951,95),OK);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(release(&mut r,h),OK);
    }

    #[test]
    fn m0_windows_fixed6_native_authenticated_m2_reverse_feedback_same_owner(){
        // The genuine feature7 original-M3 source opener must emit a
        // canonical M2 kind1 through the SAME Rust M1 PN/SEQ owner.
        // NPF send disposition is simulated here, so no OS Applied claim.
        let mut r=Registry{generation:850,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let client=setup(&mut r,false,821,82);
        let server=setup(&mut r,true,822,83);
        let epoch=[2;16];
        {
            let mut e=r.entries[&client].lock().unwrap();
            m2_arm_entry(&mut e,epoch,821,82).unwrap();
        }
        {
            let mut e=r.entries[&server].lock().unwrap();
            m2_arm_entry(&mut e,epoch,822,83).unwrap();
        }
        let original=data(7);
        let payload={
            let e=r.entries[&server].lock().unwrap();
            let b=normal_off_windows_budget(&e).unwrap();
            fec_v2::source_owned(75,0,&original,b.record_payload_mtu).unwrap()
        };
        let (wire,seq,pn)=send(&mut r,server,822,83,2,&payload);
        {
            let mut e=r.entries[&server].lock().unwrap();
            assert_eq!(m2_kernel_firstsend_entry(&mut e,epoch,822,83,
                pn,seq,wire.len(),1),Ok(1));
        }
        let delivered=open_symbol(&mut r,client,epoch,821,82,seq,&wire).unwrap();
        assert_eq!(delivered.len(),1);
        assert_eq!(&delivered[0].frame[..delivered[0].length as usize],original.as_slice());
        std::thread::sleep(std::time::Duration::from_millis(12));
        let (receipt,feedback_seq)={
            let mut e=r.entries[&client].lock().unwrap();
            let mut out=[0u8;2048];
            let (used,seq,pn)=m2_next_feedback_entry(
                &mut e,epoch,821,82,&mut out
            ).expect("original feature7 reverse kind1 draft rejected")
             .expect("actual verified source must cause due kind1 receipt");
            assert!(used>=51&&used<=2048);
            m2_finish_feedback_entry(&mut e,epoch,821,82,pn,1).unwrap();
            (out[..used].to_vec(),seq)
        };
        let got=open_symbol(&mut r,server,epoch,822,83,feedback_seq,&receipt)
            .expect("same genuine M3 unique-PN opener must parse scoped M2");
        assert!(got.is_empty(),"authenticated kind1 is not business Wintun data");
        assert_eq!(r.entries[&server].lock().unwrap().m2.as_ref().unwrap()
            .shadow.outstanding(),0,"only genuine receipt may retire source");
        for (h,luid,index) in [(client,821,82),(server,822,83)]{
            assert_eq!(quiesce_wintun(&mut r,h,epoch,luid,index),OK);
            assert_eq!(stop(&mut r,h),OK);
            assert_eq!(release(&mut r,h),OK);
        }
    }

}
