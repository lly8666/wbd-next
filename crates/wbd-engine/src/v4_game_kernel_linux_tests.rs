//! M0 Linux-only ORIGINAL-Go-TLS Game2/4 authentic kernel-first-app test.
//! Isolated GitHub Actions network namespace ONLY. No test fixtures or cold
//! exporter keys are committed or included in an artifact. The original Go
//! credential-checked process emits ephemeral per-lane material immediately
//! before this binary runs in the same runner. This is not a public CLI grant.
#![allow(unsafe_code)]
use crate::cold_v4::UntrustedColdV4;
use crate::memory::Arena;
use crate::v4_game_lane::{Error,GameAdapter};
use std::ffi::{CString,c_char};
use std::fs::OpenOptions;
use std::net::UdpSocket;
use std::os::fd::{AsRawFd,OwnedFd};
use std::path::Path;
use std::process::Command;
use std::time::{Duration,Instant};
use wbd_types::{LogicalPacketId,MonoNs,RecordPn,SeqOffset,TunnelKey};
use wbd_types::buffer_contract::{FrozenMetadata,UniqueSealable};
use wbd_platform::ipv4_tcp::{Ipv4Tuple,PacketPersona,Presentation};
use wbd_platform::linux_raw_carrier::{ScopedRawIpv4Rx,ScopedRawIpv4Tx};
use wbd_platform::linux_tun_sink::ScopedTunSink;
use wbd_platform::r1::StopResult;

unsafe extern "C"{
    fn ioctl(fd:i32,request:usize,...) -> i32;
    fn if_nametoindex(name:*const c_char)->u32;
}
const TUNSETIFF:usize=0x400454ca;
fn tun_fd(name:&str)->OwnedFd{
    assert!(!name.is_empty()&&name.len()<16);
    let file=OpenOptions::new().read(true).write(true).open("/dev/net/tun")
        .expect("real Linux kernel TUN device");
    let mut ifreq=[0u8;40];
    ifreq[..name.len()].copy_from_slice(name.as_bytes());
    ifreq[16..18].copy_from_slice(&0x1001i16.to_ne_bytes()); // TUN|NO_PI
    let rc=unsafe{ioctl(file.as_raw_fd(),TUNSETIFF,ifreq.as_mut_ptr())};
    assert_eq!(rc,0,"actual TUNSETIFF ioctl must succeed");
    file.into()
}
fn ip(args:&[&str]){
    let result=Command::new("ip").args(args).status().expect("kernel iproute2");
    assert!(result.success(),"kernel ip failed: {:?}",args);
}
fn localhost_index()->u32{
    let name=CString::new("lo").unwrap();
    let idx=unsafe{if_nametoindex(name.as_ptr())};
    assert!(idx>0);idx
}
fn original_tls_cold(dir:&str,n:usize,side:&str)->Vec<UntrustedColdV4>{
    (1..=n).map(|lane|{
        let path=Path::new(dir).join(format!("game{n}-{side}-{lane}.cold"));
        UntrustedColdV4::parse(&std::fs::read(path)
            .expect("actual Go TLS independently authenticated private cold"))
            .expect("Go cold cannot bypass Rust grammar")
    }).collect()
}
fn original_udp_ipv4(port:u16,data:&[u8])->Vec<u8>{
    let len=20+8+data.len();
    assert!(len<=1200);
    let mut packet=vec![0u8;len];
    packet[0]=0x45;packet[2..4].copy_from_slice(&(len as u16).to_be_bytes());
    packet[4..6].copy_from_slice(&773u16.to_be_bytes());
    packet[8]=64;packet[9]=17;
    packet[12..16].copy_from_slice(&[10,66,0,2]);
    packet[16..20].copy_from_slice(&[10,66,0,1]);
    packet[20..22].copy_from_slice(&44000u16.to_be_bytes());
    packet[22..24].copy_from_slice(&port.to_be_bytes());
    packet[24..26].copy_from_slice(&((8+data.len()) as u16).to_be_bytes());
    packet[28..].copy_from_slice(data);
    let mut sum=0u32;
    for i in (0..20).step_by(2) {
        sum+=u32::from(u16::from_be_bytes([packet[i],packet[i+1]]));
    }
    while sum>0xffff{sum=(sum&0xffff)+(sum>>16)}
    packet[10..12].copy_from_slice(&(!(sum as u16)).to_be_bytes());
    packet
}

#[test]
fn m0_original_tls_game_kernel_2_4_first_app_real_m4_raw_tun(){
    if std::env::var("WBD_M0_GAME_KERNEL_TUN").as_deref()!=Ok("1"){
        return // only the privileged exact-SOURCE Actions namespace claims this
    }
    let dir=std::env::var("WBD_GAME_TLS_FIXTURE_DIR")
        .expect("same-job original Go TLS Game exporter input");
    assert!(unsafe{if_nametoindex(CString::new("lo").unwrap().as_ptr())}>0);
    let index=localhost_index();
    for n in [2usize,4] {
        let owner_tunnel=TunnelKey{slot:14,generation:n as u32};
        let mut client=GameAdapter::from_private_original_go_tls(
            original_tls_cold(&dir,n,"client"),false,owner_tunnel,7)
            .expect("authenticated original-Go client owner");
        let mut server=GameAdapter::from_private_original_go_tls(
            original_tls_cold(&dir,n,"server"),true,owner_tunnel,7)
            .expect("authenticated original-Go server owner");
        let name=format!("wbdgame{n}");
        let owned_fd=tun_fd(&name);
        ip(&["address","add","10.66.0.1/24","dev",&name]);
        ip(&["link","set","dev",&name,"up"]);
        let tun=ScopedTunSink::from_owned_fd(owned_fd,7,&name)
            .map_err(|(err,_)|err).expect("M4 real owned kernel TUN fd");
        let port=45770+n as u16;
        let socket=UdpSocket::bind(format!("10.66.0.1:{port}"))
            .expect("real netns app UDP listener");
        socket.set_read_timeout(Some(Duration::from_millis(800))).unwrap();
        let raw_tx=ScopedRawIpv4Tx::open("lo",index,7)
            .expect("M4 real original scoped Linux raw egress");
        let raw_rx=ScopedRawIpv4Rx::open("lo",index,7)
            .expect("M4 real protected TCP ingress");
        let mut arena=Arena::new(914+n as u32,32,2048,32,131072)
            .expect("same original M1 arena handles");
        let app=vec![n as u8;99];
        let ipv4=original_udp_ipv4(port,&app);
        assert_eq!(client.offer(&ipv4,MonoNs(0)).unwrap(),LogicalPacketId(0));
        let mut actual_kernel_copies=0usize;
        let mut authenticated_unique_tun_writes=0usize;
        let mut valid_lane_mask=0u8;
        let accepted=client.drain(MonoNs(1),|lane,logical,pn,wire|{
            assert_eq!(logical,LogicalPacketId(0));
            assert_eq!(pn,0);
            assert_eq!(lane.generation,7);
            let mut frozen_input=arena.allocate().expect("M1 original immutable owner slab");
            assert!(wire.len()<=frozen_input.writable().len());
            frozen_input.writable()[..wire.len()].copy_from_slice(wire);
            let frozen=frozen_input.freeze(0..wire.len(),FrozenMetadata{
                lane,seq:SeqOffset(1000+u64::from(lane.slot)*2048),
                pn:RecordPn(pn),carrier_snapshot:1
            }).expect("M1 immutable frozen ciphertext M4 loan");
            let src_port=41000+lane.slot as u16;
            let src_ip=[10,0,0,2];let dst_ip=[10,0,1,1];
            let tuple=Ipv4Tuple{
                src_ip:&src_ip,dst_ip:&dst_ip,
                src_port,dst_port:443,
            };
            let presentation=Presentation{ack32:1,advertised_window:4096,
                ip_id:60+lane.slot as u16,persona:PacketPersona::Legacy};
            let actual_copy=raw_tx.send_one(7,&frozen,tuple,presentation)
                .expect("real synchronous M4 raw IPv4/TCP kernel copy");
            assert!(actual_copy>wire.len());
            actual_kernel_copies+=1;
            let mut observed=[0u8;2048];
            let (size,_seq)=raw_rx.recv_one_into(7,&mut observed,tuple,
                PacketPersona::Legacy)
                .expect("the *real* peer-facing kernel TCP packet");
            assert_eq!(&observed[..size],wire,
                "original M3 AEAD ciphertext must survive real raw kernel");
            valid_lane_mask|=1<<(lane.slot-1);
            match server.receive(lane,observed[..size].to_vec())
                .expect("independent original-Go TLS M3 AEAD/replay") {
                Some(plaintext)=>{
                    assert_eq!(plaintext,ipv4);
                    assert_eq!(tun.write_authenticated_ipv4(7,&plaintext)
                        .expect("M4 actual TUN kernel deliver"),ipv4.len());
                    authenticated_unique_tun_writes+=1;
                },
                None=>{}, // independent GameRx first-delivery dedup
            }
            true // only after real M4 kernel TX + authenticated RX
        });
        assert_eq!(accepted,n);
        assert_eq!(actual_kernel_copies,n);
        assert_eq!(valid_lane_mask,(1<<n)-1);
        assert_eq!(authenticated_unique_tun_writes,1);
        let mut buffer=[0u8;256];
        let (size,from)=socket.recv_from(&mut buffer)
            .expect("actual netns UDP application first packet from TUN");
        assert_eq!(size,app.len());assert_eq!(&buffer[..size],&app);
        assert_eq!(from.ip().to_string(),"10.66.0.2");
        client.stop();server.stop();server.stop();
        raw_tx.begin_stop();raw_rx.begin_stop();tun.begin_stop();
        let deadline=Instant::now()+Duration::from_secs(1);
        assert_eq!(raw_tx.stop_until(deadline),StopResult::Drained);
        assert_eq!(raw_rx.stop_until(deadline),StopResult::Drained);
        assert_eq!(tun.stop_until(deadline),StopResult::Drained);
        assert!(matches!(client.offer(b"stale",MonoNs(2)),Err(Error::Stopped)));
        assert!(tun.write_authenticated_ipv4(7,&ipv4).is_err());
        println!("M0_ORIGINAL_GO_TLS_GAME_M4_RAW_TUN_UDP_FIRST_APP_PASS lanes={n} authenticated_original_go_tls=1 native_M3_AEAD_PN=1 raw_kernel_copies={n} independent_lanes={n} udp_payload=99 unique_app=1 stop_stale_denied=1 NOT_PUBLIC_GO_CLI=1 GAME_PRODUCTION_OFF=1");
    }
}
