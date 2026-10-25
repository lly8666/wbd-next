//! Controlled mixed inner-TLS and non-TLS record CPU benchmark (LAB ONLY).
//! This is NOT a product classifier: classes are supplied by an ideal offline
//! trusted oracle. TLS 1.3 0x17 type alone DOES NOT identify application data.
//! Hybrid XOR packets are entirely unauthenticated even after TLS bootstrap.
//! Real production WBD codec used for all full-AEAD packets, no mock crypto.
use std::{env,fs,hint::black_box,time::{Duration,Instant}};
use wbd_codec::record_crypto::{DirectionKeys,LaneTxCrypto,LaneRxCrypto,RecordSuite};
use wbd_codec::selective_record_experiment::{Tx,Rx,OracleRange,Mode as SelMode,OVERHEAD as AAD_OVERHEAD};
#[path = "../../../tools/lan_xor_tlslike_lab.rs"]
mod xor;

const AEAD_OVERHEAD:usize=31;
const XOR_OVERHEAD:usize=15;
const WIRE_CAP:usize=1500;

#[derive(Copy,Clone,PartialEq,Eq,Debug)]
enum Class { TlsApp, TlsEdge, TlsHandshake, PlainTcp, AckOnly, Udp }
impl Class {
    fn name(self)->&'static str {match self{
        Self::TlsApp=>"tls_app_verified",Self::TlsEdge=>"tls_first_last_protected",
        Self::TlsHandshake=>"tls_handshake_or_alert",Self::PlainTcp=>"ordinary_tcp",
        Self::AckOnly=>"tcp_ack_only",Self::Udp=>"udp_or_other"
    }}
    fn eligible(self)->bool {self==Self::TlsApp}
}
#[derive(Copy,Clone,PartialEq,Eq,Debug)]
enum Plan { FullAead, SelectiveAad, AadLayoutFull, HybridPn, HybridGate, HybridWord, AllPn }
impl Plan {
    fn name(self)->&'static str {match self {
        Self::FullAead=>"full_aead_31b",Self::SelectiveAad=>"selective_aad_33b",
        Self::AadLayoutFull=>"full_aad_layout_33b",Self::HybridPn=>"hybrid_pn_xor",Self::HybridGate=>"hybrid_fastgate_pn_xor",
        Self::HybridWord=>"hybrid_word_rolling_xor",Self::AllPn=>"all_pn_xor_insecure_floor"
    }}
    fn mode_xor(self,c:Class)->bool {match self{
        Self::HybridPn|Self::HybridWord=>c.eligible(),
        Self::HybridGate=>false,
        Self::AllPn=>true,
        _=>false
    }}
    fn mode_aad(self)->bool{matches!(self,Self::SelectiveAad|Self::AadLayoutFull)}
    fn aad_eligible(self,c:Class)->bool{self==Self::SelectiveAad && c.eligible()}
}
#[derive(Clone)]
struct Packet{cls:Class,body:Vec<u8>}
impl Packet{
    fn len(&self)->usize{self.body.len()}
}

fn keys(id:u8)->DirectionKeys{
    DirectionKeys{aead_key:[id.wrapping_add(1);32],iv:[id.wrapping_add(2);12],
        hp_key:[id.wrapping_add(3);32]}
}
fn make_ipv4(n:usize,cls:Class,tls_record:&[u8])->Packet{
    assert!(n>=40&&n<=1345);
    let mut p=vec![0u8;n];
    p[0]=0x45;p[2..4].copy_from_slice(&(n as u16).to_be_bytes());
    p[6]=0x40;p[8]=64;p[9]=if cls==Class::Udp{17}else{6};
    p[12..20].copy_from_slice(&[10,11,12,13,10,21,22,23]);
    let (port,seq) = match cls {
        Class::TlsApp=>(0x1234u16,20000u32),
        Class::TlsEdge=>(0x1234,3000),
        Class::TlsHandshake=>(0x1234,2000),
        Class::PlainTcp=>(0x4321,22000),
        Class::AckOnly=>(0x1234,26000),
        Class::Udp=>(0x5331,4000),
    };
    p[20..22].copy_from_slice(&port.to_be_bytes());
    p[22..24].copy_from_slice(&443u16.to_be_bytes());
    p[24..28].copy_from_slice(&seq.to_be_bytes());
    p[32]=0x50;
    for (i,b)in p[40..].iter_mut().enumerate(){*b=((i*37+11)&255) as u8;}
    match cls{
        Class::TlsApp|Class::TlsEdge=>{
            assert!(n>=45);
            assert!(tls_record.len()>=1305 && tls_record[..3]==[0x17,0x03,0x03]);
            p[40..45].copy_from_slice(&tls_record[..5]);
            let data_len=n-45;
            p[45..].copy_from_slice(&tls_record[5..5+data_len]);
        }
        Class::TlsHandshake=>{
            if n>=45{p[40..45].copy_from_slice(&[22,3,3,1,59]);}
        }
        Class::PlainTcp=>{
            if n>=45 {p[40..45].copy_from_slice(b"HTTP/");}
        }
        Class::AckOnly|Class::Udp=>{}
    }
    assert!(xor::ipv4_packet_ok(&p));
    Packet{cls,body:p}
}
fn scenario(label:&str,tls:&[u8])->Vec<Packet>{
    let mut counts=[0usize;6];
    if let Some(percentage)=label.strip_prefix("equal_") {
        let eligible:usize=percentage.parse().unwrap();
        assert!(eligible<=100);
        counts[0]=eligible;
        // Equal packet-size scenario, other packets split across
        // protected TLS edge, handshake, ordinary TCP.
        for i in eligible..100 {counts[1+(i-eligible)%3]+=1}
    } else {
        counts=match label{
            "web_bulk"=>[80,5,3,5,7,0],
            "mixed_session"=>[40,8,8,18,16,10],
            "non_tls_heavy"=>[10,15,15,30,20,10],
            _=>panic!("unknown workload")
        };
    }
    assert_eq!(counts.iter().sum::<usize>(),100);
    let classes=[Class::TlsApp,Class::TlsEdge,Class::TlsHandshake,
        Class::PlainTcp,Class::AckOnly,Class::Udp];
    let mut pool=Vec::with_capacity(100);
    for (i,cls) in classes.iter().copied().enumerate(){
        for _ in 0..counts[i]{
            let n=if label.starts_with("equal_"){1345}else{match cls{
                Class::TlsApp|Class::TlsEdge|Class::PlainTcp=>1345,
                Class::TlsHandshake=>360,Class::AckOnly=>40,Class::Udp=>540
            }};
            pool.push(make_ipv4(n,cls,tls));
        }
    }
    // Deterministically interleave and break long contiguous mode runs;
    // the multiplier is coprime with 100, so this visits each packet once.
    let permuted=(0..100).map(|i|pool[(i*37)%100].clone()).collect::<Vec<_>>();
    assert_eq!(permuted.iter().filter(|x|x.cls.eligible()).count(),counts[0]);
    permuted
}
// Fast gate is a self-contained O(1) original IPv4/TCP boundary check.
// The .cls attribute is a *trusted laboratory oracle* - NOT available to a
// passive real TLS classifier. This cost measures gate checks, not discovery.
#[inline]
fn fast_gate(p:&Packet)->bool{
    if !p.cls.eligible(){return false}
    let ip=&p.body;
    if ip.len()<45 || ip[0]>>4!=4 || ip[9]!=6{return false}
    let ihl=((ip[0]&15)as usize)*4;
    if ihl<20||ihl+20>ip.len()||ip[6]&0x3f!=0||ip[7]!=0{return false}
    let offset=ihl;
    if ip[offset..offset+2]!=[0x12,0x34] ||
       ip[offset+2..offset+4]!=443u16.to_be_bytes(){return false}
    let tcp=((ip[offset+12]>>4)as usize)*4;
    if tcp<20 || offset+tcp+5>ip.len(){return false}
    let seq=u32::from_be_bytes(ip[offset+4..offset+8].try_into().unwrap());
    if seq<18000 || ip[offset+13]&0x07!=0{return false}
    let data=&ip[offset+tcp..];
    data.len()>=512 && data[..3]==[0x17,0x03,0x03]
}
fn oracle(c:Class)->Option<OracleRange>{
    match c{
        Class::TlsApp=>Some(OracleRange{b_start:45,confirmed_tls_ciphertext:true,
           single_record_suffix:true,protected_edge:false}),
        Class::TlsEdge=>Some(OracleRange{b_start:45,confirmed_tls_ciphertext:true,
           single_record_suffix:true,protected_edge:true}),
        _=>None
    }
}
fn thread_cpu()->u128{
    fs::read_to_string("/proc/thread-self/schedstat").expect("Linux per-thread CPU")
        .split_whitespace().next().unwrap().parse().unwrap()
}

struct Pair{
    tx:LaneTxCrypto,rx:LaneRxCrypto,
    aad_tx:Tx,aad_rx:Rx,
    wire:Vec<u8>,out:Vec<u8>,
    xor_pn:u64,used_aead:u64,used_xor:u64,used_aad_partial:u64,
}
impl Pair{
    fn new(seed:u8)->Self{
        let suite=RecordSuite::Aes128Gcm;
        Self{
            tx:LaneTxCrypto::new_for_suite(keys(seed),WIRE_CAP,suite).unwrap(),
            rx:LaneRxCrypto::new_for_suite(keys(seed),WIRE_CAP,suite).unwrap(),
            aad_tx:Tx::new(keys(seed.wrapping_add(100)),WIRE_CAP,suite).unwrap(),
            aad_rx:Rx::new(keys(seed.wrapping_add(100)),WIRE_CAP,suite).unwrap(),
            wire:vec![0u8;WIRE_CAP],out:vec![0u8;WIRE_CAP],
            xor_pn:0,used_aead:0,used_xor:0,used_aad_partial:0,
        }
    }
    fn round<const CHECK:bool>(&mut self,plan:Plan,p:&Packet)->usize{
        let n=p.len();
        let use_xor=if plan==Plan::HybridGate{fast_gate(p)}else{plan.mode_xor(p.cls)};
        let used=if use_xor{
            // The recording carries NO authenticated policy marker. The
            // receiver here is told the mode by this BENCHMARK ONLY.
            let pn=self.xor_pn;
            self.xor_pn=self.xor_pn.checked_add(1).expect("PN exhaustion");
            let used=n+XOR_OVERHEAD;
            self.wire[..3].copy_from_slice(&[23,3,3]);
            self.wire[3..5].copy_from_slice(&((used-5) as u16).to_be_bytes());
            self.wire[5..13].copy_from_slice(&pn.to_be_bytes());
            self.wire[13..15].copy_from_slice(&(n as u16).to_be_bytes());
            self.wire[15..used].copy_from_slice(&p.body);
            match plan {
                Plan::HybridPn|Plan::HybridGate|Plan::AllPn=>
                    xor::pn_repeat_word_mask(&mut self.wire[13..used],pn),
                Plan::HybridWord=>xor::rolling_word_mask(&mut self.wire[13..used],xor::DEMO_SEED,pn),
                _=>unreachable!()
            }
            black_box(&mut self.wire[..used]);
            assert_eq!(&self.wire[..3],&[23,3,3]);
            assert_eq!(usize::from(u16::from_be_bytes(self.wire[3..5].try_into().unwrap())),used-5);
            let read_pn=u64::from_be_bytes(self.wire[5..13].try_into().unwrap());
            assert_eq!(read_pn,pn);
            match plan {
                Plan::HybridPn|Plan::HybridGate|Plan::AllPn=>
                    xor::pn_repeat_word_mask(&mut self.wire[13..used],read_pn),
                Plan::HybridWord=>xor::rolling_word_mask(&mut self.wire[13..used],xor::DEMO_SEED,read_pn),
                _=>unreachable!()
            }
            assert_eq!(usize::from(u16::from_be_bytes(self.wire[13..15].try_into().unwrap())),n);
            self.out[..n].copy_from_slice(&self.wire[15..used]);
            assert!(xor::ipv4_packet_ok(&self.out[..n]));
            self.used_xor+=1;
            used
        }else if plan.mode_aad(){
            let o=if plan.aad_eligible(p.cls){oracle(p.cls)}else{None};
            let (_,used,mode)=self.aad_tx.seal(0,&p.body,o,&mut self.wire).unwrap();
            assert_eq!(used,n+AAD_OVERHEAD);
            black_box(&mut self.wire[..used]);
            let opened=self.aad_rx.open_into(&mut self.wire[..used],&mut self.out[..n]).unwrap();
            assert_eq!(opened.len,n);
            let expected=if plan.aad_eligible(p.cls){SelMode::Selective}else{SelMode::Full};
            assert_eq!(mode,expected);
            assert_eq!(opened.mode,expected);
            if mode==SelMode::Selective {self.used_aad_partial+=1}else{self.used_aead+=1}
            used
        }else{
            self.wire[14..14+n].copy_from_slice(&p.body);
            let (_,used)=self.tx.seal_in_place(0,&mut self.wire,n,0).unwrap();
            assert_eq!(used,n+AEAD_OVERHEAD);
            black_box(&mut self.wire[..used]);
            let rec=self.rx.open_in_place(&mut self.wire[..used]).unwrap();
            assert_eq!(rec.kind,0);
            assert_eq!(rec.payload.len(),n);
            self.out[..n].copy_from_slice(rec.payload);
            self.used_aead+=1;
            used
        };
        // Functional validation upfront and continuously prevents measuring
        // a branch that secretly drops or skips original packets.
        if CHECK {assert_eq!(&self.out[..n],&p.body[..]);}
        black_box(&self.out[..n]);
        used
    }
}
fn guardrail(tls:&[u8]){
    assert!(tls.len()>=1305 && &tls[..3]==[23,3,3]);
    assert!(u16::from_be_bytes([tls[3],tls[4]]) as usize>=1300);
    // Negative oracle checks: encrypted TLS 1.3 close/handshake can ALSO
    // have the same 17 03 03 record header. Only the out-of-band label
    // allows deliberate PN-XOR. Edge never becomes XOR.
    let p=make_ipv4(1345,Class::TlsApp,tls);
    let e=make_ipv4(1345,Class::TlsEdge,tls);
    assert_eq!(&p.body[40..],&e.body[40..]);
    assert!(fast_gate(&p));
    assert!(!fast_gate(&e));
    for c in [Class::TlsHandshake,Class::PlainTcp,Class::AckOnly,Class::Udp] {
        let n=if c==Class::AckOnly{40}else if c==Class::TlsHandshake{360}else if c==Class::Udp{540}else{1345};
        assert!(!fast_gate(&make_ipv4(n,c,tls)),"unexpected fast gate for {:?}",c);
    }
    for plan in [Plan::HybridPn,Plan::HybridWord] {
        assert!(plan.mode_xor(p.cls));
        assert!(!plan.mode_xor(e.cls));
        for c in [Class::TlsHandshake,Class::PlainTcp,Class::AckOnly,Class::Udp]{
            assert!(!plan.mode_xor(c),"unsafe fallback error on {}",c.name());
        }
    }
    let mut p1=Pair::new(17);
    for kind in [Plan::FullAead,Plan::SelectiveAad,Plan::AadLayoutFull,
                  Plan::HybridPn,Plan::HybridGate,Plan::HybridWord,Plan::AllPn]{
        for c in [Class::TlsApp,Class::TlsEdge,Class::TlsHandshake,
                  Class::PlainTcp,Class::AckOnly,Class::Udp] {
            let n=if c==Class::AckOnly{40}else if c==Class::TlsHandshake{360}else if c==Class::Udp{540}else{1345};
            let q=make_ipv4(n,c,tls);
            p1.round::<true>(kind,&q);
        }
    }
    assert!(p1.used_aad_partial>0 && p1.used_xor>0 && p1.used_aead>0);
    // Validate same TLS app packet, two new outer PNs, 64/128B nonrepeat.
    let pn0=5u64;let pn1=6u64;
    let mut a=vec![0u8;1347];a[..2].copy_from_slice(&(1345u16).to_be_bytes());a[2..].copy_from_slice(&p.body);
    let mut b=a.clone();
    xor::pn_repeat_word_mask(&mut a,pn0);
    xor::pn_repeat_word_mask(&mut b,pn1);
    assert_ne!(&a[2..66],&b[2..66]);assert_ne!(&a[2..130],&b[2..130]);
    for (x,y)in a.chunks_exact(8).zip(b.chunks_exact(8)){assert_ne!(x,y);}
}
fn run(label:&str,kind:Plan,seed:u8,items:&[Packet],secs:u64,warm:bool)->(u64,u64,u128,u128,u64,u64,u64){
    let mut pair=Pair::new(seed);
    let dur=if warm{Duration::from_millis(350)}else{Duration::from_secs(secs)};
    let mut packets=0u64;
    let mut bytes_in=0u64;
    let mut bytes_wire=0u64;
    let start_cpu=thread_cpu();let start=Instant::now();
    loop {
        for _ in 0..100 {
            let item=&items[(packets as usize)%items.len()];
            let used=pair.round::<false>(kind,item);
            packets+=1;
            bytes_in+=item.len() as u64;
            bytes_wire+=used as u64;
            black_box(pair.out[packets as usize%item.len()]);
        }
        if start.elapsed()>=dur{break}
    }
    let wall=start.elapsed().as_nanos();
    let cpu=thread_cpu().saturating_sub(start_cpu);
    let last=&items[((packets-1) as usize)%items.len()];
    assert_eq!(&pair.out[..last.len()],&last.body[..],"last measured packet failed byte-exact roundtrip");
    assert!(cpu>0 && packets>0);
    if !warm{
        println!("{{\"scenario\":\"{}\",\"mode\":\"{}\",\"packets\":{},\"inner_bytes\":{},\"wire_bytes\":{},\"cpu_ns\":{},\"wall_ns\":{},\"aes_records\":{},\"xor_records\":{},\"aad_partial_records\":{},\"eligible_per_100\":{}}}",
            label,kind.name(),packets,bytes_in,bytes_wire,cpu,wall,pair.used_aead,
            pair.used_xor,pair.used_aad_partial,items.iter().filter(|x|x.cls.eligible()).count());
    }
    (packets,bytes_in,cpu,wall,pair.used_aead,pair.used_xor,pair.used_aad_partial)
}
fn main(){
    let args=env::args().collect::<Vec<_>>();
    assert_eq!(args.len(),3,"usage: lan_hybrid_mixed_cost tls_app_record.bin per_leg_seconds");
    let secs:u64=args[2].parse().unwrap();
    assert!((1..=4).contains(&secs));
    let tls=fs::read(&args[1]).expect("locally generated genuine TLS1.3 app ciphertext");
    guardrail(&tls);
    let names=["equal_0","equal_25","equal_50","equal_75","equal_90","equal_100",
        "web_bulk","mixed_session","non_tls_heavy"];
    let plans=[Plan::FullAead,Plan::SelectiveAad,Plan::AadLayoutFull,
        Plan::HybridPn,Plan::HybridGate,Plan::HybridWord,Plan::AllPn];
    println!("{{\"preflight\":\"PASS\",\"tls13_ciphertext_header\":true,\"guardrail_non_app_full_aead\":true,\"scenarios\":{},\"modes\":{}}}",names.len(),plans.len());
    let mut id=0usize;
    for name in names{
        let items=scenario(name,&tls);
        let total_bytes:usize=items.iter().map(Packet::len).sum();
        let eligible_bytes:usize=items.iter().filter(|x|x.cls.eligible()).map(Packet::len).sum();
        println!("{{\"profile\":\"{}\",\"records_per_cycle\":100,\"eligible_records\":{},\"eligible_bytes\":{},\"total_inner_bytes\":{},\"eligible_byte_pct\":{:.6}}}",
            name,items.iter().filter(|x|x.cls.eligible()).count(),eligible_bytes,total_bytes,
            100f64*eligible_bytes as f64/total_bytes as f64);
        // Forward/reverse across the SAME VM and profile.
        for reverse in [false,true]{
            let iterable=if reverse{plans.into_iter().rev().collect::<Vec<_>>()}else{plans.to_vec()};
            for kind in iterable {
                id+=1;
                // One preinitialized independent AEAD domain per leg;
                // per-packet AES nonces and XOR PNs never reused in that leg.
                let seed=30u8.wrapping_add(id as u8);
                run(name,kind,seed,&items,secs,true);
                run(name,kind,seed.wrapping_add(1),&items,secs,false);
            }
        }
    }
}
