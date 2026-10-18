//! M0 isolated Actions-only FEC2 kernel cost fixture. This is NOT product code.
use std::time::Instant;
use wbd_codec::fec_v2::{BackendChoice, BackendUsed, PreparedBlock, Profile, Rs16, REPAIR_HEADER, MAX_BATCH_ROWS};

fn process_cpu_ticks() -> Option<u64> {
    let data = std::fs::read_to_string("/proc/self/stat").ok()?;
    let after_comm = data.rsplit_once(") ")?.1;
    let fields: Vec<_> = after_comm.split_whitespace().collect();
    Some(fields.get(11)?.parse::<u64>().ok()? + fields.get(12)?.parse::<u64>().ok()?)
}

#[test]
#[ignore = "One fixed k16/r16 1200B ABBA same-VM Actions scenario; not run in general regression"]
fn m0_f2_codec_k16_r16_1200_abba() {
    let frames: Vec<Vec<u8>> = (0..16).map(|i| (0..1200)
        .map(|j| ((i * 31 + j * 17 + 9) % 251) as u8).collect()).collect();
    let sources = frames.iter().map(Vec::as_slice).collect::<Vec<_>>();
    let rs = Rs16::new();
    assert_eq!(Profile::Strong.parity_count(16), Ok(16));
    let mut baseline_checksum: Option<u64> = None;
    // This is one scenario, same worker VM/process: A -> B -> B -> A.
    // Warm each leg's native table in the same way before timing.
    for (leg, mode) in ["A", "B", "B", "A"].into_iter().enumerate() {
        let choice = if mode == "A" { BackendChoice::Scalar } else { BackendChoice::RequireNative };
        let expected = if mode == "A" { BackendUsed::Scalar } else { BackendUsed::NativeIsaL };
        let mut prepared = PreparedBlock::from_frames(&sources, 1240).unwrap();
        let length = REPAIR_HEADER + prepared.symbol_len();
        let mut out = vec![vec![0u8; length]; MAX_BATCH_ROWS];
        for row in (0..16).step_by(MAX_BATCH_ROWS) {
            let mut slices = out.iter_mut().map(Vec::as_mut_slice).collect::<Vec<_>>();
            assert_eq!(rs.encode_prepared_into(1, &mut prepared, Profile::Strong,
                row, &mut slices, 1240, choice).unwrap(), expected);
        }
        let mut checksum = 0u64;
        let cpu_start = process_cpu_ticks();
        let start = Instant::now();
        const BLOCKS: usize = 96;
        for block in 0..BLOCKS {
            for row in (0..16).step_by(MAX_BATCH_ROWS) {
                let mut slices = out.iter_mut().map(Vec::as_mut_slice).collect::<Vec<_>>();
                let used = rs.encode_prepared_into(10 + block as u64,
                    &mut prepared, Profile::Strong, row, &mut slices, 1240, choice).unwrap();
                assert_eq!(used, expected, "real native backend must be invoked for B");
                for x in &out {
                    checksum = checksum.wrapping_add((x[12] as u64) * 3
                        + (x[123] as u64) * 5 + x[length - 1] as u64);
                }
            }
        }
        let elapsed = start.elapsed().as_nanos();
        let cpu_end = process_cpu_ticks();
        let cpu_delta = cpu_start.zip(cpu_end).map(|(a,b)| b.saturating_sub(a));
        if let Some(before) = baseline_checksum { assert_eq!(checksum, before, "scalar/native payload mismatch"); }
        else { baseline_checksum = Some(checksum); }
        assert!(elapsed > 0 && checksum > 0);
        println!("F2_ABBA_RESULT leg={leg} mode={mode} backend={expected:?} blocks={BLOCKS} k=16 r=16 frame_bytes=1200 parity_symbols={} checksum={checksum} wall_ns={elapsed} cpu_ticks={}",
            BLOCKS * 16, cpu_delta.map_or(String::from("UNKNOWN"), |v| v.to_string()));
    }
    println!("F2_ABBA_SCENARIO_DONE scope=codec-only first_delivery=NOT_RUN p99=NOT_RUN product=OFF");
}
