//! Narrow native-vs-Go/scalar oracle tests; do not repeat unrelated record/LINK.
#![forbid(unsafe_code)]
use crate::fec_math::{ReedSolomon20,FecBackendChoice,FecBackendUsed,FecMathError};
use crate::link_fec_wire::{FecHeader,FecShardPhase,FEC_HEADER};

fn originals(k:usize,len:usize)->Vec<Vec<u8>>{
    (0..k).map(|i|{
        let size=if i==0{len}else{len-(i%5).min(len-1)};
        (0..size).map(|j|((i*31+j*13+5)%251) as u8).collect::<Vec<_>>()
    }).collect()
}
fn final_meta(src:&[Vec<u8>],len:usize,r:u8)->FecHeader{
    let mut lengths=[0u16;20];
    for (i,s) in src.iter().enumerate(){lengths[i]=s.len() as u16;}
    FecHeader{block_id:0x01020304,shard_index:20,parity_count:r,
        data_count:src.len() as u8,shard_size:len as u16,
        lengths,phase:FecShardPhase::FinalParity}
}
fn expected_used(len:usize)->FecBackendUsed{
    #[cfg(feature="native-isal")]
    if len>=64 {return FecBackendUsed::NativeIsaL;}
    let _=len;
    FecBackendUsed::Scalar
}
#[test]
fn r1_fec_selected_backend_go_matrix_all_profiles_short_unaligned_mtu(){
    let rs=ReedSolomon20::new().unwrap();
    // Full 20:20 and partial k<R use unchanged Go-normalized coefficient
    // positions. Every test includes deterministic dirty-tail zero padding.
    for k in 1..=20{
        for r in [4u8,8,10,12,16,20]{
            for len in [1usize,63,64,65,257,512,1200,1373]{
                let parts=originals(k,len);
                let refs=parts.iter().map(Vec::as_slice).collect::<Vec<_>>();
                let expected=rs.encode_active(&refs,r).unwrap();
                let count=expected.len();
                let (parity,used)=rs.encode_rows_active_selected(&refs,r,0,count,
                    FecBackendChoice::PreferNative).unwrap();
                assert_eq!(used,expected_used(len),"k={k} r={r} L={len}");
                assert_eq!(parity,expected,"k={k} r={r} L={len}");
                // Exact old Go 56B header and row/index/length geometry.
                let (wires,wire_used)=rs.final_parity_wires_range_selected(
                    0x01020304,&refs,r,len+FEC_HEADER,0,count,
                    FecBackendChoice::PreferNative).unwrap();
                let old=rs.final_parity_wires(0x01020304,&refs,r,len+FEC_HEADER).unwrap();
                assert_eq!(wire_used,used);
                assert_eq!(wires,old,"wire k={k} r={r} L={len}");
                if len<64{
                    assert_eq!(rs.encode_rows_active_selected(&refs,r,0,1,
                        FecBackendChoice::RequireNative),
                        Err(FecMathError::NativeUnavailable));
                }
            }
        }
    }
}
#[test]
fn r1_fec_selected_backend_missing_only_direct_inverse_recovery(){
    let rs=ReedSolomon20::new().unwrap();
    for k in 1..=20{
        for r in [4u8,8,10,12,16,20]{
            for len in [1usize,64,65,257,1200]{
                let parts=originals(k,len);
                let refs=parts.iter().map(Vec::as_slice).collect::<Vec<_>>();
                let p=rs.encode_active(&refs,r).unwrap();
                // Non-prefix erasures and reversed parity arrival exercise
                // row choice, e-by-e inversion and direct output coefficients.
                let e=k.min(r as usize).min(4);
                let missing=(k-e..k).collect::<Vec<_>>();
                let sources=(0..k).map(|i|if missing.contains(&i){
                    None
                }else{Some(parts[i].as_slice())}).collect::<Vec<_>>();
                let available=p.iter().enumerate().take(e).rev()
                    .map(|(i,row)|((20+i) as u8,row.as_slice())).collect::<Vec<_>>();
                let meta=final_meta(&parts,len,r);
                let old=rs.recover_missing(&meta,&sources,&available).unwrap();
                let (new,used)=rs.recover_missing_selected(&meta,&sources,
                    &available,FecBackendChoice::PreferNative).unwrap();
                assert_eq!(new,old,"k={k} r={r} L={len}");
                assert_eq!(used,expected_used(len));
                for (i,b) in new{assert_eq!(b,parts[i]);}
            }
        }
    }
    // Maximal 20 erasures must still use e x e inverse, not 20 parity
    // reconstructions or the unrelated ISA-L Cauchy generator.
    for k in [1usize,4,12,20]{
        let rs=ReedSolomon20::new().unwrap();
        let data=originals(k,65);
        let refs=data.iter().map(Vec::as_slice).collect::<Vec<_>>();
        let p=rs.encode_active(&refs,20).unwrap();
        let par=p.iter().enumerate().map(|(i,p)|((20+i) as u8,p.as_slice()))
            .collect::<Vec<_>>();
        let (recovered,used)=rs.recover_missing_selected(
            &final_meta(&data,65,20),&vec![None;k],&par,
            FecBackendChoice::PreferNative).unwrap();
        assert_eq!(used,expected_used(65));
        assert_eq!(recovered,data.into_iter().enumerate().collect::<Vec<_>>());
    }
}
#[test]
fn r1_fec_selected_backend_actual_owner_20_20_and_no_fake_native(){
    use crate::fec_tx::FecTxOwner;
    let len=65usize;let budget=20*len;
    let mut scalar=FecTxOwner::new(1,budget).unwrap();
    let mut native=FecTxOwner::new_cooperative_with_backend(1,budget,
        FecBackendChoice::PreferNative).unwrap();
    let mut golden=Vec::new();
    for i in 0..20{
        let source=vec![(i*7+1) as u8;len];
        let prior=scalar.submit(&source,i as u64,20,len+FEC_HEADER,false).unwrap();
        let current=native.submit(&source,i as u64,20,len+FEC_HEADER,false).unwrap();
        assert_eq!(current.systematic,prior.systematic);
        assert!(current.parity.is_empty());
        golden.extend(prior.parity);
    }
    let mut real=Vec::new();
    for _ in 0..5{
        let frame=native.poll_cooperative_parity().unwrap();
        assert!(frame.systematic.is_empty());
        assert_eq!(frame.parity.len(),4);
        assert_eq!(native.last_parity_backend(),Some(expected_used(len)));
        real.extend(frame.parity);
    }
    assert_eq!(real,golden);
    assert_eq!(native.stats().retained_bytes,0);
    // Required mode is fail-closed when feature or size is unsupported:
    // a failed poll must not advance a parity row.
    let mut short=FecTxOwner::new_cooperative_with_backend(7,20,
        FecBackendChoice::RequireNative).unwrap();
    short.submit(b"x",0,20,57,false).unwrap();
    short.flush_due(32).unwrap();
    assert_eq!(short.poll_cooperative_parity(),Err(crate::fec_tx::TxError::Math(
        FecMathError::NativeUnavailable)));
    assert_eq!(short.stats().pending_parity_rows,1);
    #[cfg(feature="native-isal")]
    {
        assert_eq!(native.last_parity_backend(),Some(FecBackendUsed::NativeIsaL));
        println!("M3_ACTUAL_ISAL_GO_MATRIX_NATIVE_ENCODE_AND_RECOVERY");
        println!("M3_NATIVE_HOST_ARCH={} AVX2={} SSE2={}",
            std::env::consts::ARCH,
            std::is_x86_feature_detected!("avx2"),
            std::is_x86_feature_detected!("sse2"));
    }
}

#[cfg(all(target_os="linux",feature="native-isal"))]
fn r1_fec_cpu_ns()->Option<u64>{
    let text=std::fs::read_to_string("/proc/thread-self/schedstat").ok()?;
    text.split_whitespace().next()?.parse::<u64>().ok()
}

/// Single fixed 20:20/1200B source, identical generator, inputs and recovery
/// for both legs. Order is declared through WBD_FEC_ORDER=AB or BA BEFORE job.
/// This diagnoses codec-only CPU and local operation latency, NOT packet RTT,
/// kernel delivery, QoS, FEC queue fairness or physical throughput.
#[cfg(all(target_os="linux",feature="native-isal"))]
#[test]
#[ignore = "M0 pinned native ISA-L Linux Release compiled-once same-VM job only"]
fn r1_fec_native_release_same_vm_scalar_isal_paired_cpu(){
    use std::time::{Instant,Duration};
    use std::hint::black_box;
    assert!(!cfg!(debug_assertions),"Release only");
    let order=std::env::var("WBD_FEC_ORDER").unwrap_or_else(|_|"AB".into());
    assert!(order=="AB"||order=="BA");
    let modes=if order=="AB"{
        [FecBackendChoice::Scalar,FecBackendChoice::RequireNative]
    }else{
        [FecBackendChoice::RequireNative,FecBackendChoice::Scalar]
    };
    let rs=ReedSolomon20::new().unwrap();
    let data=(0..20).map(|i|(0..1200)
        .map(|j|((i*37+j*19+23)%251) as u8).collect::<Vec<_>>())
        .collect::<Vec<_>>();
    let slices=data.iter().map(Vec::as_slice).collect::<Vec<_>>();
    let expected=rs.encode_active(&slices,20).unwrap();
    let m=final_meta(&data,1200,20);
    let mut known=(0..20).map(|i|Some(data[i].as_slice())).collect::<Vec<_>>();
    for i in 16..20{known[i]=None;}
    let mode_name=|m:FecBackendChoice|if m==FecBackendChoice::Scalar{"scalar"}else{"native-isal"};
    let once=|choice:FecBackendChoice|->u8{
        // Five bounded four-row quanta, actual parity delivered to codec
        // recovery e=4, no skipped parity to buy cheaper CPU.
        let mut parity=Vec::new();
        for first in [0,4,8,12,16]{
            let (batch,used)=rs.encode_rows_active_selected(&slices,20,first,4,choice).unwrap();
            assert_eq!(used,if choice==FecBackendChoice::Scalar{
                FecBackendUsed::Scalar
            }else{FecBackendUsed::NativeIsaL});
            parity.extend(batch);
        }
        assert_eq!(parity,expected);
        let selected=(0..4).map(|j|((20+j) as u8,parity[j].as_slice())).collect::<Vec<_>>();
        let (recovered,backend)=rs.recover_missing_selected(&m,&known,&selected,choice).unwrap();
        assert_eq!(backend,if choice==FecBackendChoice::Scalar{
            FecBackendUsed::Scalar
        }else{FecBackendUsed::NativeIsaL});
        assert_eq!(recovered.len(),4);
        for (idx,b) in recovered{assert_eq!(b,data[idx]);}
        parity[0][0]
    };
    println!("M3_FEC_CPU_HOST order={} arch={} SSE2={} SSSE3={} AVX2={} AVX512F={} source=PINNED_ACTION_MANIFEST",
        order,std::env::consts::ARCH,
        std::is_x86_feature_detected!("sse2"),
        std::is_x86_feature_detected!("ssse3"),
        std::is_x86_feature_detected!("avx2"),
        std::is_x86_feature_detected!("avx512f"));
    for (leg,choice) in modes.into_iter().enumerate(){
        // Warmup excluded from both measurements; execute identical genuine
        // 20 original + 20 first-send parity + 4 recovered-source work.
        let warm=Instant::now();
        while warm.elapsed()<Duration::from_millis(200){black_box(once(choice));}
        let mut windows_ok=0usize;
        let mut windows_bad=0usize;
        let mut wall_total=0u128;
        let mut cpu_total=0u128;
        let mut blocks=0usize;
        let mut latency=Vec::<u64>::new();
        while wall_total<Duration::from_millis(1125).as_nanos(){
            let wall_start=Instant::now();
            let cpu_start=r1_fec_cpu_ns();
            let mut n=0usize;
            while n<16||wall_start.elapsed()<Duration::from_millis(250){
                let call=Instant::now();
                black_box(once(choice));
                if latency.len()<2048{
                    latency.push(call.elapsed().as_nanos().min(u128::from(u64::MAX)) as u64);
                }
                n+=1;
            }
            let cpu_end=r1_fec_cpu_ns();
            let wall_ns=wall_start.elapsed().as_nanos();
            let cpu_ns=match (cpu_start,cpu_end){
                (Some(b),Some(e)) if e>=b && u128::from(e-b)*100<=wall_ns*102=>Some(e-b),
                _=>None
            };
            if let Some(v)=cpu_ns{cpu_total+=u128::from(v);windows_ok+=1;}
            else{windows_bad+=1;}
            println!("M3_FEC_CPU_RAW order={} leg={} mode={} wall_ns={} cpu_ns={} clock_status={} blocks={} systematic={} parity={} recovered={}",
                order,leg,mode_name(choice),wall_ns,cpu_ns.unwrap_or(0),
                if cpu_ns.is_some(){"OK"}else{"CPU_INCONCLUSIVE"},n,20*n,20*n,4*n);
            wall_total+=wall_ns;blocks+=n;
        }
        latency.sort_unstable();
        let p99=latency[(latency.len()-1)*99/100];
        println!("M3_FEC_CPU_RESULT order={} leg={} mode={} cpu_qualified={} cpu_ns={} wall_ns={} blocks={} systematic={} parity={} recovered={} p99_CODEC_OPERATION_WALL_ns={} windows_ok={} windows_bad={} NIC_DELIVERY=NOT_RUN PACKET_P99=NOT_RUN SIMD_INSTRUCTION_PROOF=NOT_RUN PRODUCT=NOT_RUN",
            order,leg,mode_name(choice),
            if windows_bad==0&&windows_ok>0{"SAME_WINDOW_CPU"}else{"CPU_INCONCLUSIVE"},
            if windows_bad==0{cpu_total}else{0},wall_total,blocks,
            blocks*20,blocks*20,blocks*4,p99,windows_ok,windows_bad);
        assert!(wall_total>=Duration::from_millis(1125).as_nanos()&&blocks>0);
    }
}
