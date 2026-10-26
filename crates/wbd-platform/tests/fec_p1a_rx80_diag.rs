//! W139: opt-in, bounded Linux ARM64 RX syscall-only microbenchmark.
//! NOT a Game/Normal product, FEC, AEAD, TUN, 80Mbps product qualification.
//! Existing platform recvmmsg implementation, exact 4-slot P1a contract.
//! 64B UDP payload at 80Mbps -> 156250 attempted packets/sec, one socket
//! and one sender thread; four sequential legs ABBA, never concurrent A/B.
#![cfg(all(target_os = "linux", target_arch = "aarch64"))]
use std::io::ErrorKind;
use std::net::UdpSocket;
use std::os::fd::AsRawFd;
use std::sync::{Arc,atomic::{AtomicBool,Ordering}};
use std::thread;
use std::time::{Duration,Instant};
use wbd_platform::linux_rx_batch::{receive_ready_udp,RxStatus};
use wbd_platform::r1::BorrowFence;

const APP_BITS_PER_SECOND:u64=80_000_000;
const BODY_BYTES:u64=64;
const TEST_SECONDS:u64=2;
const TARGET:u64=APP_BITS_PER_SECOND/8/BODY_BYTES*TEST_SECONDS;
const BURST:u64=16;
const STOP_GRACE_MS:u64=250;
#[repr(C)]
struct Timespec{seconds:i64,nanos:i64}
#[repr(C)]
struct PollFd{fd:i32,events:i16,revents:i16}
unsafe extern "C" {
    fn clock_gettime(clock_id:i32,tp:*mut Timespec)->i32;
    fn poll(fds:*mut PollFd,nfds:usize,timeout:i32)->i32;
    fn setsockopt(fd:i32,level:i32,name:i32,ptr:*const u8,len:u32)->i32;
}
fn thread_cpu_ns()->u64{
    let mut time=Timespec{seconds:0,nanos:0};
    // CLOCK_THREAD_CPUTIME_ID=3 on Linux. No payload/key observation.
    let rc=unsafe{clock_gettime(3,&mut time)};
    assert_eq!(rc,0);
    time.seconds as u64*1_000_000_000+time.nanos as u64
}
fn host_psi_avg10()->Option<f64>{
    let s=std::fs::read_to_string("/proc/pressure/cpu").ok()?;
    let some=s.lines().find(|x|x.starts_with("some "))?;
    some.split_whitespace().find_map(|f|
        f.strip_prefix("avg10=").and_then(|v|v.parse::<f64>().ok()))
}
#[derive(Clone,Copy,Debug)]
enum Mode{OneRecvfrom,FourRecvmmsg}
struct Receipt{
    mode:Mode,attempted:u64,received:u64,
    recv_calls:u64,full_four:u64,poll_calls:u64,
    elapsed_s:f64,recv_thread_cpu_s:f64,
    offered_payload_mbps:f64,delivered_pps:f64,psi_after:f64
}
fn run(mode:Mode)->Receipt{
    let rx=UdpSocket::bind("127.0.0.1:0").expect("bind RX");
    let tx=UdpSocket::bind("127.0.0.1:0").expect("bind TX");
    tx.connect(rx.local_addr().expect("RX addr")).expect("connect TX");
    rx.set_nonblocking(true).expect("nonblocking receiver");
    let buf_bytes:i32=4*1024*1024;
    let _=unsafe{setsockopt(rx.as_raw_fd(),1,8,
        (&buf_bytes as *const i32).cast(),4)};
    let done=Arc::new(AtomicBool::new(false));
    let done_tx=Arc::clone(&done);
    let sender=thread::spawn(move||{
        let payload=[0x5Au8;BODY_BYTES as usize];
        let t0=Instant::now();
        let mut sent=0u64;
        for index in 0..TARGET {
            if index%BURST==0 {
                let due=t0+Duration::from_nanos(
                    ((index as u128*BODY_BYTES as u128*8*1_000_000_000u128)
                     /APP_BITS_PER_SECOND as u128) as u64);
                while let Some(remaining)=due.checked_duration_since(Instant::now()){
                    if remaining>Duration::from_micros(90){
                        thread::sleep(remaining-Duration::from_micros(35));
                    }else{std::hint::spin_loop();}
                }
            }
            match tx.send(&payload){
                Ok(n) if n==BODY_BYTES as usize=>sent+=1,
                Ok(_)=>break,
                Err(e) if e.kind()==ErrorKind::Interrupted=>continue,
                Err(_)=>break
            }
        }
        let elapsed=t0.elapsed().as_secs_f64();
        done_tx.store(true,Ordering::Release);
        (sent,elapsed)
    });
    let mut single=[0u8;BODY_BYTES as usize];
    let mut bulk=[[0u8;BODY_BYTES as usize];4];
    let fence=BorrowFence::default();
    let mut received=0u64;
    let mut calls=0u64;
    let mut full_four=0u64;
    let mut polls=0u64;
    let mut deadline:Option<Instant>=None;
    let t0=Instant::now();
    let cpu0=thread_cpu_ns();
    loop {
        let n=match mode{
            Mode::OneRecvfrom=>{
                calls+=1;
                match rx.recv(&mut single){
                    Ok(n) if n==BODY_BYTES as usize=>1,
                    Ok(_)=>0,
                    Err(e) if e.kind()==ErrorKind::WouldBlock=>0,
                    Err(e) if e.kind()==ErrorKind::Interrupted=>0,
                    Err(e)=>panic!("old native recv failure: {e}")
                }
            }
            Mode::FourRecvmmsg=>{
                calls+=1;
                let [a,b,c,d]=&mut bulk;
                let mut slots:[&mut [u8];4]=[
                    &mut a[..],&mut b[..],&mut c[..],&mut d[..]];
                let result=receive_ready_udp(&rx,&mut slots,&fence);
                match result.status{
                    RxStatus::InvalidBuffers|RxStatus::IoUncertain|RxStatus::Stopping=>
                        panic!("native batch failure: {:?}",result.status),
                    _=>{}
                }
                let valid=(0..result.received).filter(|i|
                    matches!(result.entry(*i),
                        Some(wbd_platform::linux_rx_batch::RxEntry::Complete{len})
                            if len==BODY_BYTES as usize)).count() as u64;
                if result.received==4{full_four+=1;}
                valid
            }
        };
        received+=n;
        if n==0 {
            polls+=1;
            let mut fd=PollFd{fd:rx.as_raw_fd(),events:1,revents:0};
            let _=unsafe{poll(&mut fd,1,1)};
        }
        if done.load(Ordering::Acquire){
            let end=deadline.get_or_insert_with(||
                Instant::now()+Duration::from_millis(STOP_GRACE_MS));
            if Instant::now()>=*end{break}
        }
        if t0.elapsed()>Duration::from_secs(TEST_SECONDS+5){
            panic!("bounded 80Mbps benchmark exceeded 7 seconds");
        }
    }
    let cpu=(thread_cpu_ns()-cpu0) as f64/1e9;
    let wall=t0.elapsed().as_secs_f64();
    let (sent,sender_time)=sender.join().expect("sender join");
    Receipt{
        mode,attempted:sent,received,recv_calls:calls,full_four,poll_calls:polls,
        elapsed_s:wall,recv_thread_cpu_s:cpu,
        offered_payload_mbps:sent as f64*BODY_BYTES as f64*8.0/sender_time/1e6,
        delivered_pps:received as f64/wall,
        psi_after:host_psi_avg10().unwrap_or(-1.0)
    }
}
#[test]
#[ignore="intentionally triggered once by independent ARM64 diagnostic Action"]
fn w139_p1a_native_recvfrom_vs_recvmmsg_80mbps(){
    let psi=host_psi_avg10().unwrap_or(-1.0);
    if psi>=20.0{
        println!("W139_CAPACITY_STOP preflight_cpu_psi_avg10_pct={psi:.3} (NO_BENCHMARK)");
        return
    }
    println!("W139_METADATA kernel_rx_only=1 product_game_fec_qualified=0 body_bytes=64 target_payload_mbps=80 target_pps=156250 order=ABBA");
    let mut records=Vec::new();
    for mode in [Mode::OneRecvfrom,Mode::FourRecvmmsg,Mode::FourRecvmmsg,Mode::OneRecvfrom]{
        let r=run(mode);
        println!("W139_RX mode={:?} tx_packets={} rx_packets={} missing={} syscall_attempts={} full_four_calls={} idle_polls={} rx_thread_cpu_s={:.6} wall_s={:.6} offered_payload_mbps={:.4} delivered_pps={:.3} host_cpu_psi_avg10_pct={:.4}",
            r.mode,r.attempted,r.received,
            r.attempted.saturating_sub(r.received),r.recv_calls,r.full_four,
            r.poll_calls,r.recv_thread_cpu_s,r.elapsed_s,
            r.offered_payload_mbps,r.delivered_pps,r.psi_after);
        assert!(r.attempted>0 && r.received>0);
        records.push(r);
        if records.last().is_some_and(|r|r.psi_after>=20.0){
            println!("W139_CAPACITY_STOP host_pressure_after_leg, no further legs");
            break
        }
    }
    if records.len()==4 {
        let a=(records[0].recv_thread_cpu_s+records[3].recv_thread_cpu_s)/2.0;
        let b=(records[1].recv_thread_cpu_s+records[2].recv_thread_cpu_s)/2.0;
        let coverage=records.iter().all(|r|
            r.attempted>0 &&
            r.received as f64/r.attempted as f64>=0.98 &&
            (76.0..=84.0).contains(&r.offered_payload_mbps));
        println!("W139_SUMMARY old_recvfrom_cpu_s_mean={a:.6} four_recvmmsg_cpu_s_mean={b:.6} rx_cpu_delta_pct={:.3} strict_input_and_delivery_qualified={} native_only=true game_product_80mbps=NOT_RUN",
            (b/a-1.0)*100.0,coverage);
    }else{
        println!("W139_SUMMARY comparison=NOT_QUALIFIED_CAPACITY_STOP");
    }
}
