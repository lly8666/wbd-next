//! M1 R1-M1-READY-GENERATION-RELEASE-008.
 //! Test-only Release executable built and executed once from worker native
 //! test consumer. NEVER a production throughput or authenticated-go benchmark.
 #![forbid(unsafe_code)]
 use super::generation::{ScopedOwner,ScopeToken,ScopeError,ScopedOfferError,LoanBatch};
 use super::{TxOwner,RxOwner,TxDispatch,RxPacket,QueueLimits,TxKind};
 use crate::memory::{Arena,UniqueBuffer,FrozenRecord};
 use wbd_types::{MonoNs,LaneKey,TunnelKey,RecordPn,SeqOffset};
 use wbd_types::buffer_contract::{FrozenMetadata,FrozenRecordHandle,UniqueSealable};

 fn lane(g:u32)->LaneKey {
     LaneKey{tunnel:TunnelKey{slot:133,generation:g},slot:7,generation:g}
 }
 fn limits()->QueueLimits {
     QueueLimits{slots:64,bytes:64,max_age_ns:1_000_000_000}
 }
 fn pair()->(TxOwner,RxOwner){
     (TxOwner::new(limits(),limits()).unwrap(),RxOwner::new(limits()).unwrap())
 }
 fn owner()->ScopedOwner{
     let (tx,rx)=pair();
     ScopedOwner::new(808,1,lane(1),tx,rx).unwrap()
 }
 fn arena()->Arena{Arena::new(160,96,256,1,100_000).unwrap()}
 fn frozen(a:&mut Arena,v:u8,gen:u32)->FrozenRecord{
     let mut b=a.allocate().unwrap();
     b.writable()[0]=v;
     b.freeze(0..1,FrozenMetadata{
         lane:lane(gen),pn:RecordPn(v as u64),seq:SeqOffset(v as u64),
         carrier_snapshot:7
     }).unwrap()
 }
 fn rx_buffer(a:&mut Arena,v:u8)->UniqueBuffer{
     let mut b=a.allocate().unwrap();b.writable()[0]=v;b
 }
 fn take<T>(result:Result<LoanBatch<T>,(ScopeError,Vec<T>)>)->LoanBatch<T>{
     result.unwrap_or_else(|_|panic!("current owner ready batch failed"))
 }
 fn rotate(s:&mut ScopedOwner,t:&ScopeToken){
     let (tx,rx)=pair();
     s.rotate(t,lane(2),tx,rx).unwrap_or_else(|_|panic!("rotation failed"));
 }

 #[test]
 fn r1_owner_release_ready_0_1_32_33_tx_rx_two_lanes() {
     let mut a=arena();let mut s=owner();let old=s.token();
     let tx=take(s.drain_tx(&old,MonoNs(0),Vec::with_capacity(32)));
     let rx=take(s.drain_rx(&old,MonoNs(0),Vec::with_capacity(32)));
     assert_eq!((tx.len(),rx.len()),(0,0));
     let txslots=tx.recycle();let rxslots=rx.recycle();
     s.offer_fresh(&old,frozen(&mut a,1,1),MonoNs(0)).unwrap();
     s.offer_rx(&old,rx_buffer(&mut a,2),0..1,MonoNs(0)).unwrap();
     let one_tx=take(s.drain_tx(&old,MonoNs(0),txslots));
     let one_rx=take(s.drain_rx(&old,MonoNs(0),rxslots));
     assert_eq!(s.checked_tx_ready(&old,&one_tx).unwrap().len(),1);
     assert_eq!(s.checked_rx_ready(&old,&one_rx).unwrap().len(),1);
     rotate(&mut s,&old);
     let current=s.token();
     assert_eq!(s.checked_tx_ready(&current,&one_tx).err(),Some(ScopeError::Stale));
     assert_eq!(s.checked_rx_ready(&current,&one_rx).err(),Some(ScopeError::Stale));
     drop(one_tx);drop(one_rx);
     for i in 0..33u8 {
         s.offer_fresh(&current,frozen(&mut a,i,2),MonoNs(1)).unwrap();
         s.offer_rx(&current,rx_buffer(&mut a,i),0..1,MonoNs(1)).unwrap();
     }
     let tx32=take(s.drain_tx(&current,MonoNs(1),Vec::with_capacity(32)));
     let rx32=take(s.drain_rx(&current,MonoNs(1),Vec::with_capacity(32)));
     let tx1=take(s.drain_tx(&current,MonoNs(1),Vec::with_capacity(32)));
     let rx1=take(s.drain_rx(&current,MonoNs(1),Vec::with_capacity(32)));
     assert_eq!((tx32.len(),tx1.len(),rx32.len(),rx1.len()),(32,1,32,1));
     assert_eq!(s.checked_tx_ready(&current,&tx32).unwrap()[0].record.bytes(),&[0]);
     assert_eq!(s.checked_tx_ready(&current,&tx1).unwrap()[0].record.bytes(),&[32]);
     assert_eq!(s.checked_rx_ready(&current,&rx32).unwrap().len(),32);
     assert_eq!(s.checked_rx_ready(&current,&rx1).unwrap().len(),1);
     drop(tx32);drop(tx1);drop(rx32);drop(rx1);
     assert_eq!(a.report().loaned,0);
 }
 #[test]
 fn r1_owner_release_fresh_first_stale_stop_aba_no_resubmission() {
     let mut a=arena();let mut s=owner();let old=s.token();
     let held=frozen(&mut a,9,1);
     let copy=held.clone();
     s.offer_fresh(&old,held,MonoNs(0)).unwrap();
     let retired={let(tx,rx)=pair();s.rotate(&old,lane(2),tx,rx)
         .unwrap_or_else(|_|panic!("rotation failed"))};
     assert_eq!(retired.canceled,1);
     let current=s.token();
     let bad=s.offer_fresh(&old,copy.clone(),MonoNs(0));
     assert!(matches!(bad,Err((ScopedOfferError::Scope(ScopeError::Stale),_))));
     drop(bad);
     let bad=s.offer_repair(&current,copy,MonoNs(0));
     assert!(matches!(bad,Err((ScopedOfferError::Scope(ScopeError::LaneMismatch),_))));
     drop(bad);
     s.offer_repair(&current,frozen(&mut a,10,2),MonoNs(0)).unwrap();
     s.offer_fresh(&current,frozen(&mut a,11,2),MonoNs(0)).unwrap();
     let batch=take(s.drain_tx(&current,MonoNs(0),Vec::with_capacity(2)));
     let ready=s.checked_tx_ready(&current,&batch).unwrap();
     assert_eq!((ready[0].kind,ready[1].kind),(TxKind::Fresh,TxKind::Repair));
     let closing=s.stop(&current).unwrap();
     assert_eq!(s.checked_tx_ready(&current,&batch).err(),Some(ScopeError::Stopped));
     drop(batch);
     assert!(closing.batch_handles_released());
     assert_eq!(a.report().loaned,0);
     let restarted=owner();let again=restarted.token();
     assert_eq!(again.serial(),old.serial());
     assert_eq!(again.owner_id(),old.owner_id());
     assert_eq!(restarted.checked_tx_ready(&old,&take_empty_tx()).err(),Some(ScopeError::Stale));
 }
 fn take_empty_tx()->LoanBatch<TxDispatch> {
     let mut s=owner();let t=s.token();
     take(s.drain_tx(&t,MonoNs(0),Vec::with_capacity(1)))
 }
 #[test]
 fn r1_owner_release_old_batch_held_stop_new_scope_stale_after_32() {
     let mut a=arena();let mut s=owner();let old=s.token();
     for i in 0..32u8 {
         s.offer_fresh(&old,frozen(&mut a,i,1),MonoNs(0)).unwrap();
         s.offer_rx(&old,rx_buffer(&mut a,i),0..1,MonoNs(0)).unwrap();
     }
     let old_tx=take(s.drain_tx(&old,MonoNs(0),Vec::with_capacity(32)));
     let old_rx=take(s.drain_rx(&old,MonoNs(0),Vec::with_capacity(32)));
     let (tx,rx)=pair();
     let retired=s.rotate(&old,lane(2),tx,rx)
         .unwrap_or_else(|_|panic!("rotation failed"));
     let current=s.token();
     assert_eq!(s.checked_tx_ready(&current,&old_tx).err(),Some(ScopeError::Stale));
     assert_eq!(s.checked_rx_ready(&current,&old_rx).err(),Some(ScopeError::Stale));
     s.offer_fresh(&current,frozen(&mut a,80,2),MonoNs(0)).unwrap();
     let live=take(s.drain_tx(&current,MonoNs(0),Vec::with_capacity(32)));
     assert_eq!(s.checked_tx_ready(&current,&live).unwrap()[0].record.bytes(),&[80]);
     let stopper=s.stop(&current).unwrap();
     assert_eq!(s.checked_tx_ready(&current,&live).err(),Some(ScopeError::Stopped));
     let old_join=std::thread::spawn(move||{drop(old_tx);drop(old_rx);});
     drop(live);
     old_join.join().unwrap();
     assert!(retired.batch_handles_released());
     assert!(stopper.batch_handles_released());
     assert_eq!(a.report().loaned,0);
 }

 // Compiled only into the hosted worker DEBUG test binary. A distinct
 // release-mode native test executable is built ONCE from the exact checkout,
 // sha256-attested and executed once. No root workflow changes.
 #[cfg(debug_assertions)]
 #[test]
 fn r1_owner_release_compiled_once_hosted_cpu_latency_provenance() {
     use std::{process::Command,path::PathBuf};
     if std::env::var("GITHUB_ACTIONS").ok().as_deref()!=Some("true") {
         println!("M1_OWNER_RELEASE_NOT_RUN local run; no hosted SOURCE provenance");
         return;
     }
     let source=std::env::var("GITHUB_SHA").expect("GitHub SOURCE required");
     let run=std::env::var("GITHUB_RUN_ID").expect("GitHub run id required");
     assert_eq!(source.len(),40);
     let dir=PathBuf::from(env!("CARGO_MANIFEST_DIR"));
     let build=Command::new("cargo")
         .args(["test","--release","--locked","--offline",
             "-p","wbd-engine","--lib","--no-run"])
         .current_dir(&dir).output().expect("cargo release build should run");
     if !build.status.success(){
         panic!("release compilation failed: {}",String::from_utf8_lossy(&build.stderr));
     }
     let release_dir=dir.join("../../target/release/deps");
     let bins:Vec<_>=std::fs::read_dir(&release_dir).expect("release output missing")
         .filter_map(Result::ok)
         .filter(|entry|{
             let name=entry.file_name().to_string_lossy().into_owned();
             name.starts_with("wbd_engine-") && !name.contains('.')
               && entry.path().is_file()
         }).collect();
     assert_eq!(bins.len(),1,"must select exactly one release native test binary");
     let path=bins[0].path();
     let checksum=Command::new("sha256sum").arg(&path)
         .output().expect("linux sha256sum");
     assert!(checksum.status.success());
     let digest=String::from_utf8(checksum.stdout).expect("utf8 hash")
         .split_whitespace().next().expect("digest").to_owned();
     assert_eq!(digest.len(),64);
     let runner=std::env::var("RUNNER_NAME").unwrap_or_else(|_|"unknown".into());
     println!("M1_OWNER_RELEASE_BUILD source_sha={} run_id={} binary_sha256={} compiler=cargo-release-locked-offline binary_count=1 runner={}",
         source,run,digest,runner);
     let executed=Command::new(&path)
         .args(["--ignored","--nocapture",
            "r1_owner_release_component_actual_dispatch_repeats"])
         .current_dir(&dir).output().expect("run release benchmark");
     let out=String::from_utf8_lossy(&executed.stdout);
     let err=String::from_utf8_lossy(&executed.stderr);
     // The outer worker-native parser must see ONLY outer r1_ test names
     // and its own final test count; never leak nested Rust test markers.
     for line in out.lines().filter(|line|line.contains("M1_OWNER_RELEASE_SAMPLE ")) {
         println!("{}",line);
     }
     if !executed.status.success(){panic!("release binary failed: {} {}",out,err);}
     assert_eq!(out.matches("M1_OWNER_RELEASE_SAMPLE ").count(),3);
     assert!(out.contains("test result: ok. 1 passed; 0 failed"));
 }
 #[cfg(not(debug_assertions))]
 fn cpu_ticks()->Option<(u64,u64)> {
     let text=std::fs::read_to_string("/proc/self/stat").ok()?;
     let suffix=text.rsplit_once(')')?.1;
     let p:Vec<_>=suffix.split_whitespace().collect();
     Some((p.get(11)?.parse().ok()?,p.get(12)?.parse().ok()?))
 }
 #[cfg(not(debug_assertions))]
 fn clock_hz()->Option<u64>{
     let out=std::process::Command::new("getconf").arg("CLK_TCK").output().ok()?;
     if !out.status.success(){return None;}
     std::str::from_utf8(&out.stdout).ok()?.trim().parse().ok()
 }
 #[cfg(not(debug_assertions))]
 fn quantile(mut points:Vec<u64>,ratio:usize)->u64{
     points.sort_unstable();
     points[(points.len()*ratio/100).min(points.len()-1)]
 }
 // Compiled ONLY into the independent release-mode Rust native binary.
 // Process CPU elapsed measured over >=1s of real generation ready batches.
 // It contains arena fill/freeze setup and empty batch reuse each iteration;
 // the per-batch latency excludes these setup costs.
 #[cfg(not(debug_assertions))]
 #[test]
 #[ignore="run only from attested native SOURCE wrapper"]
 fn r1_owner_release_component_actual_dispatch_repeats() {
     use std::time::{Instant,Duration};
     let source=std::env::var("GITHUB_SHA").expect("exact source");
     let run=std::env::var("GITHUB_RUN_ID").expect("run id");
     let runner=std::env::var("RUNNER_NAME").unwrap_or_else(|_|"unknown".into())
         .replace('"',"_");
     let hz=clock_hz().expect("Linux process CPU HZ");
     assert!(hz>0);
     let mut a=arena();let mut s=owner();let old=s.token();
     s.offer_fresh(&old,frozen(&mut a,200,1),MonoNs(0)).unwrap();
     s.offer_rx(&old,rx_buffer(&mut a,201),0..1,MonoNs(0)).unwrap();
     let stale_tx=take(s.drain_tx(&old,MonoNs(0),Vec::with_capacity(32)));
     let stale_rx=take(s.drain_rx(&old,MonoNs(0),Vec::with_capacity(32)));
     let (tx,rx)=pair();let retired=s.rotate(&old,lane(2),tx,rx)
         .unwrap_or_else(|_|panic!("rotation"));
     let current=s.token();
     let mut txstorage=Vec::with_capacity(32);
     let mut rxstorage=Vec::with_capacity(32);
     let mut tx_lat=Vec::with_capacity(40000);
     let mut rx_lat=Vec::with_capacity(40000);
     let mut reject_lat=Vec::with_capacity(40000);
     for leg in 0..3 {
         const WARM:usize=512;
         for iteration in 0..WARM {
             for i in 0..32u8 {
                 s.offer_fresh(&current,frozen(&mut a,i,2),MonoNs(iteration as u64)).unwrap();
                 s.offer_rx(&current,rx_buffer(&mut a,i),0..1,MonoNs(iteration as u64)).unwrap();
             }
             let tx=take(s.drain_tx(&current,MonoNs(iteration as u64),txstorage));
             let rx=take(s.drain_rx(&current,MonoNs(iteration as u64),rxstorage));
             assert_eq!(s.checked_tx_ready(&current,&tx).unwrap().len(),32);
             assert_eq!(s.checked_rx_ready(&current,&rx).unwrap().len(),32);
             txstorage=tx.recycle();rxstorage=rx.recycle();
             a.drain_returns();
         }
         tx_lat.clear();rx_lat.clear();reject_lat.clear();
         let before=cpu_ticks().expect("Linux proc cpu ticks");
         let begin=Instant::now();
         let mut rounds=0usize;
         let mut sent=0u64;
         let mut received=0u64;
         while begin.elapsed()<Duration::from_millis(1100) {
             for i in 0..32u8 {
                 s.offer_fresh(&current,frozen(&mut a,i,2),MonoNs(0)).unwrap();
                 s.offer_rx(&current,rx_buffer(&mut a,i),0..1,MonoNs(0)).unwrap();
             }
             let ptx=txstorage.as_ptr();let prx=rxstorage.as_ptr();
             let start=Instant::now();
             let tx=take(s.drain_tx(&current,MonoNs(0),txstorage));
             let tx_ns=start.elapsed().as_nanos() as u64;
             let start=Instant::now();
             let rx=take(s.drain_rx(&current,MonoNs(0),rxstorage));
             let rx_ns=start.elapsed().as_nanos() as u64;
             assert_eq!(tx.as_slice().as_ptr(),ptx);
             assert_eq!(rx.as_slice().as_ptr(),prx);
             assert_eq!(s.checked_tx_ready(&current,&tx).unwrap().len(),32);
             assert_eq!(s.checked_rx_ready(&current,&rx).unwrap().len(),32);
             let start=Instant::now();
             assert_eq!(s.checked_tx_ready(&current,&stale_tx).err(),Some(ScopeError::Stale));
             assert_eq!(s.checked_rx_ready(&current,&stale_rx).err(),Some(ScopeError::Stale));
             let stale_ns=start.elapsed().as_nanos() as u64;
             if tx_lat.len()<40000 {
                 tx_lat.push(tx_ns);rx_lat.push(rx_ns);reject_lat.push(stale_ns);
             }else {
                 let index=rounds%40000;
                 tx_lat[index]=tx_ns;rx_lat[index]=rx_ns;reject_lat[index]=stale_ns;
             }
             txstorage=tx.recycle();rxstorage=rx.recycle();
             a.drain_returns();
             rounds+=1;
             sent+=32;received+=32;
         }
         let wall=begin.elapsed();
         let after=cpu_ticks().expect("cpu ticks after");
         assert!(wall>=Duration::from_secs(1));
         let cpu_ticks=after.0.saturating_sub(before.0)+
                       after.1.saturating_sub(before.1);
         let cpu_s=cpu_ticks as f64/hz as f64;
         assert!(rounds>100);
         assert_eq!(s.checked_tx_ready(&current,&stale_tx).err(),Some(ScopeError::Stale));
         assert_eq!(a.report().loaned,2,"retired old loans must remain");
         let tp50=quantile(tx_lat.clone(),50);let tp99=quantile(tx_lat.clone(),99);
         let rp50=quantile(rx_lat.clone(),50);let rp99=quantile(rx_lat.clone(),99);
         let sp50=quantile(reject_lat.clone(),50);let sp99=quantile(reject_lat.clone(),99);
         println!("M1_OWNER_RELEASE_SAMPLE {{\"schema\":1,\"source_sha\":\"{}\",\"run_id\":\"{}\",\"runner\":\"{}\",\"leg\":{},\"warmup_rounds\":{},\"rounds\":{},\"tx_ready_records\":{},\"rx_ready_records\":{},\"max_batch\":32,\"wall_s\":{:.6},\"cpu_s\":{:.6},\"cpu_hz\":{},\"tx_actual_ready_p50_ns\":{},\"tx_actual_ready_p99_ns\":{},\"rx_actual_ready_p50_ns\":{},\"rx_actual_ready_p99_ns\":{},\"stale_reject_p50_ns\":{},\"stale_reject_p99_ns\":{},\"quantile_sample_count\":{},\"profile\":\"release\",\"measurement_scope\":\"owner_actual_ready_tx_rx_plus_stale_reject_only\",\"cpu_process_scope\":\"unisolated_single_process_total\",\"product\":\"NOT_RUN\"}}",
             source,run,runner,leg,WARM,rounds,sent,received,wall.as_secs_f64(),cpu_s,hz,
             tp50,tp99,rp50,rp99,sp50,sp99,tx_lat.len());
     }
     drop(stale_tx);drop(stale_rx);
     assert!(retired.batch_handles_released());
     assert_eq!(a.report().loaned,0);
 }
