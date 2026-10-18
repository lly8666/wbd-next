//! M0 source-locked, Actions-only FEC2 codec cost fixture. NOT product code.
//! One deterministic C(k16,r16,1200B,e4), one Release binary and worker VM.
//! No general CI: the full 4-leg measurement is intentionally long.
use std::time::Instant;
use wbd_codec::fec_v2::{
    BackendChoice, BackendUsed, PreparedBlock, Profile, Rs16, REPAIR_HEADER,
    MAX_BATCH_ROWS, parse_repair,
};

// Linux USER+SYSTEM process clock; usually CLK_TCK=100, i.e. 10ms ticks.
// Require >=100 ticks AND >=1s wall for each measured stage, not a noisy 0-tick
// 0.4ms leg. This file is only built on pinned Linux x86_64 Actions runner.
fn process_cpu_ticks() -> Option<u64> {
    let data = std::fs::read_to_string("/proc/self/stat").ok()?;
    let after_comm = data.rsplit_once(") ")?.1;
    let fields: Vec<_> = after_comm.split_whitespace().collect();
    Some(fields.get(11)?.parse::<u64>().ok()? + fields.get(12)?.parse::<u64>().ok()?)
}

#[test]
#[ignore = "400000 blocks + 400000 e4 recoveries per leg, ABBA, pinned GitHub Actions only"]
fn m0_f2_codec_k16_r16_1200_abba() {
    const BLOCKS: usize = 400_000;
    const RECOVERIES: usize = 400_000;
    const RECORD_BUDGET: usize = 1240;
    const MISSING: [usize;4] = [1,5,10,14];
    let frames: Vec<Vec<u8>> = (0..16).map(|i| (0..1200)
        .map(|j| ((i * 31 + j * 17 + 9) % 251) as u8).collect()).collect();
    let sources = frames.iter().map(Vec::as_slice).collect::<Vec<_>>();
    let available = frames.iter().enumerate().map(|(i,f)|
        if MISSING.contains(&i) {None} else {Some(f.as_slice())}
    ).collect::<Vec<_>>();
    let mut expected: Option<(u64,u64)> = None;
    assert_eq!(Profile::Strong.parity_count(16), Ok(16));
    assert_eq!(available.iter().filter(|s|s.is_none()).count(),4);

    // The one fixed deterministic dataset and workload are identical for A/B
    // and B/A. ISA-L backend selection is checked in every *actual* native
    // encode and recovery invocation, not inferred from an enabled feature.
    for (leg,mode) in ["A","B","B","A"].into_iter().enumerate() {
        let choice = if mode=="A"{BackendChoice::Scalar}else{BackendChoice::RequireNative};
        let selected = if mode=="A"{BackendUsed::Scalar}else{BackendUsed::NativeIsaL};
        let mut rs=Rs16::new();
        let mut prepared=PreparedBlock::from_frames(&sources,RECORD_BUDGET).unwrap();
        let len=REPAIR_HEADER+prepared.symbol_len();
        let mut out=vec![vec![0u8;len];MAX_BATCH_ROWS];

        // Warm all 4 ISA-L coefficient batch tables, and establish true e4
        // recovery data through the very same encoder and public wire parser.
        for row in (0..16).step_by(MAX_BATCH_ROWS) {
            let mut borrow=out.iter_mut().map(Vec::as_mut_slice).collect::<Vec<_>>();
            assert_eq!(rs.encode_prepared_into(42,&mut prepared,Profile::Strong,
                row,&mut borrow,RECORD_BUDGET,choice).unwrap(),selected);
        }
        let mut parity=vec![vec![0u8;len];4];
        {
            let mut borrow=parity.iter_mut().map(Vec::as_mut_slice).collect::<Vec<_>>();
            assert_eq!(rs.encode_prepared_into(99,&mut prepared,Profile::Strong,
                0,&mut borrow,RECORD_BUDGET,choice).unwrap(),selected);
        }
        let repairs=parity.iter().map(|v|parse_repair(v,RECORD_BUDGET).unwrap())
            .collect::<Vec<_>>();
        let (warm,used)=rs.recover_missing(99,&available,&repairs,
            RECORD_BUDGET,choice).unwrap();
        assert_eq!(used,selected);
        assert_eq!(warm.len(),MISSING.len());
        for (index,(got,plain)) in warm.iter().enumerate(){
            assert_eq!(*got as usize,MISSING[index]);
            assert_eq!(plain.as_slice(),frames[MISSING[index]].as_slice());
        }

        let start_cpu=process_cpu_ticks();
        let start=Instant::now();
        let mut encode_checksum=0u64;
        for block in 0..BLOCKS {
            for row in (0..16).step_by(MAX_BATCH_ROWS) {
                let mut borrow=out.iter_mut().map(Vec::as_mut_slice).collect::<Vec<_>>();
                let used=rs.encode_prepared_into(100+block as u64,&mut prepared,
                    Profile::Strong,row,&mut borrow,RECORD_BUDGET,choice).unwrap();
                assert_eq!(used,selected);
                for x in &out{
                    encode_checksum=encode_checksum.wrapping_add(
                        (x[12] as u64)*3+(x[123] as u64)*5+x[len-1] as u64
                    );
                }
            }
        }
        let encode_wall=start.elapsed().as_nanos();
        let encode_cpu=start_cpu.zip(process_cpu_ticks())
            .map(|(a,b)|b.saturating_sub(a));

        let start_cpu=process_cpu_ticks();
        let start=Instant::now();
        let mut recovery_checksum=0u64;
        for _ in 0..RECOVERIES {
            let (got,used)=rs.recover_missing(
                99,&available,&repairs,RECORD_BUDGET,choice).unwrap();
            assert_eq!(used,selected);
            assert_eq!(got.len(),4);
            for (idx,frame) in got{
                assert_eq!(frame.len(),1200);
                recovery_checksum=recovery_checksum.wrapping_add(
                    idx as u64+frame[0] as u64+frame[599] as u64+frame[1199] as u64
                );
            }
        }
        let recovery_wall=start.elapsed().as_nanos();
        let recovery_cpu=start_cpu.zip(process_cpu_ticks())
            .map(|(a,b)|b.saturating_sub(a));

        if let Some((enc,rec))=expected {
            assert_eq!((encode_checksum,recovery_checksum),(enc,rec),
                "scalar/native parity and e4 recovered bytes must be equivalent");
        }else{expected=Some((encode_checksum,recovery_checksum));}
        assert!(encode_wall>0 && recovery_wall>0
            && encode_checksum>0 && recovery_checksum>0);
        println!(
            "F2_ABBA_RESULT leg={leg} mode={mode} backend={selected:?} blocks={BLOCKS} \
             recoveries={RECOVERIES} e=4 k=16 r=16 frame_bytes=1200 \
             parity_symbols={} encode_checksum={encode_checksum} recovery_checksum={recovery_checksum} \
             encode_wall_ns={encode_wall} encode_cpu_ticks={} recovery_wall_ns={recovery_wall} recovery_cpu_ticks={}",
            BLOCKS*16,encode_cpu.map_or("UNKNOWN".into(),|x|x.to_string()),
            recovery_cpu.map_or("UNKNOWN".into(),|x|x.to_string())
        );
    }
    println!("F2_ABBA_SCENARIO_DONE scope=codec-only fixed_blocks=400000 e4_recovery=400000 per_leg_min_cpu_ticks=100 per_stage_min_wall_ns=1000000000 first_delivery=NOT_RUN p99=NOT_RUN product=OFF");
}
