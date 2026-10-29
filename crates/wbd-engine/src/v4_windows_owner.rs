//! Windows-only developer-opt-in half of the *original* credential-checked
//! Go V4 -> Rust private owner handoff. NO Windows product network activation.
//! The caller must be the same-process original Go post-TLS callback; valid
//! cold248/WBGH bytes alone are NOT credentials or a kernel driver lease.
//! This module reuses the normal M1/M3 ProtectedScopedOwner, not fake crypto.
#![cfg(all(target_os="windows",feature="m0_v4_embedded_go"))]
use std::collections::{BTreeMap,BTreeSet,VecDeque};
use std::sync::{Arc,Mutex,OnceLock};
use std::time::Instant;
use crate::cold_v4::{UntrustedColdV4,COLD_V4_LEN};
#[path = "v4_windows_native_runtime.rs"]
mod native_runtime;
#[path = "v4_windows_game_owner.rs"]
mod game;
#[cfg(feature="fec2_product_record")]
#[path = "v4_windows_game_native_runtime.rs"]
mod game_native;
#[cfg(feature="fec2_product_record")]
#[path = "v4_windows_rust_auto.rs"]
mod auto_native;
#[cfg(feature="fec2_product_record")]
#[path = "v4_windows_fec2_owner.rs"]
mod fec2;
use crate::v4_protected_handoff::{PrivateGoV4Handoff,HANDOFF_V1_LEN};
use crate::v4_owner_crypto::ProtectedScopedOwner;
use crate::memory::{Arena,FrozenRecord};
use crate::runtime::early_rx::EarlyAccepted;
use crate::runtime::{TxDispatch,RxPacket};
use wbd_types::{MonoNs,RecordPn};
use wbd_types::buffer_contract::{UniqueSealable,FrozenRecordHandle};
use wbd_codec::path_budget::{FrameBudget,FrameBudgetInput,FecReservation};
use wbd_codec::link_fec_wire::{inspect_link,LinkMode,LinkView};
use wbd_codec::record_frame::FIXED_WIRE_OVERHEAD;
use wbd_recovery::{BudgetDirection,WireDirection,ReceiptConfig,ReceiptState,ReceiptRouteScope,ReceiptOpenFacts,ReceiptPage,ScopedAuthenticatedReceipt,GlobalRepairAllocator,GlobalRepairConfig,RepairBudgetConfig,RepairCandidate,GrantLease,GlobalReservationId,RepairSendResult,reserve_frozen_submission,complete_driver_prefix,DriverPrefixObservation,BatchSuffixEvidence,RxFeedbackState,RxFeedbackConfig,FeedbackDraft,FeedbackSendResult};

const OK:i32=0;
const INVALID:i32=1;
const UNKNOWN:i32=2;
const BAD_STAGE:i32=3;
const FULL:i32=4;
const STOP_INCOMPLETE:i32=5;
const MAX_SESSIONS:usize=16;
// Genuine AEAD+unique-PN kind1 receives pending exact M2 route binding.
const MAX_AUTHENTICATED_KIND1:usize=32;
// Original M1 arena has 64 slots: hold at most 48 DATA shadows + one
// pending first-send while leaving room for RX and authentic control.
const MAX_M2_FROZEN:usize=24_576; // Normal/off independent snapshots only
const MAX_M2_FIXED_FROZEN:usize=1536; // preserve existing Fixed FEC arena-backed shadow and tests
// Source-observed Windows Netem300/600ms RTT step: startup low RTT samples
// shortened v3 H to 250ms, retiring ~all shadows BEFORE authentic feedback.
// Bound Normal-only protection to the original 600ms RTT bootstrap horizon;
// no blind PTO, no percentage increase, no retained fresh M1 slabs.
const WIN_NORMAL_M2_MIN_RETAIN_NS:u64=1_200_000_000;
const M2_HARD_EXPIRY_NS:u64=2_000_000_000;
const MAX_EARLY:u32=32;
const PH_PREPARED:u32=1;
const PH_ACTIVE:u32=2;
const PH_STOPPED:u32=3;
const PH_STOPPING:u32=4;
const ABI_V1:u32=1;
const HANDLE_KIND:u64=0x574Eu64; // not a generic public engine token
// Explicitly 0: even an authenticated native Rust owner without a trusted
// Windows M4 device and OS WFP/route readback has not APPLIED a product.
const PRODUCT_APPLIED:u32=0;

// The SAME original protected TLS lane and M1 FrozenRecord handles are
// authoritative. Fresh shadow admission is only after the synchronous real
// Npcap pcap_sendpacket return; TCP cumulative ACK cannot call this owner.
struct WindowsM2QueuedRepair {
    candidate:RepairCandidate<FrozenRecord>,
    lease:GrantLease,
    reservation_id:GlobalReservationId,
}
struct WindowsOriginalM2 {
    shadow:ReceiptState<FrozenRecord>,
    pending:BTreeMap<RecordPn,FrozenRecord>,
    direction:BudgetDirection,
    route:ReceiptRouteScope,
    in_flight:Option<WindowsM2QueuedRepair>,
    ready_repairs:VecDeque<RepairCandidate<FrozenRecord>>, // one bounded 32-candidate M2 turn
    reverse_authenticated_receipts:u64,
    repair_polls:u64,
    repair_preflight_stale:u64,
    repair_quota_rejected:u64,
    // Feedback comes ONLY from this original M3 opener's unique reverse PN.
    // At most one immutable original-M1 kind1 draft is awaiting real NPF send.
    feedback:RxFeedbackState,
    feedback_pending:Option<(Option<FeedbackDraft>,u64,bool)>,
    // Per-lane state, no thread/timer; TX Health deadline not yet activated.
    health:crate::v4_native_health::HealthClock,
    // Same W168 mature source-only denominator as Linux Fixed; never a
    // Go carrier ACK or configuration-intent receipt.
    #[cfg(feature="fec2_product_record")]
    mature:Option<wbd_recovery::MatureFirstSend>,
    #[cfg(feature="fec2_product_record")]
    fec_copied_source:u64,
    #[cfg(feature="fec2_product_record")]
    fec_copied_parity:u64,
    #[cfg(feature="fec2_product_record")]
    fec_reverse_reports:u64,
    #[cfg(feature="fec2_product_record")]
    fec_positive_2s:u64,
    #[cfg(feature="fec2_product_record")]
    fec_covered_2s:u64,
    #[cfg(feature="fec2_product_record")]
    fec_censored:bool,
    // A temporary quality metadata shortage is interval UNKNOWN, never
    // a permanent dead session or a forged line-loss measurement.
    #[cfg(feature="fec2_product_record")]
    fec_last_capacity_at:Option<MonoNs>,
    // Same Linux M2 first-send 2s/8s and closed-block k histogram
    // exported to the one shared Go FecV2Step Auto policy. These are
    // CUMULATIVE, not fabricated success from TCP appearance ACK.
    #[cfg(feature="fec2_product_record")]
    auto_quality:[u64;30],
    // The native revision-local MatureFirstSend resets on a real profile
    // change. Keep only genuinely M3-authenticated reverse reports
    // cumulative for Linux FecV2Step's monotone 8s delta projection.
    #[cfg(feature="fec2_product_record")]
    auto_reverse_base:u64,
}
// Exact Linux v3 half-sampled PN/generation selection and global bounded PPS.
// No RNG, time query or global mutex per business packet; now comes from M2.
fn win_v3_pps_permit(counter:&std::sync::atomic::AtomicU64,
    now:MonoNs,max_packets:u64)->bool {
    use std::sync::atomic::Ordering;
    let epoch=(now.0/1_000_000_000)&0xffff_ffff;
    counter.fetch_update(Ordering::Relaxed,Ordering::Relaxed,|old|{
        let count=if (old>>32)==epoch {old&0xffff_ffff}else{0};
        (count<max_packets).then_some((epoch<<32)|(count+1))
    }).is_ok()
}
fn win_v3_sample(pn:u64,lane:wbd_types::LaneKey)->bool {
    let key=pn^((lane.tunnel.slot as u64)<<48)
        ^((lane.tunnel.generation as u64)<<32)
        ^((lane.slot as u64)<<16)^(lane.generation as u64);
    let mut x=key.wrapping_add(0x9e3779b97f4a7c15);
    x=(x^(x>>30)).wrapping_mul(0xbf58476d1ce4e5b9);
    x=(x^(x>>27)).wrapping_mul(0x94d049bb133111eb);
    x^=x>>31;
    x&1==0
}
fn win_v3_admit_shadow(pn:u64,lane:wbd_types::LaneKey,now:MonoNs)->bool {
    static ADMISSIONS:std::sync::atomic::AtomicU64=
        std::sync::atomic::AtomicU64::new(0);
    win_v3_sample(pn,lane) && win_v3_pps_permit(&ADMISSIONS,now,32_768)
}
fn win_v3_send_pps_permit(now:MonoNs)->bool {
    static REPAIRS:std::sync::atomic::AtomicU64=
        std::sync::atomic::AtomicU64::new(0);
    win_v3_pps_permit(&REPAIRS,now,8_192)
}
/// Rust-Auto desired vs genuine M2-verified Applied, read-only cold C ABI.
#[cfg(feature="fec2_product_record")]
#[repr(C)]
pub struct WbdWindowsRustAutoStateV1{
    pub version:u32,pub size:u32,
    pub requested_revision:u64,pub applied_revision:u64,
    pub profile:u32,pub applied:u32,
}
#[cfg(feature="fec2_product_record")]
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v9_rust_auto_state(
    handle:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
    out:*mut WbdWindowsRustAutoStateV1,size:u32,
)->i32{
    if out.is_null()||size!=std::mem::size_of::<WbdWindowsRustAutoStateV1>() as u32{
        return INVALID
    }
    let Some(epoch)=v3_epoch(epoch,epoch_len)else{return INVALID};
    let lane={
        let Ok(registry)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=registry.entries.get(&handle)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(e)=lane.lock()else{return BAD_STAGE};
    if !v3_ready(&e,epoch,luid,ifindex)||!e.feature7||
        e.game_group.is_some(){return BAD_STAGE}
    let Some(actor)=e.auto_actor.as_ref()else{return BAD_STAGE};
    let Some(m)=e.m2.as_ref()else{return BAD_STAGE};
    let valid=m.fec_copied_source>0&&m.fec_copied_parity>0&&
        m.fec_reverse_reports>0&&
        (m.fec_positive_2s>0||m.fec_covered_2s>0)&&
        !m.fec_censored&&
        m.fec_last_capacity_at.is_none_or(|at|m2_clock().0.saturating_sub(at.0)>=8_000_000_000);
    let requested_revision=actor.revision();
    unsafe{out.write(WbdWindowsRustAutoStateV1{
        version:1,size,requested_revision,
        applied_revision:if valid{requested_revision}else{0},
        profile:u32::from(actor.profile()),applied:u32::from(valid),
    })};
    OK
}

// Authenticated cold original-Go TLS / scoped M4 device health policy.
// A config write never claims network/GUI Applied. The effective readback
// comes from the same native Rust HealthClock the TX worker really uses.
#[repr(C)]
#[derive(Clone,Copy)]
pub struct WbdWinHealthPolicyV1{
    pub version:u32,pub size:u32,
    pub interval_seconds:u32,pub dead_seconds:u32,
    pub dormant_seconds:u32,pub configured:u32,
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v9_native_health_config(
    handle:u64,epoch_ptr:*const u8,epoch_len:usize,
    luid:u64,ifindex:u32,ptr:*const WbdWinHealthPolicyV1,
)->i32{
    if ptr.is_null(){return INVALID}
    let c=unsafe{*ptr};
    if c.version!=1||c.size as usize!=std::mem::size_of::<WbdWinHealthPolicyV1>()||
        c.configured!=0{return INVALID}
    let Some(epoch)=v3_epoch(epoch_ptr,epoch_len)else{return INVALID};
    let interval=u64::from(c.interval_seconds).saturating_mul(1_000_000_000);
    let dead=u64::from(c.dead_seconds).saturating_mul(1_000_000_000);
    let dormant=(c.dormant_seconds>0).then_some(
        u64::from(c.dormant_seconds).saturating_mul(1_000_000_000));
    let Some(policy)=crate::v4_native_health::HealthPolicy::new(
        interval,dead,dormant)else{return INVALID};
    if native_runtime::active_owner(handle){return BAD_STAGE}
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&handle)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    if !v3_ready(&e,epoch,luid,ifindex)||
        e.role_server||e.game_group.is_some(){return BAD_STAGE}
    let Some(m)=e.m2.as_mut()else{return BAD_STAGE};
    if m.shadow.outstanding()>0||m.in_flight.is_some()||
        m.feedback_pending.is_some(){return BAD_STAGE}
    m.health=crate::v4_native_health::HealthClock::new(policy,m2_clock().0);
    OK
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v9_native_health_effective(
    handle:u64,epoch_ptr:*const u8,epoch_len:usize,
    luid:u64,ifindex:u32,out:*mut WbdWinHealthPolicyV1,
)->i32{
    if out.is_null(){return INVALID}
    let Some(epoch)=v3_epoch(epoch_ptr,epoch_len)else{return INVALID};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&handle)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(e)=lane.lock()else{return BAD_STAGE};
    if !v3_ready(&e,epoch,luid,ifindex)||
        e.role_server||e.game_group.is_some(){return BAD_STAGE}
    let Some(m)=e.m2.as_ref()else{return BAD_STAGE};
    let p=m.health.policy();
    unsafe{out.write(WbdWinHealthPolicyV1{
        version:1,size:std::mem::size_of::<WbdWinHealthPolicyV1>() as u32,
        interval_seconds:(p.interval_ns()/1_000_000_000) as u32,
        dead_seconds:(p.dead_ns()/1_000_000_000) as u32,
        dormant_seconds:p.dormant_ns().map_or(0,|v|(v/1_000_000_000) as u32),
        configured:1,
    })};
    OK
}
fn m2_clock()->MonoNs{
    static START:OnceLock<Instant>=OnceLock::new();
    let elapsed=START.get_or_init(Instant::now).elapsed().as_nanos();
    MonoNs(elapsed.min(u128::from(u64::MAX)) as u64)
}
fn m2_global()->&'static Mutex<GlobalRepairAllocator>{
    static GLOBAL:OnceLock<Mutex<GlobalRepairAllocator>>=OnceLock::new();
    GLOBAL.get_or_init(||Mutex::new(GlobalRepairAllocator::new(
        GlobalRepairConfig{
            // Absolute safety caps above 9% v3 credit for simultaneous
            // 500Mbps outer C2S + S2C; v3 share and actual first-send
            // receipt remain the authoritative *lower* ceilings.
            max_bytes_per_epoch:14_000_000,max_directions:32,
            max_grant_bytes:262_144,max_grant_lifetime_ns:50_000_000,
            max_pending:256,max_pending_bytes:524_288,
        },MonoNs(0)).expect("bounded M2 process allocator")))
}
fn m2_arm_entry(e:&mut Entry,epoch:[u8;16],luid:u64,ifindex:u32)->Result<(),i32>{
    if !v3_ready(e,epoch,luid,ifindex)||e.m2.is_some() {
        return Err(BAD_STAGE)
    }
    let (lane,protected_epoch)=e.owner.normal_firstsend_identity().ok_or(BAD_STAGE)?;
    if protected_epoch!=epoch{return Err(INVALID)}
    let outbound=if e.role_server{WireDirection::ServerToClient}
        else{WireDirection::ClientToServer};
    let direction=BudgetDirection{tunnel:lane.tunnel,direction:outbound};
    let all=(RecordPn(0),RecordPn(u64::MAX));
    let route=ReceiptRouteScope::checked(lane,lane,outbound,epoch,all,all)
        .map_err(|_|INVALID)?;
    // Windows original Go/Npcap M2 uses W168's *same opportunistic-v3*
    // policy, not pre-freeze PTO/RACK blind two-repair retries. The verified
    // original sender holds at most 24,576 separately charged immutable snapshots.
    let mut shadow=ReceiptState::new(lane,ReceiptConfig{
        max_shadow_entries:if e.feature7{MAX_M2_FIXED_FROZEN}else{MAX_M2_FROZEN},
        pto_ns:810_000_000,
        reorder_window_ns:20_000_000,
    }).map_err(|_|INVALID)?;
    shadow.enable_adaptive_timing(600_000_000,50_000_000)
        .map_err(|_|BAD_STAGE)?;
    shadow.enable_opportunistic_v3().map_err(|_|BAD_STAGE)?;
    let feedback=RxFeedbackState::new(RxFeedbackConfig{
        max_retained_pages:1024,max_pages_per_report:8,
        retention_ns:2_000_000_000,srtt_ns:600_000_000,
    }).map_err(|_|INVALID)?;
    let now=m2_clock();
    let mut g=m2_global().lock().map_err(|_|BAD_STAGE)?;
    g.register(direction,RepairBudgetConfig{
        outer_mtu:u64::from(e.path_mtu).saturating_add(54),
        max_repair_bytes_per_epoch:7_000_000,max_pending_reservations:256,
        max_pending_bytes:524_288,io_timeout_ns:100_000_000,
    },now).map_err(|_|BAD_STAGE)?;
    if g.enable_opportunistic_v3(direction).is_err() ||
        g.bind_receipt_route(direction,route,now).is_err(){
        let _=g.retire_tunnel(lane.tunnel,now);
        return Err(BAD_STAGE)
    }
    #[cfg(feature="fec2_product_record")]
    let mature=if e.feature7 {
        Some(wbd_recovery::MatureFirstSend::new(
            route,wbd_recovery::MaturityConfig{max_live_data:524_288},now
        ).map_err(|_|BAD_STAGE)?)
    }else{None};
    #[cfg(feature="fec2_product_record")]
    if e.feature7 {
        let budget=normal_off_windows_budget(e)?;
        // Exactly the Linux frozen M1 source grouping / staged-parity owner.
        // Fixed6 equals Linux W168 Maximum profile 6; same class grouping,
        // k<=16, r<=20, no alternative Windows FEC scheduler.
        e.fec2_tx=Some(crate::v4_fixed_stream::FixedStream::new(
            6,1,budget.record_payload_mtu
        ).ok_or(BAD_STAGE)?);
    }
    e.m2=Some(WindowsOriginalM2{
        shadow,pending:BTreeMap::new(),direction,route,in_flight:None,
        ready_repairs:VecDeque::with_capacity(32),
        reverse_authenticated_receipts:0,repair_polls:0,
        repair_preflight_stale:0,repair_quota_rejected:0,
        feedback,feedback_pending:None,
        health:crate::v4_native_health::HealthClock::new(
            crate::v4_native_health::HealthPolicy::default_connected(),now.0),
        #[cfg(feature="fec2_product_record")]
        mature,
        #[cfg(feature="fec2_product_record")]
        fec_copied_source:0,
        #[cfg(feature="fec2_product_record")]
        fec_copied_parity:0,
        #[cfg(feature="fec2_product_record")]
        fec_reverse_reports:0,
        #[cfg(feature="fec2_product_record")]
        fec_positive_2s:0,
        #[cfg(feature="fec2_product_record")]
        fec_covered_2s:0,
        #[cfg(feature="fec2_product_record")]
        fec_censored:false,
        #[cfg(feature="fec2_product_record")]
        fec_last_capacity_at:None,
        #[cfg(feature="fec2_product_record")]
        auto_quality:[0;30],
        #[cfg(feature="fec2_product_record")]
        auto_reverse_base:0,
    });
    Ok(())
}
// S865 original TLS-bound Windows reverse feedback: one bounded M3-unique
// receipt draft. No TCP-appearance ACK, untrusted carrier, or replayed PN
// may create a bit in this original-Go M2 receive bitmap.
fn m2_next_feedback_entry(e:&mut Entry,epoch:[u8;16],luid:u64,
    ifindex:u32,out:&mut [u8]
)->Result<Option<(usize,u32,u64)>,i32>{
    if !v3_ready(e,epoch,luid,ifindex){return Err(INVALID)}
    let now=m2_clock();
    let (draft,health_due)={
        let m=e.m2.as_mut().ok_or(BAD_STAGE)?;
        if m.feedback_pending.is_some(){return Ok(None)}
        let draft=m.feedback.on_due(now);
        let health_due=m.health.tx_due(now.0);
        if draft.is_none()&&!health_due{return Ok(None)}
        (draft,health_due)
    };
    let prepared=(||->Result<(usize,u32,u64),i32>{
        let msg=draft.as_ref().map(|d|wbd_codec::Receipt{
            largest_data_pn:d.largest_data_pn().0,
            ack_delay_us:0,report_seq:d.report_seq(),
            pages:d.pages().iter().map(|p|wbd_codec::ReceiptPage{
                base_pn:p.base_pn.0,bitmap:p.bitmap,
            }).collect(),
        });
        // A genuine M2/Quality draft carries the same authenticated idle
        // evidence. Its confirmed native NPF copy defers standalone Health.
        let budget=normal_off_windows_budget(e)?;
        let m=e.m2.as_ref().ok_or(BAD_STAGE)?;
        let tlv=crate::v4_native_health::encode_authenticated_health_live(
            m.health.local_idle_ns(now.0),msg.as_ref(),None,
            budget.record_payload_mtu.min(out.len().saturating_sub(FIXED_WIRE_OVERHEAD))
        ).map_err(|_|INVALID)?;
        // Preflight the *actual encoded receipt* against the caller's
        // C ABI output BEFORE spending an AEAD PN and original TCP sequence.
        // A short buffer is backpressure, not a silently emitted control:
        // returning Ok(None) after seal would strand exactly one ciphertext
        // length in Rust's stream while Go's sendNext stayed unchanged.
        let needed=tlv.len().checked_add(FIXED_WIRE_OVERHEAD).ok_or(FULL)?;
        if needed>out.len(){return Err(FULL)}
        let slab=e.arena.allocate().map_err(|_|FULL)?;
        let (pn,seq,used)=e.owner.seal_original_authenticated_receipt(
            slab,&tlv,budget,15,now
        ).map_err(|_|BAD_STAGE)?;
        let storage=std::mem::take(&mut e.tx_scratch);
        let batch=match e.owner.drain_tx(now,storage){
            Ok(batch)=>batch,
            Err((_,storage))=>{
                e.tx_scratch=storage;
                return Err(BAD_STAGE)
            },
        };
        let read=(||{
            let ready=e.owner.checked_tx_ready(&batch).map_err(|_|BAD_STAGE)?;
            if ready.len()!=1 || ready[0].record.bytes().len()!=used ||
                ready[0].record.metadata().pn!=RecordPn(pn) ||
                ready[0].record.metadata().seq.0 as u32!=seq {
                return Err(BAD_STAGE)
            }
            // Should be impossible after preflight. Never demote a
            // post-seal inconsistency to optional/no-feedback (FULL):
            // the Rust PN/sequence has already advanced and Go must Stop.
            if used!=needed || used>out.len(){return Err(BAD_STAGE)}
            out[..used].copy_from_slice(ready[0].record.bytes());
            Ok((used,seq,pn))
        })();
        e.tx_scratch=batch.recycle();
        read
    })();
    let m=e.m2.as_mut().ok_or(BAD_STAGE)?;
    match prepared{
        Ok((n,seq,pn))=>{
            m.feedback_pending=Some((draft,pn,true));
            Ok(Some((n,seq,pn)))
        },
        Err(err)=>{
            // No NPF syscall accepted this draft: restore dirty coverage.
            if let Some(draft)=draft.as_ref(){
                let _=m.feedback.on_send_result(
                    draft,FeedbackSendResult::NotSent,now
                );
            }
            m.health.on_health_send_result(now.0,false);
            if err==FULL{Ok(None)}else{Err(err)}
        },
    }
}
fn m2_finish_feedback_entry(e:&mut Entry,epoch:[u8;16],luid:u64,
    ifindex:u32,pn:u64,npcap_sent:u32
)->Result<(),i32>{
    if !v3_ready(e,epoch,luid,ifindex)||npcap_sent>1{return Err(INVALID)}
    let m=e.m2.as_mut().ok_or(BAD_STAGE)?;
    let Some((_,expected,_))=m.feedback_pending.as_ref()
        else{return Err(BAD_STAGE)};
    if *expected!=pn{return Err(INVALID)}
    let (draft,_,has_health)=m.feedback_pending.take().ok_or(BAD_STAGE)?;
    let now=m2_clock();
    if let Some(draft)=draft.as_ref(){
        m.feedback.on_send_result(draft,if npcap_sent==1{
            FeedbackSendResult::Accepted
        }else{FeedbackSendResult::NotSent},now).map_err(|_|BAD_STAGE)?;
    }
    if has_health{m.health.on_health_send_result(now.0,npcap_sent==1)}
    Ok(())
}
fn m2_kernel_firstsend_entry(e:&mut Entry,epoch:[u8;16],luid:u64,
    ifindex:u32,pn:u64,seq:u32,wire_len:usize,sent:u32,
)->Result<u32,i32>{
    // 2 is explicit unknown driver completion, not definitely NotSent:
    // burn the original PN without fabricating peer delivery or fresh F.
    if !v3_ready(e,epoch,luid,ifindex)||sent>2{return Err(INVALID)}
    let m=e.m2.as_mut().ok_or(BAD_STAGE)?;
    let key=RecordPn(pn);
    let row=m.pending.get(&key).ok_or(INVALID)?;
    if row.metadata().pn!=key||row.metadata().seq.0 as u32!=seq
        ||row.bytes().len()!=wire_len {return Err(INVALID)}
    let frozen=m.pending.remove(&key).ok_or(INVALID)?;
    #[cfg(feature="fec2_product_record")]
    if let Some(mature)=m.mature.as_mut(){
        let (lane,_) = e.owner.normal_firstsend_identity().ok_or(BAD_STAGE)?;
        let observation=match sent {
            1=>wbd_recovery::FirstSendOutcome::Accepted{
                pn:key,wire_bytes:(wire_len as u64).saturating_add(54)
            },
            2=>wbd_recovery::FirstSendOutcome::Uncertain{
                pn:key,wire_bytes:(wire_len as u64).saturating_add(54)
            },
            _=>wbd_recovery::FirstSendOutcome::DefinitelyNotSent{pn:key},
        };
        match mature.on_first_send(
            lane,wbd_recovery::FirstSendKind::Data,observation,m2_clock()
        ){
            Ok(())=>{},
            // Auto quality metadata is optional to fresh M4 delivery.
            // A saturated observer counts censored capacity but cannot
            // convert a real NPF firstsend into a fatal DATA-path error.
            Err(wbd_recovery::MaturityError::CapacityLimited)=>{
                m.fec_last_capacity_at=Some(m2_clock());
            },
            Err(_)=>{m.fec_censored=true;return Err(BAD_STAGE)},
        }
        if sent==1{m.fec_copied_source=m.fec_copied_source.saturating_add(1)}
    }
    if sent!=1{return Ok(m.shadow.outstanding() as u32)}
    // The caller's synchronous pcap_sendpacket success is a copied
    // kernel submission, NEVER proof of remote peer delivery.
    let now=m2_clock();
    let bytes=wire_len.checked_add(54).ok_or(INVALID)? as u64;
    let mut global=m2_global().lock().map_err(|_|BAD_STAGE)?;
    global.on_fresh_accepted(m.direction,bytes,now).map_err(|_|BAD_STAGE)?;
    // Every successful NPF submission counts as a first send. Repair
    // retention is optional under v3, not an ACK window or DATA credit.
    // Keep a bounded immutable shadow while there is room; once saturated,
    // release only the optional copy, never reject accepted fresh traffic.
    if e.feature7 {
        // Fixed/Auto still uses the historical 1536-slot original M1
        // contract. This Normal/off-only opportunity repair must not
        // silently change Fixed FEC protected regression semantics.
        if m.shadow.outstanding()<MAX_M2_FIXED_FROZEN {
            m.shadow.on_sent_adaptive(frozen,now).map_err(|_|BAD_STAGE)?;
        }
    }else if m.shadow.outstanding()<MAX_M2_FROZEN &&
        win_v3_admit_shadow(pn,m.route.outbound_lane(),now) {
        // Linux v3 exact frozen-record detached repair snapshot:
        // returned first-send M1 loan is never pinned through an RTT.
        // Candidate memory denial is optional and cannot fail fresh DATA.
        if let Some(snapshot)=frozen.try_v3_repair_snapshot(){
            let _=m.shadow.on_sent_adaptive_with_floor(
                snapshot,now,WIN_NORMAL_M2_MIN_RETAIN_NS);
        }
    }
    Ok(m.shadow.outstanding() as u32)
}
// Poll is owner-time-only; an actual repair remains byte-exact from its
// original M1 FrozenRecord and gets a GLOBAL process quota reservation BEFORE
// going to the Windows Npcap sink. No private Go 750ms reseal/retry timer.
// Successful return publishes one bounded repair candidate for Go to send;
// no candidate never fabricates a peer ACK or consumes a new AEAD PN.
fn m2_next_repair_entry(e:&mut Entry,epoch:[u8;16],luid:u64,
    ifindex:u32,out:&mut [u8],
)->Result<Option<(usize,u32,u64)>,i32>{
    if !v3_ready(e,epoch,luid,ifindex){return Err(INVALID)}
    let m=e.m2.as_mut().ok_or(BAD_STAGE)?;
    if m.in_flight.is_some(){return Err(BAD_STAGE)}
    let now=m2_clock();
    m.repair_polls+=1;
    // A single timer call supplies up to 32 ready candidates; Windows
    // previously threw away every one after the first. Preserve the bounded
    // turn and recheck authenticated positives just before driver send.
    if m.ready_repairs.is_empty(){
        m.ready_repairs.extend(m.shadow.on_timer(now).candidates);
    }
    while let Some(candidate)=m.ready_repairs.pop_front(){
        if !m.shadow.preflight(&candidate,now){
            m.repair_preflight_stale+=1;continue
        }
        if !win_v3_send_pps_permit(now){
            let _=m.shadow.on_send_result(&candidate,RepairSendResult::NotSent,now);
            continue
        }
        let wire=candidate.frozen().bytes();
        if wire.len()>out.len()||wire.len()>2048 { 
            let _=m.shadow.on_send_result(&candidate,RepairSendResult::NotSent,now);
            continue
        }
        let bytes=wire.len().checked_add(54).ok_or(INVALID)? as u64;
        let mut g=m2_global().lock().map_err(|_|BAD_STAGE)?;
        let lease=match g.grant(m.direction,bytes,40_000_000,now){
            Ok(v)=>v,
            Err(_)=>{
                m.repair_quota_rejected+=1;
                let _=m.shadow.on_send_result(&candidate,RepairSendResult::NotSent,now);
                continue
            }
        };
        let submission=reserve_frozen_submission(
            &mut g,lease,m.route,&m.shadow,&candidate,bytes,now
        );
        let reservation_id=match submission {
            Ok(v) if v.driver.metadata==candidate.frozen().metadata()
                && v.driver.wire.as_ptr()==candidate.frozen().bytes().as_ptr() =>
                v.reservation_id,
            _=>{
                let _=g.revoke(lease,now);
                let _=m.shadow.on_send_result(&candidate,RepairSendResult::NotSent,now);
                continue
            }
        };
        let n=wire.len();
        let seq=candidate.frozen().metadata().seq.0 as u32;
        let pn=candidate.pn().0;
        // Only a byte-for-byte copy into the Go carrier writer: original M1
        // frozen ciphertext itself stays pinned through actual kernel send.
        out[..n].copy_from_slice(wire);
        m.in_flight=Some(WindowsM2QueuedRepair{
            candidate,lease,reservation_id
        });
        return Ok(Some((n,seq,pn)));
    }
    Ok(None)
}
fn m2_complete_repair_entry(e:&mut Entry,epoch:[u8;16],luid:u64,
    ifindex:u32,pn:u64,sent:u32
)->Result<u32,i32>{
    if !v3_ready(e,epoch,luid,ifindex)||sent>2{return Err(INVALID)}
    let m=e.m2.as_mut().ok_or(BAD_STAGE)?;
    let held=m.in_flight.take().ok_or(BAD_STAGE)?;
    if held.candidate.pn()!=RecordPn(pn){
        m.in_flight=Some(held);return Err(INVALID)
    }
    let now=m2_clock();
    let observation=DriverPrefixObservation::checked(
        1,usize::from(sent==1),if sent==1{None}else{Some(0)},
        BatchSuffixEvidence::Unproven
    ).map_err(|_|BAD_STAGE)?;
    let mut g=m2_global().lock().map_err(|_|BAD_STAGE)?;
    let settled=complete_driver_prefix(
        &mut g,&[(held.reservation_id,m.route)],observation,now
    );
    let status=match settled{
        Ok(v)=>v.shadow_result(0).unwrap_or(RepairSendResult::Uncertain),
        Err(_)=>RepairSendResult::Uncertain,
    };
    // If a real authenticated reverse ACK arrived between polls, the
    // candidate is now stale and must never resurrect a retired shadow.
    let _=m.shadow.on_send_result(&held.candidate,status,now);
    let _=g.revoke(held.lease,now);
    Ok(m.shadow.outstanding() as u32)
}
fn m2_authenticated_kind1_entry(e:&mut Entry,reverse_pn:u64,
    control:&crate::v4_native_health::AuthenticatedControl,
)->Result<u32,i32>{
    let m=e.m2.as_mut().ok_or(BAD_STAGE)?;
    let now=m2_clock();
    if let Some(idle)=control.peer_idle_ns{
        m.health.on_peer_idle_hint(now.0,idle);
    }else{m.health.on_authenticated_control(now.0)}
    let Some(receipt)=control.receipt.as_ref()else{return Ok(0)};
    let opened=ReceiptOpenFacts{
        verified_reverse_lane:m.route.outbound_lane(),
        verified_reverse_direction:if e.role_server {
            WireDirection::ClientToServer
        }else{WireDirection::ServerToClient},
        verified_tunnel_epoch:e.authenticated_epoch,
        control_record_pn:RecordPn(reverse_pn),
    };
    let pages=receipt.pages.iter().map(|p|ReceiptPage{
        base_pn:RecordPn(p.base_pn),bitmap:p.bitmap,
    }).collect();
    let scoped=ScopedAuthenticatedReceipt::checked_after_open(
        m.route,opened,RecordPn(receipt.largest_data_pn),
        receipt.report_seq,pages,
    ).map_err(|_|INVALID)?;
    #[cfg(feature="fec2_product_record")]
    if let Some(mature)=m.mature.as_mut(){
        if mature.on_authenticated_receipt(&scoped,now).is_err(){
            m.fec_censored=true;return Err(BAD_STAGE)
        }
        m.fec_reverse_reports=m.fec_reverse_reports.saturating_add(1);
    }
    let mut global=m2_global().lock().map_err(|_|BAD_STAGE)?;
    let releases=global.observe_scoped_receipt(
        m.direction,&mut m.shadow,&scoped,now
    ).map_err(|_|INVALID)?;
    m.reverse_authenticated_receipts+=1;
    Ok(releases.len() as u32)
}
struct Entry {
    generation:u32,
    phase:u32,
    role_server:bool,
    rx_boundary:u32,
    rx_unwrapped_high:u64, // original Go Detach boundary, serial wrap safe
    limit:u16,
    count:u32,
    bytes:u32,
    owner:ProtectedScopedOwner,
    arena:Arena,
    // Returned M1 loan containers are re-used across bounded records.
    // Packet ownership still lives in the original generation arena.
    tx_scratch:Vec<TxDispatch>,
    rx_scratch:Vec<RxPacket>,
    // Only the exact original Go TLS-derived M3 opener can append here.
    // This is a bounded M2 ingress staging lane, NOT an ACK or a repair grant.
    authenticated_kind1:VecDeque<(u64,wbd_codec::Receipt)>,
    m2:Option<WindowsOriginalM2>,
    authenticated_epoch:[u8;16],
    peer_mss:u16,
    peer_mss_advertised:bool,
    record_wire_limit:usize,
    // Real pinned Win32 interface MTU, enrolled after M4 Wintun Hold.
    path_mtu:u16,
    device:Option<ScopedWindowsWintunIdentity>,
    feature7:bool,
    #[cfg(feature="fec2_product_record")]
    fec2_tx:Option<crate::v4_fixed_stream::FixedStream>,
    #[cfg(feature="fec2_product_record")]
    auto_actor:Option<auto_native::NativeAutoActor>,
    game_cold:Option<UntrustedColdV4>,
    game_group:Option<u64>,
    #[cfg(feature="fec2_product_record")]
    fec2_rx:Option<crate::v4_fec2_live_rx::Fec2LiveRx>,
}
// An original-Go-verified WintunReservation.Hold on the actual native OS
// adapter is REQUIRED before this private record can be created. This C ABI
// cannot itself open or validate a Wintun and does NOT grant OS Apply.
#[derive(Clone,Copy)]
struct ScopedWindowsWintunIdentity {
    luid:u64,ifindex:u32,quiesced:bool,
}
#[derive(Default)]
struct Registry {
    generation:u32,
    entries:BTreeMap<u64,Arc<Mutex<Entry>>>,
    game_groups:BTreeMap<u64,Arc<Mutex<game::WinGameGroup>>>,
}
static REGISTRY:OnceLock<Mutex<Registry>>=OnceLock::new();
fn registry()->&'static Mutex<Registry>{
    REGISTRY.get_or_init(||Mutex::new(Registry{generation:1,entries:BTreeMap::new(),game_groups:BTreeMap::new()}))
}
fn allocate(r:&mut Registry, cold:&[u8],command:&[u8],server:bool)->Result<u64,i32>{
    if r.entries.len()>=MAX_SESSIONS{return Err(FULL)}
    let handoff=PrivateGoV4Handoff::decode(command).map_err(|_|INVALID)?;
    // Feature7 is admitted only by explicit Rust FEC2 test-channel build.
    // This is a cryptographic lane candidate, never a WFP/OS Applied grant.
    if handoff.negotiated_features!=3 &&
       !(cfg!(feature="fec2_product_record") && handoff.negotiated_features==7){
        return Err(INVALID)
    }
    let parsed=UntrustedColdV4::parse(cold).map_err(|_|INVALID)?;
    if parsed.identity().server!=server{return Err(INVALID)}
    let identity=parsed.identity();
    let generation=r.generation;
    if generation==0{return Err(FULL)}
    let next=generation.checked_add(1).ok_or(FULL)?;
    let handle=(u64::from(generation)<<32)|HANDLE_KIND;
    if r.entries.contains_key(&handle){return Err(FULL)}
    let owner=handoff.prepare_scoped_owner_for_side(
        &parsed,generation,handle,server).map_err(|_|INVALID)?;
    // Normal/off M2 stores genuine M1 FrozenRecord slabs over the 300ms
    // each-direction + reverse-feedback flight. 10Mb/s * 0.6s / ~1280B
    // requires ~586 immutable in-flight records, not a 48-slot smoke pool.
    // This is only safe after the authenticated M2 receipt+global repair
    // actor is bound; no public bit is promoted, and all memory is bounded.
    // Normal/off negotiated inside ORIGINAL protected Go TLS. A 600ms
    // RTT at 10Mbps and 661B mean-symbol needs ~1135 immutable in-flight
    // M1 records. Linux v3 detaches only sampled repair ciphertext; M1
    // retains the proven bounded 2048 slots/5MB (Arena hard cap 8192).
    let normal=handoff.negotiated_features==3;
    let slots=if normal||handoff.negotiated_features==7{2048}else{64};
    let bytes=if normal||handoff.negotiated_features==7{5_000_000}else{3_000_000};
    let arena=Arena::new(generation,slots,2048,64,bytes)
        .map_err(|_|FULL)?;
    let rx_limit=if server{parsed.identity().server_limit}
        else{parsed.identity().client_limit};
    let record_wire_limit=usize::from(if server{
        parsed.identity().client_limit
    }else{parsed.identity().server_limit});
    r.generation=next;
    r.entries.insert(handle,Arc::new(Mutex::new(Entry{
        generation,phase:PH_PREPARED,role_server:server,
        rx_boundary:handoff.rx_boundary,
        rx_unwrapped_high:u64::from(handoff.rx_boundary),
        limit:rx_limit,count:0,bytes:0,
        owner,arena,tx_scratch:Vec::with_capacity(8),rx_scratch:Vec::with_capacity(8),
        authenticated_kind1:VecDeque::with_capacity(MAX_AUTHENTICATED_KIND1),m2:None,
        authenticated_epoch:identity.logical_epoch,
        peer_mss:handoff.peer_mss,
        peer_mss_advertised:handoff.peer_mss_advertised,
        record_wire_limit,path_mtu:0,device:None,
        feature7:handoff.negotiated_features==7,
        #[cfg(feature="fec2_product_record")]
        fec2_tx:None,
        #[cfg(feature="fec2_product_record")]
        auto_actor:None,
        game_cold:if handoff.negotiated_features==7{Some(parsed)}else{None},
        game_group:None,
        #[cfg(feature="fec2_product_record")]
        fec2_rx:None,
    })));
    Ok(handle)
}
fn stage(r:&mut Registry,h:u64,seq:u32,bytes:&[u8])->i32{
    let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    if e.phase!=PH_PREPARED{return BAD_STAGE}
    let len=bytes.len();
    let delta=seq.wrapping_sub(e.rx_boundary);
    let max=u32::from(e.limit).saturating_mul(MAX_EARLY);
    if len==0||len>usize::from(e.limit)||e.count>=MAX_EARLY
        ||e.bytes.saturating_add(len as u32)>max
        ||delta>=max||delta.saturating_add(len as u32)>max{return INVALID}
    let Ok(mut slab)=e.arena.allocate()else{return FULL};
    slab.writable()[..len].copy_from_slice(bytes);
    let absolute=u64::from(e.rx_boundary)+u64::from(delta);
    match e.owner.offer_early(slab,0..len,absolute,MonoNs(0)){
        Ok(EarlyAccepted::Staged)=>{
            e.count+=1;
            e.bytes+=len as u32;
            OK
        }
        _=>INVALID
    }
}
fn commit(r:&mut Registry,h:u64,count:u32,total:u32,tx_boundary:u32)->i32{
    let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    if e.phase!=PH_PREPARED{return BAD_STAGE}
    if count!=e.count||total!=e.bytes||count>MAX_EARLY{return INVALID}
    // Only original protected reply / Detach owns the actual SenderNext.
    if e.owner.commit_after_detach(tx_boundary).is_err(){return BAD_STAGE}
    e.phase=PH_ACTIVE;
    OK
}
fn bind_wintun(r:&mut Registry,h:u64,epoch:[u8;16],luid:u64,ifindex:u32)->i32{
    if luid==0||ifindex==0||epoch==[0;16]{return INVALID}
    let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE||e.device.is_some(){return BAD_STAGE}
    if epoch!=e.authenticated_epoch{return INVALID}
    e.device=Some(ScopedWindowsWintunIdentity{luid,ifindex,quiesced:false});
    OK
}
// Control plane only: Go verified this CURRENT Win32 Wintun and reads OS MTU.
fn set_path_mtu(r:&mut Registry,h:u64,epoch:[u8;16],luid:u64,
    ifindex:u32,mtu:u16)->Result<u32,i32>{
    if !(576..=2048).contains(&mtu){return Err(INVALID)}
    let lane=r.entries.get(&h).ok_or(UNKNOWN)?;
    let mut e=lane.lock().map_err(|_|BAD_STAGE)?;
    if e.phase!=PH_ACTIVE||e.authenticated_epoch!=epoch||
        !e.device.is_some_and(|d|!d.quiesced&&d.luid==luid&&d.ifindex==ifindex)||
        e.path_mtu!=0 {return Err(BAD_STAGE)}
    e.path_mtu=mtu;
    // Feature7 must reserve enough room for BOTH canonical FEC2
    // 10B source and 12B+2B protected-symbol repair, never return the
    // larger Normal/off packet ceiling and fail in the live seal path.
    let business=normal_off_windows_budget(&e).ok().and_then(|b|
        if e.feature7 {
            b.record_payload_mtu.checked_sub(wbd_codec::fec_v2::RECORD_RESERVATION)
        }else{Some(b.single_business_payload_mtu)}
    );
    match business {
        Some(n) if n>=20=>Ok(n as u32),
        _=>{e.path_mtu=0;Err(INVALID)},
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v4_bind_real_path_mtu(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
    mtu:u32,out:*mut u32,
)->i32{
    if out.is_null()||mtu>2048{return INVALID}
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    let Ok(mut registry)=registry().lock()else{return BAD_STAGE};
    match set_path_mtu(&mut registry,h,exact,luid,ifindex,mtu as u16){
        Ok(bound)=>{unsafe{out.write(bound)};OK},
        Err(e)=>e,
    }
}
fn quiesce_wintun(r:&mut Registry,h:u64,epoch:[u8;16],luid:u64,ifindex:u32)->i32{
    let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    if e.phase!=PH_ACTIVE{return BAD_STAGE}
    if epoch!=e.authenticated_epoch{return INVALID}
    let Some(device)=e.device.as_mut()else{return BAD_STAGE};
    if luid!=device.luid||ifindex!=device.ifindex{
        return INVALID
    }
    device.quiesced=true;
    OK
}
fn stop(r:&mut Registry,h:u64)->i32{
    let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    if e.phase==PH_STOPPED{return OK}
    if e.phase!=PH_ACTIVE&&e.phase!=PH_STOPPING{return BAD_STAGE}
    if e.game_group.is_some(){return STOP_INCOMPLETE}
    // Keep authenticated crypto owner alive if M4's current Wintun hold
    // has not ended its packet workers and completed the exact close fence.
    if e.device.is_some_and(|d|!d.quiesced){return STOP_INCOMPLETE}
    e.phase=PH_STOPPING;
    if let Some(m)=e.m2.take(){
        // One sparse joined Stop receipt exposes causal M2 state. No
        // per-packet timers/logging, no dump of keys/PN/ciphertext.
        let d=m.shadow.diagnostic_snapshot();
        eprintln!("WBD_WINDOWS_NATIVE_M2_OPPORTUNITY_STOP authenticated_reverse_reports={} repair_polls={} shadow_outstanding={} candidate_first={} expired_first={} acked_first={} repair_accepted={} repair_abandoned={} preflight_stale={} quota_rejected={} queued={} joined=true",
            m.reverse_authenticated_receipts,m.repair_polls,
            m.shadow.outstanding(),d.candidate_first,d.expired_attempt0,
            d.acked_attempt0,d.repair_accepted_retired,
            d.repair_abandoned_retired,m.repair_preflight_stale,
            m.repair_quota_rejected,m.ready_repairs.len());
        // Return original M1 frozen clones and retire the exact global
        // direction before original owner retirement. No late kernel sender.
        let Ok(mut global)=m2_global().lock()else{return STOP_INCOMPLETE};
        if global.retire_tunnel(m.direction.tunnel,m2_clock()).is_err(){
            return STOP_INCOMPLETE
        }
        drop(m);
    }
    let Ok(retired)=e.owner.stop()else{return STOP_INCOMPLETE};
    if !retired.ready.batch_handles_released(){return STOP_INCOMPLETE}
    #[cfg(feature="fec2_product_record")]
    {e.auto_actor.take();}
    #[cfg(feature="fec2_product_record")]
    if let Some(mut tx)=e.fec2_tx.take(){tx.stop()}
    #[cfg(feature="fec2_product_record")]
    if let Some(mut rx)=e.fec2_rx.take(){rx.stop()}
    // This STOP receipt covers Rust owner loans alone, never claims native
    // Windows WFP/TUN/route Stop; the product gate is permanently false.
    e.authenticated_kind1.clear();
    e.phase=PH_STOPPED;
    OK
}
fn abort(r:&mut Registry,h:u64)->i32{
    let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
    let Ok(e)=lane.lock()else{return BAD_STAGE};
    // A half-prepared owner holds no published DATA or native device lease.
    // A failed original protected TLS/transition must discard this generation
    // rather than ever making a forged Detach/Stop look successful.
    if e.phase!=PH_PREPARED{return BAD_STAGE}
    drop(e);
    r.entries.remove(&h);
    OK
}
fn release(r:&mut Registry,h:u64)->i32{
    let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
    let Ok(e)=lane.lock()else{return BAD_STAGE};
    if e.phase!=PH_STOPPED{return BAD_STAGE}
    drop(e);
    r.entries.remove(&h);
    OK
}
#[repr(C)]
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub struct WbdOriginalWindowsOwnerStateV1 {
    pub abi_version:u32,
    pub struct_size:u32,
    pub generation:u32,
    pub phase:u32,
    pub role_server:u32,
    pub product_applied:u32,
    pub kernel_loans_drained:u32,
    pub reserved:u32,
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_owner_v1_query(
    out:*mut WbdOriginalWindowsOwnerStateV1,out_size:u32)->i32{
    if out.is_null()||out_size!=std::mem::size_of::<WbdOriginalWindowsOwnerStateV1>() as u32{
        return INVALID
    }
    unsafe{out.write(WbdOriginalWindowsOwnerStateV1{
        abi_version:ABI_V1,struct_size:out_size,generation:0,phase:0,
        role_server:0,product_applied:PRODUCT_APPLIED,
        kernel_loans_drained:0,reserved:0
    })}
    OK
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v1_prepare(
    cold:*const u8,cold_len:usize,command:*const u8,command_len:usize,
    server:u32,out:*mut u64,
)->i32{
    if cold.is_null()||command.is_null()||out.is_null()
        ||cold_len!=COLD_V4_LEN||command_len!=HANDOFF_V1_LEN||server>1{return INVALID}
    // SAFETY: restricted developer FFI requires caller-owned contiguous
    // buffers of exactly these checked fixed lengths, valid for this call.
    let c=unsafe{std::slice::from_raw_parts(cold,cold_len)};
    let cmd=unsafe{std::slice::from_raw_parts(command,command_len)};
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    match allocate(&mut r,c,cmd,server==1){
        Ok(h)=>{unsafe{out.write(h)};OK},Err(e)=>e
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v1_stage(
    h:u64,seq:u32,data:*const u8,len:usize,
)->i32{
    if data.is_null()||len==0||len>2048{return INVALID}
    let bytes=unsafe{std::slice::from_raw_parts(data,len)};
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    stage(&mut r,h,seq,bytes)
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_owner_v1_abort(h:u64)->i32{
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    abort(&mut r,h)
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_owner_v1_commit(
    h:u64,staged_count:u32,staged_bytes:u32,exact_go_sender_next:u32,
)->i32{
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    commit(&mut r,h,staged_count,staged_bytes,exact_go_sender_next)
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_owner_v1_state(
    h:u64,out:*mut WbdOriginalWindowsOwnerStateV1,out_size:u32,
)->i32{
    if out.is_null()||out_size!=std::mem::size_of::<WbdOriginalWindowsOwnerStateV1>() as u32{
        return INVALID
    }
    let Ok(r)=registry().lock()else{return BAD_STAGE};
    let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
    let Ok(e)=lane.lock()else{return BAD_STAGE};
    unsafe{out.write(WbdOriginalWindowsOwnerStateV1{
        abi_version:ABI_V1,struct_size:out_size,generation:e.generation,
        phase:e.phase,role_server:u32::from(e.role_server),
        product_applied:PRODUCT_APPLIED,
        kernel_loans_drained:u32::from(e.phase==PH_STOPPED),reserved:0
    })}
    OK
}
// All v2 device calls are bounded, fixed-size and private to SAME-PROCESS
// original-Go post-credential callback. A token/record is not proof of WFP,
// real OS applied network, packet TX or M4 Stop; product_applied stays zero.
#[repr(C)]
#[derive(Clone,Copy)]
pub struct WbdWindowsDeviceFenceV2{
    pub abi_version:u32,
    pub struct_size:u32,
    pub generation:u32,
    pub bound:u32,
    pub quiesced:u32,
    pub product_applied:u32,
    pub ifindex:u32,
    pub reserved:u32,
    pub luid:u64,
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v2_bind_wintun(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
)->i32{
    if epoch.is_null()||epoch_len!=16{return INVALID}
    let mut exact=[0u8;16];
    exact.copy_from_slice(unsafe{std::slice::from_raw_parts(epoch,16)});
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    bind_wintun(&mut r,h,exact,luid,ifindex)
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v2_quiesce_wintun(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
)->i32{
    if epoch.is_null()||epoch_len!=16{return INVALID}
    let mut exact=[0u8;16];
    exact.copy_from_slice(unsafe{std::slice::from_raw_parts(epoch,16)});
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    quiesce_wintun(&mut r,h,exact,luid,ifindex)
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_owner_v2_device_state(
    h:u64,out:*mut WbdWindowsDeviceFenceV2,out_size:u32,
)->i32{
    if out.is_null()||out_size!=std::mem::size_of::<WbdWindowsDeviceFenceV2>() as u32{
        return INVALID
    }
    let Ok(r)=registry().lock()else{return BAD_STAGE};
    let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
    let Ok(e)=lane.lock()else{return BAD_STAGE};
    let (bound,quiesced,ifindex,luid)=match e.device{
        Some(d)=>(1,u32::from(d.quiesced),d.ifindex,d.luid),
        None=>(0,0,0,0)
    };
    unsafe{out.write(WbdWindowsDeviceFenceV2{
        abi_version:2,struct_size:out_size,generation:e.generation,
        bound,quiesced,product_applied:PRODUCT_APPLIED,ifindex,reserved:0,luid
    })}
    OK
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_owner_v1_stop(h:u64)->i32{
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    stop(&mut r,h)
}
#[no_mangle]
pub extern "C" fn wbd_m0_win_owner_v1_release(h:u64)->i32{
    let Ok(mut r)=registry().lock()else{return BAD_STAGE};
    release(&mut r,h)
}

// This read-only ABI binds public Windows mode claims to the actual
// END-TO-END native owner contract, not to isolated Rust codecs or a
// half-wired Windows CLI mode selector. Bits: Normal=1, Fixed=2,
// Auto=4, Game2=8, Game4=16. Source-locked Windows/Linux Normal/off
// kernel UDP/TCP and owned Stop have positive product evidence;
// Fixed/Auto/Game lack their independent public mode-positive proof.
// Reuse Linux shared architecture before promoting another bit.
// Never use an advertised mode mask as an FEC2 feature/test switch.
#[repr(C)]
pub struct WbdWindowsV4ModeCapabilities {
    pub version:u32,
    pub size:u32,
    pub supported_modes:u32,
    pub authenticated_lanes:u32,
    pub reserved:u32,
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v4_mode_capabilities(
    out:*mut WbdWindowsV4ModeCapabilities,size:u32,
)->i32{
    if out.is_null()||size!=std::mem::size_of::<WbdWindowsV4ModeCapabilities>() as u32{
        return INVALID
    }
    unsafe{out.write(WbdWindowsV4ModeCapabilities{
        // Isolated Draft full-wiring CANDIDATE: exact source functional run
        // must qualify all five original-Go modes before public release.
        version:4,size,supported_modes:31,authenticated_lanes:4,reserved:0,
    })};
    OK
}
// V3 is deliberately a private RECORD boundary, not a Windows OS Applied
// decision. The source of the real credentials is the existing original-Go
// protected callback that issued this handle, never these C bytes alone.
// Real OS pinned Wintun MTU + original Go TLS MSS, shared FrameBudget.
// No arbitrary conservative 576/512 cap on the live packet path.
fn normal_off_windows_budget(e:&Entry)->Result<FrameBudget,i32>{
    if e.path_mtu<576{return Err(INVALID)}
    let mtu=usize::from(e.path_mtu);
    FrameBudget::derive(FrameBudgetInput{
        connection_mtu:mtu,local_packet_mtu:mtu,
        ipv4_header_len:20,tcp_header_len:20,
        peer_mss:if e.peer_mss_advertised {Some(e.peer_mss)} else {None},
        record_wire_limit:e.record_wire_limit,
        fec:FecReservation::FixedOff,game:false,
    }).map_err(|_|INVALID)
}
fn v3_ready(e:&Entry,epoch:[u8;16],luid:u64,ifindex:u32)->bool{
    e.phase==PH_ACTIVE && e.authenticated_epoch==epoch &&
    e.device.is_some_and(|d|!d.quiesced && d.luid==luid && d.ifindex==ifindex)
}
fn v3_seal_entry(e:&mut Entry,epoch:[u8;16],luid:u64,
    ifindex:u32,ipv4:&[u8],out:&mut [u8]
)->Result<(usize,u32,u64),i32>{
    if !v3_ready(e,epoch,luid,ifindex)||ipv4.len()<20||
        ipv4[0]>>4!=4 || ipv4.len()>2048 || out.len()<ipv4.len()+FIXED_WIRE_OVERHEAD{
        return Err(INVALID)
    }
    let budget=normal_off_windows_budget(e)?;
    if ipv4.len()>budget.single_business_payload_mtu ||
        ipv4[0]&15<5{return Err(INVALID)}
    let mut slab=e.arena.allocate().map_err(|_|FULL)?;
    slab.writable()[14..14+ipv4.len()].copy_from_slice(ipv4);
    // The same original M1 TX owner also seals M2 kind1 controls at
    // m2_clock(): stale zero time after a genuine control deadline can
    // reverse its clock and reject an otherwise valid first DATA packet.
    let now=m2_clock();
    let (pn,seq,used)=e.owner.seal_normal_off_one(
        slab,ipv4.len(),budget,0,now).map_err(|_|BAD_STAGE)?;
    // Copy only the SAME M1 immutable FrozenRecord into the caller's bounded
    // carrier buffer while its genuine LoanBatch remains borrowed; recycle
    // generation-scoped loans on *every* path, including rejected batches.
    let tx_storage=std::mem::take(&mut e.tx_scratch);
    let batch=match e.owner.drain_tx(now,tx_storage){
        Ok(batch)=>batch,
        Err((_,storage))=>{e.tx_scratch=storage;return Err(BAD_STAGE)}
    };
    let accepted=(||{
        let ready=e.owner.checked_tx_ready(&batch).map_err(|_|BAD_STAGE)?;
        if ready.len()!=1 || ready[0].record.bytes().len()!=used {
            return Err(BAD_STAGE)
        }
        if let Some(m)=e.m2.as_mut(){
            let original=&ready[0].record;
            if original.metadata().pn!=RecordPn(pn) ||
                original.metadata().seq.0 as u32!=seq ||
                m.pending.insert(RecordPn(pn),original.clone()).is_some() {
                return Err(BAD_STAGE)
            }
        }
        out[..used].copy_from_slice(ready[0].record.bytes());
        Ok((used,seq,pn))
    })();
    e.tx_scratch=batch.recycle();
    accepted
}
// One bounded zero-wait staged SOURCE batch (not a kernel submission).
// Native Go captures a maximum of four actually ready Wintun frames and
// holds its real M4 lease while one Rust M1 Entry lock seals each original
// contiguous PN/SEQ. No cipher, packet receipt or fresh F is forged here.
#[repr(C)]
#[derive(Clone,Copy)]
pub struct WbdWindowsOriginalSourceInput {
    pub length:u32,pub reserved:u32,pub ipv4:[u8;2048],
}
#[repr(C)]
#[derive(Clone,Copy)]
pub struct WbdWindowsOriginalSourceOutput {
    pub used:u32,pub seq:u32,pub pn:u64,pub wire:[u8;2048],
}
const MAX_WINDOWS_SOURCE_BATCH:usize=4;
fn original_source_batch_entry(
    e:&mut Entry,epoch:[u8;16],luid:u64,ifindex:u32,
    rows:&[WbdWindowsOriginalSourceInput],
    outputs:&mut [WbdWindowsOriginalSourceOutput],
)->(i32,u32){
    if !v3_ready(e,epoch,luid,ifindex)||
        rows.is_empty()||rows.len()>MAX_WINDOWS_SOURCE_BATCH||
        rows.len()!=outputs.len()||e.m2.is_none(){
        return (BAD_STAGE,0)
    }
    let budget=match normal_off_windows_budget(e){
        Ok(v)=>v,Err(code)=>return (code,0),
    };
    // Preflight ALL original IPv4 bounds and the expected 31/45-byte
    // wire budget before spending even one Rust AEAD nonce/TCP serial.
    let max=if e.feature7{
        #[cfg(feature="fec2_product_record")]
        {if e.fec2_tx.is_none(){return (BAD_STAGE,0)};}
        #[cfg(not(feature="fec2_product_record"))]
        {return (BAD_STAGE,0);}
        budget.record_payload_mtu.saturating_sub(14)
    }else{budget.single_business_payload_mtu};
    for row in rows{
        let n=row.length as usize;
        if row.reserved!=0||n<20||n>max||n>2048||
           row.ipv4[0]>>4!=4||row.ipv4[0]&15<5||
           n.checked_add(if e.feature7{45}else{31})
             .is_none_or(|wire|wire>2048){
            return (INVALID,0)
        }
    }
    let mut produced=0u32;
    for (row,out) in rows.iter().zip(outputs.iter_mut()){
        let ipv4=&row.ipv4[..row.length as usize];
        let result=if e.feature7{
            #[cfg(feature="fec2_product_record")]
            {fec2::stage_fixed_source_entry(e,epoch,luid,ifindex,
                ipv4,&mut out.wire)}
            #[cfg(not(feature="fec2_product_record"))]
            {Err(BAD_STAGE)}
        }else{
            v3_seal_entry(e,epoch,luid,ifindex,ipv4,&mut out.wire)
        };
        match result{
            Ok((used,seq,pn))=>{
                out.used=used as u32;
                out.seq=seq;
                out.pn=pn;
                produced+=1;
            },
            // Partial post-seal failure is terminal. Go cannot call this
            // C ABI again for the same Wintun source, and must Stop the
            // whole epoch without inventing a compensating TCP sequence.
            Err(code)=>return (code,produced),
        }
    }
    (OK,produced)
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v11_stage_original_sources_batch(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
    inputs:*const WbdWindowsOriginalSourceInput,count:u32,
    outputs:*mut WbdWindowsOriginalSourceOutput,capacity:u32,
    produced:*mut u32,
)->i32{
    if inputs.is_null()||outputs.is_null()||produced.is_null()||
       count==0||count as usize>MAX_WINDOWS_SOURCE_BATCH||
       capacity!=count||
       (inputs as usize)%std::mem::align_of::<WbdWindowsOriginalSourceInput>()!=0||
       (outputs as usize)%std::mem::align_of::<WbdWindowsOriginalSourceOutput>()!=0{
        return INVALID
    }
    // No mutable alias of caller's encrypted output and immutable source.
    let in_start=inputs as usize;
    let out_start=outputs as usize;
    let in_end=in_start.checked_add(
        count as usize*std::mem::size_of::<WbdWindowsOriginalSourceInput>());
    let out_end=out_start.checked_add(
        count as usize*std::mem::size_of::<WbdWindowsOriginalSourceOutput>());
    if in_end.is_none_or(|end|out_start<end&&in_start<out_end.unwrap_or(0))||
       out_end.is_none(){
        return INVALID
    }
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    let input=unsafe{std::slice::from_raw_parts(inputs,count as usize)};
    let output=unsafe{std::slice::from_raw_parts_mut(outputs,count as usize)};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    let (status,n)=original_source_batch_entry(
        &mut e,exact,luid,ifindex,input,output);
    unsafe{produced.write(n)}
    status
}
// Unfold exact captured TCP serial bytes against this original-Go-verified
// owner only. No arbitrary wrapped seq can claim a different generation.
fn m0_tcp_unwrap(e:&Entry,seq:u32,len:usize)->Result<u64,i32>{
    let anchor=e.rx_unwrapped_high;
    let base=(anchor&!0xffff_ffff)|u64::from(seq);
    let next=base.saturating_add(1u64<<32);
    let earlier=base.checked_sub(1u64<<32);
    let distance=|x:u64|anchor.max(x)-anchor.min(x);
    let mut choice=base;
    if distance(next)<distance(choice){choice=next}
    if let Some(x)=earlier{
        if distance(x)<distance(choice){choice=x}
    }
    // Only the authentic M3 AEAD/unique PN decision may deliver a future
    // record beyond Go's 128KiB *presentation* ACK ledger. Bound the
    // unauthenticated serial input to 4MiB; do NOT advance Go TCP ACK
    // across a hole or bypass Rust replay validation.
    if distance(choice)>4*1024*1024 ||
        choice<u64::from(e.rx_boundary) ||
        choice.checked_add(len as u64).is_none(){
        return Err(INVALID)
    }
    Ok(choice)
}
fn v5_open_record_entry(e:&mut Entry,epoch:[u8;16],luid:u64,
    ifindex:u32,seq:u32,wire:&[u8],out:&mut [u8]
)->Result<(usize,u32,u64),i32>{
    if !v3_ready(e,epoch,luid,ifindex)||
        wire.len()<=FIXED_WIRE_OVERHEAD || wire.len()>2048 ||
        out.len()<wire.len(){return Err(INVALID)}
    let mut slab=e.arena.allocate().map_err(|_|FULL)?;
    slab.writable()[..wire.len()].copy_from_slice(wire);
    let unfolded=m0_tcp_unwrap(e,seq,wire.len())?;
    let now=m2_clock();
    e.owner.offer_after_active(slab,0..wire.len(),unfolded,now)
        .map_err(|_|INVALID)?;
    let mut len=0usize;
    let mut valid=false;
    let mut opened_data_pn=None;
    let mut opened_kind1=None;
    let rx_storage=std::mem::take(&mut e.rx_scratch);
    let draining=e.owner.drain_windows_authenticated_kind1(
        now,rx_storage,|pn,link|{
            // No unauthenticated DATA, replay, HEALTH or fragmented LINK
            // can reach a Windows kernel packet sink from this v3 boundary.
            // Fragmentation will be installed with the complete M3 table.
            if matches!(inspect_link(link,wire.len(),LinkMode::FixedOff),
                Ok(LinkView::Ordinary(_))) &&
                link.len()>=20 && link[0]>>4==4 &&
                link[0]&15>=5 && link.len()<=out.len(){
                out[..link.len()].copy_from_slice(link);
                len=link.len();valid=true;opened_data_pn=Some(pn);
            }
        },|pn,receipt|{opened_kind1=Some((pn,receipt))});
    let (storage,report)=match draining{
        Ok(v)=>v,
        Err((_,scratch))=>{e.rx_scratch=scratch;return Err(BAD_STAGE)}
    };
    e.rx_scratch=storage;
    if valid && report.link_ready==1 && report.rejected==0
        && report.control_ready==0 {
        let unique_pn=opened_data_pn.ok_or(INVALID)?;
        // Only the same owner-replay-checked M3 successful DATA opens
        // activate RxFeedbackState. Control kind1 cannot ACK itself.
        if let Some(m)=e.m2.as_mut(){
            m.feedback.on_authenticated_data(RecordPn(unique_pn),m2_clock());
            m.health.on_authenticated_business(m2_clock().0);
        }
        e.rx_unwrapped_high=e.rx_unwrapped_high.max(unfolded+wire.len() as u64);
        Ok((len,1,unique_pn))
    }
    // Only after the SAME original protected M3 AEAD and replay admission
    // can this typed kind1 enter the bounded staging lane. It does not yet
    // authorize shadow retirement or Go TCP carrier receipt.
    else if report.link_ready==0&&report.control_ready==1&&report.rejected==0 {
        let Some((pn,control))=opened_kind1 else{return Err(INVALID)};
        if e.m2.is_some(){
            // Health-only is verified liveness, not a frozen DATA receipt.
            m2_authenticated_kind1_entry(e,pn,&control)?;
        }else if let Some(receipt)=control.receipt{
            if e.authenticated_kind1.len()>=MAX_AUTHENTICATED_KIND1{return Err(FULL)}
            e.authenticated_kind1.push_back((pn,receipt));
        }
        e.rx_unwrapped_high=e.rx_unwrapped_high.max(unfolded+wire.len() as u64);
        Ok((0,2,pn)) // kind1 is not an IPv4 packet or M2 shadow-release grant
    } else {Err(INVALID)}
}
// Existing v3 semantics remain data-only: even authenticated control may not
// be reinterpreted as application IPv4 when a legacy caller uses this ABI.
fn v3_open_entry(e:&mut Entry,epoch:[u8;16],luid:u64,
    ifindex:u32,seq:u32,wire:&[u8],out:&mut [u8]
)->Result<usize,i32>{
    let (size,kind,_pn)=v5_open_record_entry(e,epoch,luid,ifindex,seq,wire,out)?;
    if kind==1 {Ok(size)} else {Err(INVALID)}
}
// Test helper; each production FFI clones a session Arc while the
// registry mutex is briefly held, then releases it before AEAD and loans.
fn v3_seal_one(r:&Registry,h:u64,epoch:[u8;16],luid:u64,
    ifindex:u32,ipv4:&[u8],out:&mut [u8],
)->Result<(usize,u32,u64),i32>{
    let lane=r.entries.get(&h).ok_or(UNKNOWN)?;
    let mut e=lane.lock().map_err(|_|BAD_STAGE)?;
    v3_seal_entry(&mut e,epoch,luid,ifindex,ipv4,out)
}
fn v3_open_one(r:&Registry,h:u64,epoch:[u8;16],luid:u64,
    ifindex:u32,seq:u32,wire:&[u8],out:&mut [u8],
)->Result<usize,i32>{
    let lane=r.entries.get(&h).ok_or(UNKNOWN)?;
    let mut e=lane.lock().map_err(|_|BAD_STAGE)?;
    v3_open_entry(&mut e,epoch,luid,ifindex,seq,wire,out)
}
fn v5_open_record_one(r:&Registry,h:u64,epoch:[u8;16],luid:u64,
    ifindex:u32,seq:u32,wire:&[u8],out:&mut [u8]
)->Result<(usize,u32,u64),i32>{
    let lane=r.entries.get(&h).ok_or(UNKNOWN)?;
    let mut e=lane.lock().map_err(|_|BAD_STAGE)?;
    v5_open_record_entry(&mut e,epoch,luid,ifindex,seq,wire,out)
}
fn v3_epoch(ptr:*const u8,len:usize)->Option<[u8;16]>{
    if ptr.is_null()||len!=16{return None}
    let mut epoch=[0;16];
    epoch.copy_from_slice(unsafe{std::slice::from_raw_parts(ptr,16)});
    Some(epoch)
}
// A transport-layer Go driver still must prove the native Wintun OS
// ownership/route readback before using this wire on an actual socket.
// Epoch/luid/index are checked AGAINST an already bound Rust owner; passing
// them as params cannot bind or grant an unauthorized device.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v3_seal_normal_off(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
    ipv4:*const u8,ipv4_len:usize,out:*mut u8,capacity:usize,
    used:*mut usize,seq:*mut u32,pn:*mut u64,
)->i32{
    if ipv4.is_null()||out.is_null()||used.is_null()||seq.is_null()||
        pn.is_null()||ipv4_len<20||ipv4_len>2048||
        capacity<ipv4_len+FIXED_WIRE_OVERHEAD||capacity>65535{return INVALID}
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    // No mutable-aliasing FFI: input and output must not overlap.
    let src_start=ipv4 as usize;let dst_start=out as usize;
    if src_start.checked_add(ipv4_len).is_none_or(|end|
        dst_start<end && src_start<dst_start.saturating_add(capacity)){return INVALID}
    let data=unsafe{std::slice::from_raw_parts(ipv4,ipv4_len)};
    let dst=unsafe{std::slice::from_raw_parts_mut(out,capacity)};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    match v3_seal_entry(&mut e,exact,luid,ifindex,data,dst){
        Ok((n,s,p))=>{
            unsafe{used.write(n);seq.write(s);pn.write(p)};OK
        },
        Err(e)=>e,
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v3_open_normal_off(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
    seq:u32,wire:*const u8,wire_len:usize,out:*mut u8,capacity:usize,
    used:*mut usize,
)->i32{
    if wire.is_null()||out.is_null()||used.is_null()||
        wire_len<=FIXED_WIRE_OVERHEAD||wire_len>2048||
        capacity<wire_len||capacity>65535{return INVALID}
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    let src_start=wire as usize;let dst_start=out as usize;
    if src_start.checked_add(wire_len).is_none_or(|end|
        dst_start<end && src_start<dst_start.saturating_add(capacity)){return INVALID}
    let data=unsafe{std::slice::from_raw_parts(wire,wire_len)};
    let dst=unsafe{std::slice::from_raw_parts_mut(out,capacity)};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    match v3_open_entry(&mut e,exact,luid,ifindex,seq,data,dst){
        Ok(n)=>{unsafe{used.write(n)};OK},Err(e)=>e,
    }
}


// One Rust-owned timer/repair turn. Caller must report its true Npcap
// outcome before the next poll or Stop. A zero used means no repair ready.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v6_next_frozen_repair(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
    out:*mut u8,capacity:usize,used:*mut usize,seq:*mut u32,pn:*mut u64,
)->i32{
    if out.is_null()||used.is_null()||seq.is_null()||pn.is_null()||
        capacity<51||capacity>65535{return INVALID}
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    let dst=unsafe{std::slice::from_raw_parts_mut(out,capacity)};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    match m2_next_repair_entry(&mut e,exact,luid,ifindex,dst){
        Ok(Some((n,s,p)))=>{unsafe{used.write(n);seq.write(s);pn.write(p)};OK},
        Ok(None)=>{unsafe{used.write(0);seq.write(0);pn.write(0)};OK},
        Err(err)=>err,
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v6_finish_frozen_repair(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
    pn:u64,npcap_sent:u32,outstanding:*mut u32
)->i32{
    if outstanding.is_null(){return INVALID}
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    match m2_complete_repair_entry(&mut e,exact,luid,ifindex,pn,npcap_sent){
        Ok(n)=>{unsafe{outstanding.write(n)};OK},
        Err(err)=>err
    }
}

#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v6_m2_outstanding(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
    out:*mut u32
)->i32{
    if out.is_null(){return INVALID}
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(e)=lane.lock()else{return BAD_STAGE};
    if !v3_ready(&e,exact,luid,ifindex){return INVALID}
    let Some(m)=e.m2.as_ref()else{return BAD_STAGE};
    unsafe{out.write(m.shadow.outstanding() as u32)};OK
}

// Source-locked runtime-effective M2 bounds, not CLI-requested defaults or
// a claim of product/OS Applied. C ABI cannot expose mutable Rust owners.
#[repr(C)]
#[derive(Clone,Copy,Debug)]
pub struct WbdWindowsM2Effective {
    pub version:u32,pub size:u32,
    pub path_mtu:u32,pub business_ipv4_mtu:u32,
    pub shadow_limit:u32,pub feedback_page_limit:u32,
    pub mature_live_limit:u32,pub v3_enabled:u32,
    pub process_repair_hard_cap:u64,
    pub direction_epoch_limit:u64,
    pub direction_fresh_confirmed:u64,
    pub process_charged_repairs:u64,
    pub process_pending_bytes:u64,
}
fn m2_effective_entry(e:&Entry,epoch:[u8;16],luid:u64,ifindex:u32)
    ->Result<WbdWindowsM2Effective,i32>{
    if !v3_ready(e,epoch,luid,ifindex){return Err(INVALID)}
    let m=e.m2.as_ref().ok_or(BAD_STAGE)?;
    let budget=normal_off_windows_budget(e)?;
    let mtu=if e.feature7{
        budget.record_payload_mtu.saturating_sub(14)
    }else{budget.single_business_payload_mtu};
    if mtu<20||mtu>2048{return Err(INVALID)}
    let g=m2_global().lock().map_err(|_|BAD_STAGE)?;
    let dir=g.local_snapshot(m.direction).ok_or(BAD_STAGE)?;
    let process=g.snapshot();
    Ok(WbdWindowsM2Effective{
        version:1,size:std::mem::size_of::<WbdWindowsM2Effective>() as u32,
        path_mtu:u32::from(e.path_mtu),
        business_ipv4_mtu:mtu as u32,
        shadow_limit:m.shadow.policy_limits().1 as u32,
        feedback_page_limit:m.feedback.config().max_retained_pages as u32,
        mature_live_limit:{
            #[cfg(feature="fec2_product_record")]
            {m.mature.as_ref().map_or(0,|x|x.max_live_data() as u32)}
            #[cfg(not(feature="fec2_product_record"))]
            {0}
        },
        v3_enabled:u32::from(m.shadow.is_opportunistic_v3()),
        process_repair_hard_cap:process.hard_cap,
        direction_epoch_limit:dir.epoch_repair_limit,
        direction_fresh_confirmed:dir.fresh_confirmed_bytes,
        process_charged_repairs:process.charged_repairs,
        process_pending_bytes:process.pending_bytes as u64,
    })
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v9_m2_effective(
    h:u64,ep:*const u8,ep_len:usize,luid:u64,ifindex:u32,
    out:*mut WbdWindowsM2Effective,size:u32,
)->i32{
    if out.is_null()||size!=std::mem::size_of::<WbdWindowsM2Effective>() as u32{
        return INVALID
    }
    let Some(epoch)=v3_epoch(ep,ep_len)else{return INVALID};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(e)=lane.lock()else{return BAD_STAGE};
    match m2_effective_entry(&e,epoch,luid,ifindex){
        Ok(v)=>{unsafe{out.write(v)};OK},Err(code)=>code
    }
}
// V6 firstsend callback is valid only for the SAME activated, OS Wintun
// epoch. Every callback matches exact original frozen PN/SEQ/len. Status 1
// means actual Npcap pcap_sendpacket returned success, not remote Applied.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v6_arm_original_m2(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32
)->i32{
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    match m2_arm_entry(&mut e,exact,luid,ifindex){
        Ok(())=>OK,Err(err)=>err
    }
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v6_report_npcap_firstsend(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
    pn:u64,seq:u32,wire_len:usize,sent:u32,outstanding:*mut u32
)->i32{
    if outstanding.is_null()||wire_len<FIXED_WIRE_OVERHEAD||wire_len>2048{
        return INVALID
    }
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    match m2_kernel_firstsend_entry(
        &mut e,exact,luid,ifindex,pn,seq,wire_len,sent
    ){
        Ok(n)=>{unsafe{outstanding.write(n)};OK},
        Err(err)=>err
    }
}

// Complete up to 32 already-accepted native firstsend outcomes under ONE
// original generation/Entry lock and one real TLS-bound Wintun lease.
// Every row is untrusted until matched to immutable pending Rust M1 PN/SEQ.
#[repr(C)]
#[derive(Clone,Copy)]
pub struct WbdWindowsM2FirstsendResult{
    pub pn:u64,pub seq:u32,pub wire_len:u32,pub outcome:u32,pub reserved:u32,
}
const MAX_WINDOWS_M2_COMPLETIONS:usize=32;
fn m2_kernel_firstsend_batch_entry(
    e:&mut Entry,epoch:[u8;16],luid:u64,ifindex:u32,
    rows:&[WbdWindowsM2FirstsendResult],
)->(i32,u32,u32){
    if !v3_ready(e,epoch,luid,ifindex)||
        rows.is_empty()||rows.len()>MAX_WINDOWS_M2_COMPLETIONS{
        return (INVALID,0,0)
    }
    let Some(m)=e.m2.as_ref()else{return (BAD_STAGE,0,0)};
    let mut unique=BTreeSet::new();
    let mut next=None;
    // Check every original immutable PN/SEQ/length and all consecutive
    // byte ranges BEFORE removing any pending M1 handle. On preflight
    // failure no staged record is lost, nor is any peer receipt forged.
    for row in rows{
        if row.reserved!=0||row.outcome>2||
            (row.wire_len as usize)<FIXED_WIRE_OVERHEAD||
            row.wire_len>2048||!unique.insert(row.pn)||
            next.is_some_and(|prior:u32|prior!=row.seq){return (INVALID,0,0)}
        let Some(original)=m.pending.get(&RecordPn(row.pn))else{
            return (INVALID,0,0)
        };
        if original.metadata().pn!=RecordPn(row.pn)||
            original.metadata().seq.0 as u32!=row.seq||
            original.bytes().len()!=row.wire_len as usize{
            return (INVALID,0,0)
        }
        next=Some(row.seq.wrapping_add(row.wire_len));
    }
    let mut settled=0u32;
    let mut outstanding=m.shadow.outstanding() as u32;
    for row in rows{
        // If a post-NPF internal owner failure occurs, report the exact
        // already-settled prefix and fail closed. Neither the remaining
        // accepted NPF rows nor the settled prefix may be blindly retried.
        match m2_kernel_firstsend_entry(e,epoch,luid,ifindex,row.pn,
            row.seq,row.wire_len as usize,row.outcome){
            Ok(left)=>{settled+=1;outstanding=left},
            Err(code)=>return (code,settled,outstanding),
        }
    }
    (OK,settled,outstanding)
}
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v10_report_npcap_firstsend_batch(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
    rows:*const WbdWindowsM2FirstsendResult,count:u32,
    settled:*mut u32,outstanding:*mut u32,
)->i32{
    if rows.is_null()||settled.is_null()||outstanding.is_null()||
        count==0||count as usize>MAX_WINDOWS_M2_COMPLETIONS||
        (rows as usize)%std::mem::align_of::<WbdWindowsM2FirstsendResult>()!=0 {
        return INVALID
    }
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    let rows=unsafe{std::slice::from_raw_parts(rows,count as usize)};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    let (status,n,m)=m2_kernel_firstsend_batch_entry(
        &mut e,exact,luid,ifindex,rows);
    unsafe{settled.write(n);outstanding.write(m)}
    status
}
// Bounded C ABI only through the exact credential-checked Go native owner,
// current Wintun LUID/index and one original Rust M1/PN sender. No callback
// indicates remote delivery: success here means ciphertext was staged.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v7_reverse_m2_feedback_due(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
    out:*mut u8,capacity:usize,used:*mut usize,seq:*mut u32,pn:*mut u64
)->i32{
    if out.is_null()||used.is_null()||seq.is_null()||pn.is_null()||
        capacity<128||capacity>2048{return INVALID}
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    let dst=unsafe{std::slice::from_raw_parts_mut(out,capacity)};
    match m2_next_feedback_entry(&mut e,exact,luid,ifindex,dst){
        Ok(Some((n,s,p)))=>{unsafe{
            used.write(n);seq.write(s);pn.write(p);
        };OK},
        Ok(None)=>{unsafe{used.write(0);seq.write(0);pn.write(0)};OK},
        Err(err)=>err,
    }
}
// Commit exactly the NPF actual pcap_sendpacket result. Not a peer ACK.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v7_reverse_m2_feedback_result(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
    pn:u64,npcap_sent:u32
)->i32{
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    match m2_finish_feedback_entry(&mut e,exact,luid,ifindex,pn,npcap_sent){
        Ok(())=>OK,Err(err)=>err,
    }
}
// V5 returns TYPE only after the SAME real original M3 AEAD + unique PN
// opener. Kind 1=verified business IPv4, 2=verified canonical M2 kind1;
// kind2 is STAGED in the Rust owner and cannot authorize shadow release
// until a separately scoped M2 recovery state consumes it.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_win_owner_v5_open_data_or_kind1(
    h:u64,epoch:*const u8,epoch_len:usize,luid:u64,ifindex:u32,
    seq:u32,wire:*const u8,wire_len:usize,out:*mut u8,capacity:usize,
    used:*mut usize,kind:*mut u32,pn:*mut u64,
)->i32{
    if wire.is_null()||out.is_null()||used.is_null()||kind.is_null()||
        pn.is_null()||wire_len<=FIXED_WIRE_OVERHEAD||wire_len>2048||
        capacity<wire_len||capacity>65535{return INVALID}
    let Some(exact)=v3_epoch(epoch,epoch_len)else{return INVALID};
    let src_start=wire as usize;let dst_start=out as usize;
    if src_start.checked_add(wire_len).is_none_or(|end|
        dst_start<end && src_start<dst_start.saturating_add(capacity)){return INVALID}
    let data=unsafe{std::slice::from_raw_parts(wire,wire_len)};
    let dst=unsafe{std::slice::from_raw_parts_mut(out,capacity)};
    let lane={
        let Ok(r)=registry().lock()else{return BAD_STAGE};
        let Some(lane)=r.entries.get(&h)else{return UNKNOWN};
        Arc::clone(lane)
    };
    let Ok(mut e)=lane.lock()else{return BAD_STAGE};
    match v5_open_record_entry(&mut e,exact,luid,ifindex,seq,data,dst){
        Ok((n,k,p)) if k==1||k==2=>{
            unsafe{used.write(n);kind.write(k);pn.write(p)};OK
        },
        Ok(_)=>INVALID,
        Err(err)=>err,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn cold(server:bool)->[u8;COLD_V4_LEN]{
        let mut a=[0;COLD_V4_LEN];
        a[..4].copy_from_slice(b"WBCO");
        a[4..6].copy_from_slice(&1u16.to_be_bytes());
        a[6..8].copy_from_slice(&(COLD_V4_LEN as u16).to_be_bytes());
        a[8]=u8::from(server);a[9]=1;a[10]=1;
        a[12..28].fill(1);a[28..44].fill(2);
        a[44..60].fill(3);a[60..62].copy_from_slice(&1400u16.to_be_bytes());
        a[62..64].copy_from_slice(&1400u16.to_be_bytes());
        a[64..96].fill(4);a[96..172].fill(5);a[172..].fill(6);
        a
    }
    fn cmd()->[u8;HANDOFF_V1_LEN]{
        let mut a=[0;HANDOFF_V1_LEN];
        a[..4].copy_from_slice(b"WBGH");
        a[4..6].copy_from_slice(&1u16.to_be_bytes());
        a[6..8].copy_from_slice(&(HANDOFF_V1_LEN as u16).to_be_bytes());
        a[8..12].copy_from_slice(&[10,25,0,2]);
        a[12..16].copy_from_slice(&[10,25,0,1]);
        a[16..18].copy_from_slice(&41001u16.to_be_bytes());
        a[18..20].copy_from_slice(&443u16.to_be_bytes());
        a[20..24].copy_from_slice(&500u32.to_be_bytes());
        a[24..26].copy_from_slice(&1360u16.to_be_bytes());
        a[26]=1;a
    }
    #[test]
    fn m0_windows_original_m1_2048_slots_and_m2_detached_shadow_contract(){
        // This is a REAL Windows-only original M1 ownership fixture. It is
        // never an OS/product or 10Mbps performance qualification.
        assert_eq!(MAX_M2_FROZEN,24_576,
            "original Npcap frozen-M2 limit must match Go admission");
        let mut r=Registry{generation:711,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let h=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        {
            let e=r.entries[&h].lock().unwrap();
            assert_eq!(e.arena.capacity(),2048,
                "Normal feature3 original Windows M1 slabs cannot regress");
            assert!(e.m2.is_none());
        }
        assert_eq!(commit(&mut r,h,0,0,500),OK);
        let epoch=[2u8;16];
        assert_eq!(bind_wintun(&mut r,h,epoch,91,19),OK);
        assert!(set_path_mtu(&mut r,h,epoch,91,19,1400).is_ok());
        {
            let mut e=r.entries[&h].lock().unwrap();
            assert!(m2_arm_entry(&mut e,epoch,91,19).is_ok());
            assert_eq!(e.arena.capacity(),2048);
            assert_eq!(e.m2.as_ref().unwrap().shadow.outstanding(),0);
        }
        assert_eq!(quiesce_wintun(&mut r,h,epoch,91,19),OK);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(release(&mut r,h),OK);
    }
    #[test]
    fn m0_windows_original_m2_effective_readback_is_actual_runtime_budget(){
        let mut r=Registry{generation:712,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let h=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        let ep=[2u8;16];
        assert_eq!(commit(&mut r,h,0,0,500),OK);
        assert_eq!(bind_wintun(&mut r,h,ep,93,21),OK);
        let bound=set_path_mtu(&mut r,h,ep,93,21,1400).unwrap();
        {
            let mut e=r.entries[&h].lock().unwrap();
            m2_arm_entry(&mut e,ep,93,21).unwrap();
            let actual=m2_effective_entry(&e,ep,93,21).unwrap();
            assert_eq!(actual.version,1);
            assert_eq!(actual.size,std::mem::size_of::<WbdWindowsM2Effective>() as u32);
            assert_eq!(actual.path_mtu,1400);
            assert_eq!(actual.business_ipv4_mtu,bound);
            assert_eq!(actual.shadow_limit,MAX_M2_FROZEN as u32);
            assert_eq!(actual.feedback_page_limit,1024);
            assert_eq!(actual.mature_live_limit,0);
            assert_eq!(actual.v3_enabled,1);
            assert_eq!(actual.process_repair_hard_cap,14_000_000);
            assert_eq!(actual.direction_fresh_confirmed,0);
            assert!(actual.direction_epoch_limit>0);
            assert_eq!(m2_effective_entry(&e,[9;16],93,21).map(|_|()),Err(INVALID));
        }
        assert_eq!(quiesce_wintun(&mut r,h,ep,93,21),OK);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(release(&mut r,h),OK);
    }
    #[test]
    fn m0_windows_owner_real_native_prepare_commit_stop_generation_scoped(){
        let mut r=Registry{generation:11,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let h=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        assert_eq!(h>>32,11);
        assert_eq!(r.entries[&h].lock().unwrap().phase,PH_PREPARED);
        assert_eq!(commit(&mut r,h,1,9,800),INVALID);
        assert_eq!(stop(&mut r,h),BAD_STAGE);
        assert_eq!(release(&mut r,h),BAD_STAGE);
        assert_eq!(commit(&mut r,h,0,0,800),OK);
        assert_eq!(r.entries[&h].lock().unwrap().phase,PH_ACTIVE);
        assert_eq!(commit(&mut r,h,0,0,800),BAD_STAGE);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(r.entries[&h].lock().unwrap().phase,PH_STOPPED);
        assert_eq!(release(&mut r,h),OK);
        assert_eq!(commit(&mut r,h,0,0,801),UNKNOWN);
        let prepared=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        assert_eq!(abort(&mut r,prepared),OK);
        assert_eq!(abort(&mut r,prepared),UNKNOWN);
        let newer=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        assert_ne!(newer,h);
        assert_eq!(stop(&mut r,h),UNKNOWN);
        assert_eq!(r.entries[&newer].lock().unwrap().phase,PH_PREPARED);
    }
    #[test]
    fn m0_windows_owner_role_fec2_bad_handoff_stale_and_prevent_public_apply(){
        let mut r=Registry{generation:3,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        assert_eq!(allocate(&mut r,&cold(true),&cmd(),false),Err(INVALID));
        assert_eq!(allocate(&mut r,&cold(false),&cmd(),true),Err(INVALID));
        let mut bad=cmd();bad[27]=1;
        assert_eq!(allocate(&mut r,&cold(false),&bad,false),Err(INVALID));
        bad=cmd();bad[4..6].copy_from_slice(&2u16.to_be_bytes());
        bad[27..29].copy_from_slice(&7u16.to_be_bytes());
        let feature7=allocate(&mut r,&cold(false),&bad,false);
        if cfg!(feature="fec2_product_record"){
            let candidate=feature7.expect("feature7 candidate scope");
            assert_eq!(abort(&mut r,candidate),OK);
        }else{assert_eq!(feature7,Err(INVALID));}
        assert_eq!(PRODUCT_APPLIED,0);
        let good=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        assert_eq!(stage(&mut r,good,500,&[]),INVALID);
        assert_eq!(stage(&mut r,good,500,&[0u8;9]),OK);
        assert_eq!(commit(&mut r,good,0,0,900),INVALID);
        assert_eq!(commit(&mut r,good,1,9,900),OK);
        assert_eq!(abort(&mut r,good),BAD_STAGE);
        assert_eq!(stage(&mut r,good,500,&[0u8;9]),BAD_STAGE);
        assert_eq!(stop(&mut r,good),OK);
        assert_eq!(release(&mut r,good),OK);
    }
    #[test]
    fn m0_windows_authenticated_generation_real_wintun_lease_stop_fence_and_stale(){
        let mut r=Registry{generation:91,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let h=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        // cold fixture uses [28..44] as logical_epoch; [44..60] is incarnation.
        let exact=[2u8;16];
        assert_eq!(bind_wintun(&mut r,h,exact,123,77),BAD_STAGE);
        assert_eq!(commit(&mut r,h,0,0,901),OK);
        assert_eq!(bind_wintun(&mut r,h,[0;16],123,77),INVALID);
        assert_eq!(bind_wintun(&mut r,h,[9;16],123,77),INVALID);
        assert_eq!(bind_wintun(&mut r,h,exact,0,77),INVALID);
        assert_eq!(bind_wintun(&mut r,h,exact,123,77),OK);
        assert_eq!(bind_wintun(&mut r,h,exact,123,77),BAD_STAGE);
        assert_eq!(stop(&mut r,h),STOP_INCOMPLETE);
        assert_eq!(release(&mut r,h),BAD_STAGE);
        assert_eq!(quiesce_wintun(&mut r,h,[9;16],123,77),INVALID);
        assert_eq!(quiesce_wintun(&mut r,h,exact,124,77),INVALID);
        assert_eq!(quiesce_wintun(&mut r,h,exact,123,78),INVALID);
        assert_eq!(stop(&mut r,h),STOP_INCOMPLETE);
        assert_eq!(quiesce_wintun(&mut r,h,exact,123,77),OK);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(release(&mut r,h),OK);
        assert_eq!(quiesce_wintun(&mut r,h,exact,123,77),UNKNOWN);
        let next=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        assert_ne!(h,next);
        assert_eq!(bind_wintun(&mut r,h,exact,123,77),UNKNOWN);
        assert_eq!(PRODUCT_APPLIED,0);
    }

    #[test]
    fn m0_windows_owner_v3_real_m1_m3_aead_pn_replay_and_generation(){
        let mut r=Registry{generation:101,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let client=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        let server=allocate(&mut r,&cold(true),&cmd(),true).unwrap();
        // Synthetic unit credentials do NOT authorize Windows product;
        // positive record bytes still pass the actual M3 AEAD/PN and M1
        // immutable FrozenRecord/borrowed owner queues (not a mock cipher).
        assert_eq!(commit(&mut r,client,0,0,500),OK);
        assert_eq!(commit(&mut r,server,0,0,500),OK);
        let epoch=[2u8;16];
        assert_eq!(v3_seal_one(&mut r,client,epoch,7,11,&[0x45;40],&mut [0;256]),
            Err(INVALID)); // cannot seal without real original Wintun bind
        assert_eq!(bind_wintun(&mut r,client,epoch,7,11),OK);
        assert_eq!(bind_wintun(&mut r,server,epoch,8,12),OK);
        assert!(set_path_mtu(&mut r,client,epoch,7,11,1400).is_ok());
        assert!(set_path_mtu(&mut r,server,epoch,8,12,1400).is_ok());
        let mut packet=[0u8;40];packet[0]=0x45;packet[2..4].copy_from_slice(&40u16.to_be_bytes());
        packet[8]=64;packet[9]=17;
        let mut encrypted=[0u8;256];
        let (n,seq,pn)=v3_seal_one(&mut r,client,epoch,7,11,&packet,&mut encrypted).unwrap();
        assert_eq!(n,packet.len()+FIXED_WIRE_OVERHEAD);
        assert_eq!(pn,0);
        assert_ne!(&encrypted[..n],packet.as_slice());
        let mut output=[0u8;256];
        let used=v3_open_one(&mut r,server,epoch,8,12,seq,&encrypted[..n],&mut output).unwrap();
        assert_eq!(&output[..used],packet.as_slice());
        assert_eq!(v3_open_one(&mut r,server,epoch,8,12,seq,&encrypted[..n],&mut output),Err(INVALID));
        let mut tampered=encrypted;
        tampered[n-1]^=1;
        assert_eq!(v3_open_one(&mut r,server,epoch,8,12,seq+n as u32,&tampered[..n],&mut output),Err(INVALID));
        assert_eq!(v3_seal_one(&mut r,client,[9;16],7,11,&packet,&mut encrypted),Err(INVALID));
        assert_eq!(v3_seal_one(&mut r,client,epoch,9,11,&packet,&mut encrypted),Err(INVALID));
        // Actual same M1 FrozenRecord/M3 AEAD/PN: beyond the obsolete 512B
        // smoke limit, then a newer authenticated TCP record arriving FIRST.
        // The gap must not make the newer independent business packet wait.
        let mut large=vec![0x42u8;1100];
        large[0]=0x45;large[2..4].copy_from_slice(&1100u16.to_be_bytes());
        large[8]=64;large[9]=17;
        let mut small=[0u8;84];
        small[0]=0x45;small[2..4].copy_from_slice(&84u16.to_be_bytes());
        small[8]=64;small[9]=17;
        let mut big_cipher=[0u8;2048];
        let mut small_cipher=[0u8;2048];
        let (big_len,big_seq,big_pn)=v3_seal_one(
            &r,client,epoch,7,11,&large,&mut big_cipher).unwrap();
        let (short_len,short_seq,short_pn)=v3_seal_one(
            &r,client,epoch,7,11,&small,&mut small_cipher).unwrap();
        assert_eq!(big_len,large.len()+FIXED_WIRE_OVERHEAD);
        assert_eq!(short_seq,big_seq+big_len as u32);
        assert_eq!((big_pn,short_pn),(1,2));
        let mut plaintext=[0u8;2048];
        let first=v3_open_one(&r,server,epoch,8,12,short_seq,
            &small_cipher[..short_len],&mut plaintext).unwrap();
        assert_eq!(&plaintext[..first],small.as_slice());
        assert_eq!(v3_open_one(&r,server,epoch,8,12,short_seq,
            &small_cipher[..short_len],&mut plaintext),Err(INVALID));
        let late=v3_open_one(&r,server,epoch,8,12,big_seq,
            &big_cipher[..big_len],&mut plaintext).unwrap();
        assert_eq!(&plaintext[..late],large.as_slice());

        assert_eq!(quiesce_wintun(&mut r,client,epoch,7,11),OK);
        assert_eq!(v3_seal_one(&mut r,client,epoch,7,11,&packet,&mut encrypted),Err(INVALID));
        assert_eq!(stop(&mut r,client),OK);
        assert_eq!(release(&mut r,client),OK);
        // Registry lookup after the exact generation was released must be UNKNOWN,
        // not an admitted stale record or an already-present inactive session.
        assert_eq!(v3_seal_one(&mut r,client,epoch,7,11,&packet,&mut encrypted),Err(UNKNOWN));
        assert_eq!(quiesce_wintun(&mut r,server,epoch,8,12),OK);
        assert_eq!(stop(&mut r,server),OK);
        assert_eq!(release(&mut r,server),OK);
    }

    #[test]
    fn win_v3_half_sampling_is_mixed_bounded_and_repair_is_single(){
        let lane=wbd_types::LaneKey{
            tunnel:wbd_types::TunnelKey{slot:3,generation:11},
            slot:9,generation:2,
        };
        let selected=(0..4096u64).filter(|pn|
            win_v3_admit_shadow(*pn,lane,MonoNs(2_000_000_000))
        ).count();
        assert!((1800..2300).contains(&selected));
        assert_eq!(MAX_M2_FROZEN,24_576);
        assert_eq!(WIN_NORMAL_M2_MIN_RETAIN_NS,1_200_000_000);
        assert_eq!(wbd_recovery::receipt::OUTER_REPAIR_ATTEMPT_LIMIT,1);
    }
    #[test]
    fn m0_windows_m2_v3_no_unsolicited_pto_repair_and_owned_stop(){
        // Original-Windows feature3 owner, real frozen firstsend and M2
        // shadow. W168 opportunistic-v3 MUST NOT turn an elapsed PTO into
        // plaintext refresh, new PN, fabricated ACK, or two blind repairs.
        use std::time::Duration;
        let mut r=Registry{generation:399,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let h=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        let epoch=[2u8;16];
        assert_eq!(commit(&mut r,h,0,0,500),OK);
        assert_eq!(bind_wintun(&mut r,h,epoch,91,19),OK);
        assert!(set_path_mtu(&mut r,h,epoch,91,19,1400).is_ok());
        let mut ipv4=[0u8;90];ipv4[0]=0x45;
        ipv4[2..4].copy_from_slice(&90u16.to_be_bytes());
        ipv4[8]=64;ipv4[9]=17;
        let mut wire=[0u8;2048];
        {
            let mut entry=r.entries[&h].lock().unwrap();
            assert_eq!(m2_arm_entry(&mut entry,epoch,91,19),Ok(()),
                "original M2 bootstrap must admit current generation");
            assert!(entry.m2.as_ref().unwrap().shadow.timing_snapshot().is_some());
            assert_eq!(entry.m2.as_ref().unwrap().shadow.policy_limits().1,MAX_M2_FROZEN);
        }
        let (used,seq,pn)=v3_seal_one(&r,h,epoch,91,19,&ipv4,&mut wire).unwrap();
        assert_eq!(pn,0);
        {
            let mut e=r.entries[&h].lock().unwrap();
            assert_eq!(m2_kernel_firstsend_entry(&mut e,epoch,91,19,pn,seq,used,1),Ok(1));
        }
        std::thread::sleep(Duration::from_millis(95));
        let mut candidate=[0u8;2048];
        {
            let mut e=r.entries[&h].lock().unwrap();
            assert!(m2_next_repair_entry(&mut e,epoch,91,19,&mut candidate)
                .unwrap().is_none(),"W168 v3 must not invent PTO repair without authenticated mature negative");
            assert_eq!(e.m2.as_ref().unwrap().shadow.outstanding(),1);
            assert!(e.m2.as_ref().unwrap().in_flight.is_none());
        }
        assert_eq!(quiesce_wintun(&mut r,h,epoch,91,19),OK);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(release(&mut r,h),OK);
        assert_eq!(v3_seal_one(&r,h,epoch,91,19,&ipv4,&mut wire),Err(UNKNOWN));
    }

    #[cfg(feature="fec2_product_record")]
    #[test]
    fn m0_windows_original_m2_only_real_npcap_firstsend_and_authenticated_kind1_retire(){
        use wbd_codec::{ControlTlv,Receipt,ReceiptPage};
        // Use the same production M1 frozen owner and genuine AEAD/PN
        // crypto. Test fixture cold is NOT original TLS and proves no OS
        // public connection, only exact-source recovery state transitions.
        let mut r=Registry{generation:301,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let client=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        let server=allocate(&mut r,&cold(true),&cmd(),true).unwrap();
        let epoch=[2u8;16];
        assert_eq!(commit(&mut r,client,0,0,500),OK);
        assert_eq!(commit(&mut r,server,0,0,500),OK);
        assert_eq!(bind_wintun(&mut r,client,epoch,71,91),OK);
        assert_eq!(bind_wintun(&mut r,server,epoch,72,92),OK);
        assert!(set_path_mtu(&mut r,client,epoch,71,91,1400).is_ok());
        assert!(set_path_mtu(&mut r,server,epoch,72,92,1400).is_ok());
        {
            let mut e=r.entries[&client].lock().unwrap();
            assert_eq!(m2_arm_entry(&mut e,[9;16],71,91),Err(BAD_STAGE));
            assert!(m2_arm_entry(&mut e,epoch,71,91).is_ok());
            assert_eq!(m2_arm_entry(&mut e,epoch,71,91),Err(BAD_STAGE));
        }
        let mut ipv4=[0u8;80];ipv4[0]=0x45;
        ipv4[2..4].copy_from_slice(&80u16.to_be_bytes());
        ipv4[8]=64;ipv4[9]=17;
        let mut wire=[0u8;2048];
        let (size,seq,pn)=v3_seal_one(
            &r,client,epoch,71,91,&ipv4,&mut wire).unwrap();
        let selected={
            let e=r.entries[&client].lock().unwrap();
            usize::from(win_v3_sample(pn,e.m2.as_ref().unwrap().route.outbound_lane()))
        };
        {
            let e=r.entries[&client].lock().unwrap();
            let m=e.m2.as_ref().unwrap();
            assert_eq!(m.shadow.outstanding(),0); // sealing is NOT kernel send
            assert_eq!(m.pending.len(),1); // same immutable M1 frozen handle
            assert_eq!(m.pending[&RecordPn(pn)].bytes(),&wire[..size]);
        }
        {
            let mut e=r.entries[&client].lock().unwrap();
            assert_eq!(m2_kernel_firstsend_entry(
                &mut e,epoch,71,91,pn,seq,size+1,1),Err(INVALID));
            assert_eq!(m2_kernel_firstsend_entry(
                &mut e,epoch,71,91,pn,seq,size,1),Ok(selected as u32));
            assert_eq!(m2_kernel_firstsend_entry(
                &mut e,epoch,71,91,pn,seq,size,1),Err(INVALID));
            assert_eq!(e.m2.as_ref().unwrap().shadow.outstanding(),selected);
        }
        // TCP presentation ACK never enters this recovery state.
        let mut bitmap=[0u8;32];bitmap[0]=1;
        let receipt=wbd_codec::encode_control(&[ControlTlv::Receipt(Receipt{
            largest_data_pn:pn,ack_delay_us:0,report_seq:1,
            pages:vec![ReceiptPage{base_pn:0,bitmap}]
        })],512).unwrap();
        let (rseq,rwire)={
            let mut e=r.entries[&server].lock().unwrap();
            let slab=e.arena.allocate().unwrap();
            let budget=normal_off_windows_budget(&e).unwrap();
            let (_,seq,len)=e.owner.seal_original_authenticated_receipt(
                slab,&receipt,budget,0,MonoNs(0)).unwrap();
            let storage=std::mem::take(&mut e.tx_scratch);
            let batch=e.owner.drain_tx(MonoNs(0),storage)
                .unwrap_or_else(|_|panic!("same protected M1 control missing"));
            let out={
                let rows=e.owner.checked_tx_ready(&batch).unwrap();
                assert_eq!(rows.len(),1);
                assert_eq!(rows[0].record.bytes().len(),len);
                rows[0].record.bytes().to_vec()
            };
            e.tx_scratch=batch.recycle();
            (seq,out)
        };
        let mut tamper=rwire.clone();*tamper.last_mut().unwrap()^=1;
        let mut plain=[0u8;2048];
        assert_eq!(v5_open_record_one(&r,client,epoch,71,91,rseq,
            &tamper,&mut plain),Err(INVALID));
        assert_eq!(r.entries[&client].lock().unwrap()
            .m2.as_ref().unwrap().shadow.outstanding(),selected);
        assert_eq!(v5_open_record_one(&r,client,epoch,71,91,rseq,
            &rwire,&mut plain),Ok((0,2,0)));
        assert_eq!(r.entries[&client].lock().unwrap()
            .m2.as_ref().unwrap().shadow.outstanding(),0);
        assert_eq!(v5_open_record_one(&r,client,epoch,71,91,rseq,
            &rwire,&mut plain),Err(INVALID)); // PN replay not receipt reapply
        {
            let e=r.entries[&client].lock().unwrap();
            assert!(e.authenticated_kind1.is_empty()); // consumed scoped M2
        }
        assert_eq!(quiesce_wintun(&mut r,client,epoch,71,91),OK);
        assert_eq!(stop(&mut r,client),OK);
        assert_eq!(release(&mut r,client),OK);
        assert_eq!(quiesce_wintun(&mut r,server,epoch,72,92),OK);
        assert_eq!(stop(&mut r,server),OK);
        assert_eq!(release(&mut r,server),OK);
    }

    #[cfg(feature="fec2_product_record")]
    #[test]
    fn m0_windows_original_m3_kind1_aead_unique_pn_stages_only_once_then_stop_retires(){
        use wbd_codec::{ControlTlv,Receipt,ReceiptPage};
        let mut r=Registry{generation:201,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let server=allocate(&mut r,&cold(true),&cmd(),true).unwrap();
        let client=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        assert_eq!(commit(&mut r,server,0,0,500),OK);
        assert_eq!(commit(&mut r,client,0,0,500),OK);
        let epoch=[2u8;16];
        assert_eq!(bind_wintun(&mut r,server,epoch,9,13),OK);
        assert_eq!(bind_wintun(&mut r,client,epoch,8,12),OK);
        assert!(set_path_mtu(&mut r,server,epoch,9,13,1400).is_ok());
        assert!(set_path_mtu(&mut r,client,epoch,8,12,1400).is_ok());
        let mut bitmap=[0u8;32];bitmap[0]=1;
        let control= wbd_codec::encode_control(&[ControlTlv::Receipt(Receipt{
            largest_data_pn:0,ack_delay_us:0,report_seq:1,
            pages:vec![ReceiptPage{base_pn:0,bitmap}],
        })],512).unwrap();
        let (seq,pn,wire)={
            let lane=r.entries.get(&server).unwrap();
            let mut e=lane.lock().unwrap();
            let budget=normal_off_windows_budget(&e).unwrap();
            let slab=e.arena.allocate().unwrap();
            let (pn,seq,used)=e.owner.seal_original_authenticated_receipt(
                slab,&control,budget,0,MonoNs(0)).unwrap();
            let storage=std::mem::take(&mut e.tx_scratch);
            let batch=e.owner.drain_tx(MonoNs(0),storage)
                .unwrap_or_else(|_|panic!("actual M1 TX batch must drain"));
            let wire={
                let ready=e.owner.checked_tx_ready(&batch).unwrap();
                assert_eq!(ready.len(),1);
                assert_eq!(ready[0].record.bytes().len(),used);
                ready[0].record.bytes().to_vec()
            };
            e.tx_scratch=batch.recycle();
            (seq,pn,wire)
        };
        assert_eq!(pn,0);
        assert!(wire.len()>FIXED_WIRE_OVERHEAD);
        assert_ne!(&wire[..control.len()],control.as_slice());
        let mut out=[0u8;2048];
        // Legacy v3 boundary publishes business IPv4 ONLY. Exact same
        // replay opener retains the authenticated kind1 for future M2.
        assert_eq!(v5_open_record_one(&r,client,epoch,8,12,seq,&wire,&mut out),
            Ok((0,2,0)));
        {
            let e=r.entries.get(&client).unwrap().lock().unwrap();
            assert_eq!(e.authenticated_kind1.len(),1);
            let (opened_pn,receipt)=e.authenticated_kind1.front().unwrap();
            assert_eq!(*opened_pn,0);
            assert_eq!(receipt.report_seq,1);
            assert_eq!(receipt.pages.len(),1);
            assert_eq!(receipt.pages[0].bitmap[0],1);
        }
        assert_eq!(v3_open_one(&r,client,epoch,8,12,seq,&wire,&mut out),Err(INVALID));
        assert_eq!(r.entries[&client].lock().unwrap().authenticated_kind1.len(),1);
        let mut corrupt=wire.clone();*corrupt.last_mut().unwrap()^=1;
        assert_eq!(v3_open_one(&r,client,epoch,8,12,seq+wire.len() as u32,
            &corrupt,&mut out),Err(INVALID));
        assert_eq!(r.entries[&client].lock().unwrap().authenticated_kind1.len(),1);
        assert_eq!(quiesce_wintun(&mut r,client,epoch,8,12),OK);
        assert_eq!(stop(&mut r,client),OK);
        assert_eq!(r.entries[&client].lock().unwrap().authenticated_kind1.len(),0);
        assert_eq!(release(&mut r,client),OK);
        assert_eq!(quiesce_wintun(&mut r,server,epoch,9,13),OK);
        assert_eq!(stop(&mut r,server),OK);
        assert_eq!(release(&mut r,server),OK);
    }

    #[test]
    fn m0_windows_m2_short_feedback_output_does_not_burn_original_tx_sequence(){
        // A deterministic real-M1 sealing boundary, no fake peer delivery.
        // The previous code sealed kind1 BEFORE discovering that out was too
        // short, returned Ok(None), and silently skipped one TCP wire span.
        let mut r=Registry{generation:590,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let h=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        let epoch=[2u8;16];
        assert_eq!(commit(&mut r,h,0,0,500),OK);
        assert_eq!(bind_wintun(&mut r,h,epoch,91,19),OK);
        assert!(set_path_mtu(&mut r,h,epoch,91,19,1400).is_ok());
        let mut ipv4=[0u8;90];ipv4[0]=0x45;
        ipv4[2..4].copy_from_slice(&90u16.to_be_bytes());
        ipv4[8]=64;ipv4[9]=17;
        {
            let mut e=r.entries[&h].lock().unwrap();
            assert!(m2_arm_entry(&mut e,epoch,91,19).is_ok());
        }
        let mut first=[0u8;2048];
        let (first_len,first_seq,_pn)=v3_seal_one(
            &r,h,epoch,91,19,&ipv4,&mut first).unwrap();
        // Inject a verified-M3 DATA observation *only* into this internal
        // unit fixture's feedback state. This is not an OS product PASS.
        {
            let mut e=r.entries[&h].lock().unwrap();
            e.m2.as_mut().unwrap().feedback.on_authenticated_data(
                RecordPn(19),m2_clock());
        }
        std::thread::sleep(std::time::Duration::from_millis(20));
        let mut short=[0u8;64]; // encoded kind1 (one page) cannot fit
        {
            let mut e=r.entries[&h].lock().unwrap();
            assert_eq!(m2_next_feedback_entry(
                &mut e,epoch,91,19,&mut short),Ok(None));
            assert!(e.m2.as_ref().unwrap().feedback_pending.is_none());
        }
        let mut second=[0u8;2048];
        let (_second_len,second_seq,_)=v3_seal_one(
            &r,h,epoch,91,19,&ipv4,&mut second).unwrap();
        assert_eq!(second_seq,first_seq.wrapping_add(first_len as u32),
            "unsent M2 draft must never create a hidden Rust/Go seq gap");
        assert_eq!(quiesce_wintun(&mut r,h,epoch,91,19),OK);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(release(&mut r,h),OK);
    }

    #[test]
    fn m0_windows_native_original_source_batch_preflights_all_then_contiguous_m1(){
        assert_eq!(std::mem::size_of::<WbdWindowsOriginalSourceInput>(),2056);
        assert_eq!(std::mem::size_of::<WbdWindowsOriginalSourceOutput>(),2064);
        let mut r=Registry{generation:611,entries:BTreeMap::new(),
            game_groups:BTreeMap::new()};
        let h=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        assert_eq!(commit(&mut r,h,0,0,500),OK);
        let ep=[2u8;16];
        assert_eq!(bind_wintun(&mut r,h,ep,81,18),OK);
        assert!(set_path_mtu(&mut r,h,ep,81,18,1400).is_ok());
        let mut e=r.entries[&h].lock().unwrap();
        m2_arm_entry(&mut e,ep,81,18).unwrap();
        let make=|seed:u8|{
            let mut ipv4=[0u8;2048];
            ipv4[0]=0x45;
            ipv4[2..4].copy_from_slice(&90u16.to_be_bytes());
            ipv4[8]=64;ipv4[9]=17;
            ipv4[20]=seed;
            WbdWindowsOriginalSourceInput{
                length:90,reserved:0,ipv4,
            }
        };
        let inputs=[make(1),make(2),make(3),make(4)];
        let empty=||WbdWindowsOriginalSourceOutput{
            used:0,seq:0,pn:0,wire:[0;2048],
        };
        let mut out=[empty(),empty(),empty(),empty()];
        let mut invalid=inputs;
        invalid[3].reserved=1;
        assert_eq!(original_source_batch_entry(
            &mut e,ep,81,18,&invalid,&mut out),(INVALID,0));
        assert!(e.m2.as_ref().unwrap().pending.is_empty(),
            "batch input error may not spend even first original PN");
        let (status,n)=original_source_batch_entry(
            &mut e,ep,81,18,&inputs,&mut out);
        assert_eq!((status,n),(OK,4));
        let mut distinct=BTreeSet::new();
        for (i,row) in out.iter().enumerate(){
            assert_eq!(row.used,121);
            assert!(distinct.insert(row.pn));
            if i>0{
                assert_eq!(row.seq,
                    out[i-1].seq.wrapping_add(out[i-1].used));
            }
        }
        assert_eq!(e.m2.as_ref().unwrap().pending.len(),4,
            "only genuine future NPF firstsend callbacks can give F credit");
        assert_eq!(e.m2.as_ref().unwrap().shadow.outstanding(),0);
        // Explicitly settle original pending PNs as Uncertain for this
        // native unit: no fake Accepted/F credit, no frozen staging
        // retained into owned Stop, and no reusable nonce/SEQ.
        for row in &out{
            m2_kernel_firstsend_entry(&mut e,ep,81,18,
                row.pn,row.seq,row.used as usize,2).unwrap();
        }
        assert!(e.m2.as_ref().unwrap().pending.is_empty());
        assert_eq!(e.m2.as_ref().unwrap().shadow.outstanding(),0);
        drop(e);
        assert_eq!(quiesce_wintun(&mut r,h,ep,81,18),OK);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(release(&mut r,h),OK);
    }
    #[test]
    fn m0_windows_m2_batch_validates_entire_original_seq_and_uncertain_once(){
        assert_eq!(std::mem::size_of::<WbdWindowsM2FirstsendResult>(),24);
        let mut r=Registry{generation:601,entries:BTreeMap::new(),
            game_groups:BTreeMap::new()};
        let h=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        assert_eq!(commit(&mut r,h,0,0,500),OK);
        let ep=[2u8;16];
        assert_eq!(bind_wintun(&mut r,h,ep,81,18),OK);
        assert!(set_path_mtu(&mut r,h,ep,81,18,1400).is_ok());
        let mut e=r.entries[&h].lock().unwrap();
        m2_arm_entry(&mut e,ep,81,18).unwrap();
        let mut frame=[0u8;90];frame[0]=0x45;
        frame[2..4].copy_from_slice(&90u16.to_be_bytes());
        frame[8]=64;frame[9]=17;
        let mut dst=[0u8;2048];
        let (n1,seq1,pn1)=v3_seal_entry(
            &mut e,ep,81,18,&frame,&mut dst).unwrap();
        let (n2,seq2,pn2)=v3_seal_entry(
            &mut e,ep,81,18,&frame,&mut dst).unwrap();
        assert_eq!(seq2,seq1.wrapping_add(n1 as u32));
        let a=WbdWindowsM2FirstsendResult{
            pn:pn1,seq:seq1,wire_len:n1 as u32,outcome:1,reserved:0};
        let b=WbdWindowsM2FirstsendResult{
            pn:pn2,seq:seq2,wire_len:n2 as u32,outcome:2,reserved:0};
        assert_eq!(m2_kernel_firstsend_batch_entry(
            &mut e,ep,81,18,&[a,a]),(INVALID,0,0));
        assert_eq!(m2_kernel_firstsend_batch_entry(
            &mut e,ep,81,18,&[a,WbdWindowsM2FirstsendResult{
                seq:seq2.wrapping_add(1),..b}]),(INVALID,0,0));
        assert_eq!(e.m2.as_ref().unwrap().pending.len(),2,
            "invalid batch must not consume any original pending PN");
        let (status,settled,count)=m2_kernel_firstsend_batch_entry(
            &mut e,ep,81,18,&[a,b]);
        assert_eq!((status,settled,count),(OK,2,1));
        assert!(e.m2.as_ref().unwrap().pending.is_empty());
        assert_eq!(e.m2.as_ref().unwrap().shadow.outstanding(),1,
            "only actually copied NPF row earns retained immutable repair");
        assert_eq!(m2_kernel_firstsend_batch_entry(
            &mut e,ep,81,18,&[a]),(INVALID,0,0),
            "same PN cannot be reported as an additional fresh send");
        drop(e);
        assert_eq!(quiesce_wintun(&mut r,h,ep,81,18),OK);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(release(&mut r,h),OK);
    }
    #[test]
    fn m0_windows_original_source_after_real_clock_feedback_has_contiguous_seq(){
        // A real M2 receipt is sealed at monotonic time, then a new
        // original-Go TLS DATA must NOT rewind the exact same M1 owner
        // clock by presenting synthetic MonoNs(0).
        let mut r=Registry{generation:701,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let h=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        assert_eq!(commit(&mut r,h,0,0,500),OK);
        let ep=[2u8;16];
        assert_eq!(bind_wintun(&mut r,h,ep,91,19),OK);
        assert!(set_path_mtu(&mut r,h,ep,91,19,1400).is_ok());
        let mut first=[0u8;2048];
        let mut frame=[0u8;90];
        frame[0]=0x45;frame[2..4].copy_from_slice(&90u16.to_be_bytes());
        frame[8]=64;frame[9]=17;
        let (n1,s1,_)=v3_seal_one(&r,h,ep,91,19,&frame,&mut first).unwrap();
        {
            let mut e=r.entries[&h].lock().unwrap();
            assert!(m2_arm_entry(&mut e,ep,91,19).is_ok());
            e.m2.as_mut().unwrap().feedback.on_authenticated_data(
                RecordPn(89),m2_clock());
        }
        std::thread::sleep(std::time::Duration::from_millis(21));
        let mut wire=[0u8;2048];
        let (nc,sc,_pn)={
            let mut e=r.entries[&h].lock().unwrap();
            m2_next_feedback_entry(&mut e,ep,91,19,&mut wire)
                .unwrap().expect("actual original M2 authenticated draft")
        };
        assert_eq!(sc,s1.wrapping_add(n1 as u32));
        let (n2,s2,_)=v3_seal_one(&r,h,ep,91,19,&frame,&mut first)
            .expect("fresh DATA after kind1 must keep monotonic owner clock");
        assert_eq!(s2,sc.wrapping_add(nc as u32));
        assert!(n2>51);
        assert_eq!(quiesce_wintun(&mut r,h,ep,91,19),OK);
        assert_eq!(stop(&mut r,h),OK);
        assert_eq!(release(&mut r,h),OK);
    }
    #[test]
    fn m0_windows_tcp_sequence_unwrap_gap_wrap_and_future_reject(){
        let mut r=Registry{generation:3,entries:BTreeMap::new(),game_groups:BTreeMap::new()};
        let h=allocate(&mut r,&cold(false),&cmd(),false).unwrap();
        let lane=r.entries.get(&h).unwrap();
        let mut e=lane.lock().unwrap();
        e.rx_unwrapped_high=(1u64<<32)-50;
        assert_eq!(m0_tcp_unwrap(&e,30,100).unwrap(),(1u64<<32)+30);
        assert_eq!(m0_tcp_unwrap(&e,u32::MAX-80,40).unwrap(),
            u64::from(u32::MAX-80));
        assert_eq!(m0_tcp_unwrap(&e,200_000,100).unwrap(),(1u64<<32)+200_000);
        assert_eq!(m0_tcp_unwrap(&e,5*1024*1024,100),Err(INVALID));
        e.rx_unwrapped_high=(1u64<<32)+120;
        assert_eq!(m0_tcp_unwrap(&e,30,40).unwrap(),(1u64<<32)+30);
        assert_eq!(m0_tcp_unwrap(&e,150,40).unwrap(),(1u64<<32)+150);
    }

}
