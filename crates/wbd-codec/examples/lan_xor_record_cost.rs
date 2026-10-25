//! S2 bounded LAN-record CPU comparison. Microbenchmark, NOT product/TUN.
//! Same exact 1345B IPv4/TCP lab corpus and reusable buffers, full seal+open.
//! Clear, fixed XOR, packet-local rolling XOR, AES128-GCM, ChaCha20-Poly1305.
//! One SAME CPU/runner per comparison. Deliberately no WAN traffic or TLS path.
use std::{env,fs,hint::black_box,time::{Duration,Instant}};
use wbd_codec::record_crypto::{DirectionKeys,LaneRxCrypto,LaneTxCrypto,RecordSuite};
#[path = "../../../tools/lan_xor_tlslike_lab.rs"]
mod xor;

const MAX_WIRE: usize = 1500;
const XOR_OVERHEAD: usize = 15;
const AEAD_OVERHEAD: usize = 31;

#[derive(Clone,Copy,Debug,PartialEq,Eq)]
enum Kind { Clear, Fixed, Rolling, RollingWord, PnRepeat, Aes128, Chacha }
impl Kind {
    fn name(self)->&'static str { match self {
        Self::Clear=>"clear",Self::Fixed=>"fixed_xor",Self::Rolling=>"rolling_xor",
        Self::RollingWord=>"rolling_word_xor",
        Self::PnRepeat=>"pn_repeat_word_xor",
        Self::Aes128=>"aes128_gcm",Self::Chacha=>"chacha20_poly1305"
    }}
    fn xor_mode(self)->Option<xor::Mode> {match self {
        Self::Fixed=>Some(xor::Mode::FixedXor),
        Self::Rolling|Self::RollingWord=>Some(xor::Mode::RollingXor),
        _=>None
    }}
    fn suite(self)->Option<RecordSuite> {match self {
        Self::Aes128=>Some(RecordSuite::Aes128Gcm),
        Self::Chacha=>Some(RecordSuite::ChaCha20Poly1305),
        _=>None
    }}
}

fn keys(id:u8)->DirectionKeys {
    DirectionKeys{
        aead_key:[id.wrapping_add(1);32],
        iv:[id.wrapping_add(2);12],
        hp_key:[id.wrapping_add(3);32]
    }
}
fn thread_cpu_ns()->u128 {
    fs::read_to_string("/proc/thread-self/schedstat").expect("Linux thread schedstat").split_whitespace()
        .next().expect("thread schedstat CPU field").parse::<u128>()
        .expect("valid schedstat CPU nanoseconds")
}
fn rss_kb()->u64 {
    fs::read_to_string("/proc/self/status").unwrap_or_default().lines()
      .find(|s|s.starts_with("VmRSS:"))
      .and_then(|s|s.split_whitespace().nth(1))
      .and_then(|x|x.parse().ok()).unwrap_or(0)
}

/// Fast-path reuses a preallocated buffer; format EXACTLY matches the
/// separately unit-tested fixed/rolling XOR standalone LAN fixture.
fn xor_seal_into(
    p:&[u8],mode:Option<xor::Mode>,fast_word:bool,pn_repeat:bool,pn:u64,wire:&mut [u8]
)->usize {
    let used = p.len()+XOR_OVERHEAD;
    assert!(used<=wire.len() && used<=MAX_WIRE);
    wire[..3].copy_from_slice(&[0x17,0x03,0x03]);
    wire[3..5].copy_from_slice(&((p.len()+10) as u16).to_be_bytes());
    wire[5..13].copy_from_slice(&pn.to_be_bytes());
    wire[13..15].copy_from_slice(&(p.len() as u16).to_be_bytes());
    wire[15..used].copy_from_slice(p);
    if pn_repeat { xor::pn_repeat_word_mask(&mut wire[13..used],pn); }
    else if fast_word { xor::rolling_word_mask(&mut wire[13..used],xor::DEMO_SEED,pn); }
    else if let Some(m)=mode { xor::mask(&mut wire[13..used],m,xor::DEMO_SEED,pn); }
    used
}
fn xor_open_into(
    mode:Option<xor::Mode>,fast_word:bool,pn_repeat:bool,wire:&mut [u8],used:usize,out:&mut [u8]
)->u64 {
    assert_eq!(&wire[..3], &[0x17,0x03,0x03]);
    assert_eq!(usize::from(u16::from_be_bytes([wire[3],wire[4]])),used-5);
    let pn=u64::from_be_bytes(wire[5..13].try_into().unwrap());
    if pn_repeat {xor::pn_repeat_word_mask(&mut wire[13..used],pn);}
    else if fast_word {xor::rolling_word_mask(&mut wire[13..used],xor::DEMO_SEED,pn);}
    else if let Some(m)=mode {xor::mask(&mut wire[13..used],m,xor::DEMO_SEED,pn);}
    let n=usize::from(u16::from_be_bytes([wire[13],wire[14]]));
    assert_eq!(n+XOR_OVERHEAD,used);
    out[..n].copy_from_slice(&wire[15..used]);
    assert!(xor::ipv4_packet_ok(&out[..n]));
    pn
}

struct Pair {
    tx:LaneTxCrypto,
    rx:LaneRxCrypto,
    wire:Vec<u8>,
    out:Vec<u8>,
    xor_next_pn:u64
}
impl Pair {
    fn new(kind:Kind,id:u8,n:usize)->Self {
        let suite=kind.suite().unwrap_or(RecordSuite::Aes128Gcm);
        Self{
            tx:LaneTxCrypto::new_for_suite(keys(id),MAX_WIRE,suite).unwrap(),
            rx:LaneRxCrypto::new_for_suite(keys(id),MAX_WIRE,suite).unwrap(),
            wire:vec![0u8;n+AEAD_OVERHEAD],
            out:vec![0u8;n],
            xor_next_pn:0
        }
    }
    fn round(&mut self,kind:Kind,p:&[u8])->usize {
        let n=p.len();
        let used=if kind.suite().is_some() {
            self.wire[14..14+n].copy_from_slice(p);
            let (_,used)=self.tx.seal_in_place(0,&mut self.wire,n,0).unwrap();
            assert_eq!(used,n+AEAD_OVERHEAD);
            // The sealing MUST happen: hide wire state from compiler.
            black_box(&mut self.wire[..used]);
            let r=self.rx.open_in_place(&mut self.wire[..used]).unwrap();
            assert_eq!(r.kind,0);
            assert_eq!(r.payload.len(),n);
            self.out[..n].copy_from_slice(r.payload);
            used
        } else {
            let pn=self.xor_next_pn;
            self.xor_next_pn=self.xor_next_pn.checked_add(1).unwrap();
            let used=xor_seal_into(p,kind.xor_mode(),kind==Kind::RollingWord,kind==Kind::PnRepeat,pn,&mut self.wire);
            black_box(&mut self.wire[..used]);
            let readpn=xor_open_into(kind.xor_mode(),kind==Kind::RollingWord,kind==Kind::PnRepeat,&mut self.wire,used,&mut self.out);
            assert_eq!(pn,readpn);
            used
        };
        // Equivalent sink across all modes, outside parser semantics.
        black_box(&self.out[..n]);
        used
    }
}
fn check_fixture_equivalence(p:&[u8]){
    assert!(xor::ipv4_packet_ok(p));
    for (m,kind) in [(xor::Mode::FixedXor,Kind::Fixed),
                     (xor::Mode::RollingXor,Kind::Rolling),
                     (xor::Mode::RollingXor,Kind::RollingWord)] {
        for pn in [0u64,1,2,3,100] {
            let fixture=xor::seal(p,m,xor::DEMO_SEED,pn).unwrap();
            let mut w=vec![0u8;p.len()+XOR_OVERHEAD];
            let used=xor_seal_into(p,kind.xor_mode(),kind==Kind::RollingWord,false,pn,&mut w);
            assert_eq!(&w[..used],&fixture[..],"benchmark must use captured wire format");
            let mut out=vec![0u8;p.len()];
            assert_eq!(xor_open_into(kind.xor_mode(),kind==Kind::RollingWord,false,&mut w,used,&mut out),pn);
            assert_eq!(out,p);
            let (fpn,decoded)=xor::open(&fixture,m,xor::DEMO_SEED).unwrap();
            assert_eq!(fpn,pn);assert_eq!(decoded,p);
        }
    }
    // New PN mask: required 5B TLS-like header, clear unique 8B PN,
    // and all full masked 8B chunks differing for re-sent identical payload.
    for pn in [0u64,1,255,256,u64::MAX] {
        let mut w=vec![0u8;p.len()+XOR_OVERHEAD];
        let used=xor_seal_into(p,None,false,true,pn,&mut w);
        assert_eq!(used,1360);
        assert_eq!(&w[..3],&[0x17,0x03,0x03]);
        assert_eq!(u64::from_be_bytes(w[5..13].try_into().unwrap()),pn);
        let mut out=vec![0u8;p.len()];
        assert_eq!(xor_open_into(None,false,true,&mut w,used,&mut out),pn);
        assert_eq!(out,p);
    }
    for kind in [Kind::Clear,Kind::Fixed,Kind::Rolling,Kind::RollingWord,Kind::PnRepeat,Kind::Aes128,Kind::Chacha]{
        let mut pair=Pair::new(kind,100,p.len());
        let used=pair.round(kind,p);
        assert_eq!(used,p.len()+if kind.suite().is_some(){AEAD_OVERHEAD}else{XOR_OVERHEAD});
        assert_eq!(pair.out,p);
    }
}
fn drive(kind:Kind, id:u8,p:&[u8], duration:Duration, measured:bool)->(u64,u64,u128,u128,u64) {
    let mut pair=Pair::new(kind,id,p.len());
    let start_cpu=thread_cpu_ns();
    let start=Instant::now();
    let mut packets=0u64;
    let mut wire_bytes=0u64;
    let mut sum=0u64;
    loop {
        for _ in 0..128 {
            let used=pair.round(kind,p);
            wire_bytes+=used as u64;
            sum=sum.wrapping_add(u64::from(pair.out[(packets as usize)%p.len()]));
            packets+=1;
            black_box(sum);
        }
        if start.elapsed()>=duration {break}
    }
    let wall_ns=start.elapsed().as_nanos();
    let cpu_ns=thread_cpu_ns().saturating_sub(start_cpu);
    assert!(cpu_ns>0 && packets>0 && wire_bytes>0);
    assert_eq!(pair.out,p);
    if measured {
        println!("{{\"kind\":\"{}\",\"packets\":{},\"bytes_inner\":{},\"bytes_wire\":{},\"cpu_ns\":{},\"wall_ns\":{},\"rss_kb\":{},\"check\":{}}}",
            kind.name(),packets,packets*p.len() as u64,wire_bytes,cpu_ns,wall_ns,rss_kb(),sum);
    }
    (packets,wire_bytes,cpu_ns,wall_ns,sum)
}
fn main(){
    let args:Vec<String>=env::args().collect();
    assert_eq!(args.len(),2,"usage: lan_xor_record_cost measure_seconds (3..15)");
    let secs:u64=args[1].parse().expect("positive measure seconds");
    assert!((3..=15).contains(&secs));
    let p=xor::sample_ip_packet();
    assert_eq!(p.len(),1345);
    check_fixture_equivalence(&p);
    eprintln!("preflight passed: same fixture bytes/headers & both native AEAD suites");
    let order=[
        Kind::Aes128,Kind::Chacha,Kind::Fixed,Kind::Rolling,Kind::RollingWord,Kind::PnRepeat,Kind::Clear,
        Kind::Clear,Kind::PnRepeat,Kind::RollingWord,Kind::Rolling,Kind::Fixed,Kind::Chacha,Kind::Aes128
    ];
    for (i,kind) in order.iter().copied().enumerate(){
        drive(kind,(i+20) as u8,&p,Duration::from_millis(700),false);
        println!("{{\"sequence_index\":{},\"next_kind\":\"{}\",\"warm_ms\":700}}",i,kind.name());
        drive(kind,(i+50) as u8,&p,Duration::from_secs(secs),true);
    }
}
