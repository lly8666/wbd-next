//! S1 lab-only paired record CPU cost. No real TUN/network/pcap qualification.
use std::{env,fs, hint::black_box, time::{Duration,Instant}};
use wbd_codec::record_crypto::{DirectionKeys,LaneRxCrypto,LaneTxCrypto,RecordSuite};
use wbd_codec::selective_record_experiment::{OracleRange,Tx,Rx,Mode,OVERHEAD};

fn keys(id:u8)->DirectionKeys {
    DirectionKeys{aead_key:[id.wrapping_add(1);32],iv:[id.wrapping_add(2);12],
        hp_key:[id.wrapping_add(3);32]}
}
fn suite(s:&str)->RecordSuite {
    match s {"aes128"=>RecordSuite::Aes128Gcm,
             "aes256"=>RecordSuite::Aes256Gcm,
             "chacha"=>RecordSuite::ChaCha20Poly1305,
             _=>panic!("suite must be aes128/aes256/chacha")}
}
fn packet(ciphertext_record:&[u8])->Vec<u8>{
    assert!(ciphertext_record.len()>=5+1300);
    assert_eq!(&ciphertext_record[..3], &[23,3,3],"must be a TLS 1.3 encrypted record");
    let record_len=u16::from_be_bytes([ciphertext_record[3],ciphertext_record[4]]) as usize;
    assert!(record_len>=1300 && ciphertext_record.len()>=5+record_len);
    let n=45+1300;
    let mut p=vec![0u8;n];p[0]=0x45;
    p[2..4].copy_from_slice(&(n as u16).to_be_bytes());
    p[6]=0x40;p[8]=64;p[9]=6;p[32]=0x50;
    p[40..45].copy_from_slice(&ciphertext_record[..5]);
    p[45..].copy_from_slice(&ciphertext_record[5..5+1300]);p
}
fn thread_cpu_ns()->u128 {
    fs::read_to_string("/proc/thread-self/schedstat").ok()
        .and_then(|x|x.split_whitespace().next().and_then(|v|v.parse().ok()))
        .unwrap_or(0)
}
fn rss_kb()->u64{
    fs::read_to_string("/proc/self/status").unwrap_or_default().lines()
        .find(|l|l.starts_with("VmRSS:"))
        .and_then(|l|l.split_whitespace().nth(1))
        .and_then(|s|s.parse().ok()).unwrap_or(0)
}
fn oracle()->Option<OracleRange>{
    Some(OracleRange{b_start:45,confirmed_tls_ciphertext:true,
        single_record_suffix:true,protected_edge:false})
}
fn round(kind:&str,p:&[u8],t_old:&mut LaneTxCrypto,r_old:&LaneRxCrypto,
         t_new:&mut Tx,r_new:&Rx,wire:&mut [u8],out:&mut [u8])->usize {
    if kind=="A" {
        wire[14..14+p.len()].copy_from_slice(p);
        let (_,used)=t_old.seal_in_place(0,wire,p.len(),0).expect("legacy seal");
        let rec=r_old.open_in_place(&mut wire[..used]).expect("legacy auth open");
        out[..p.len()].copy_from_slice(rec.payload);
        used
    }else{
        let o=if kind=="B"{oracle()}else{None};
        let (_,used,m)=t_new.seal(0,p,o,wire).expect("lab seal");
        assert_eq!(m, if kind=="B"{Mode::Selective}else{Mode::Full});
        let rec=r_new.open_into(&mut wire[..used],out).expect("lab auth open");
        assert_eq!(rec.len,p.len());
        used
    }
}
fn leg(kind:&str,id:u8,s:RecordSuite,p:&[u8],warm:Duration,measure:Duration){
    let mut t_old=LaneTxCrypto::new_for_suite(keys(id),1500,s).unwrap();
    let r_old=LaneRxCrypto::new_for_suite(keys(id),1500,s).unwrap();
    let mut t_new=Tx::new(keys(id),1500,s).unwrap();
    let r_new=Rx::new(keys(id),1500,s).unwrap();
    let mut wire=vec![0u8;OVERHEAD+p.len()];
    let mut out=vec![0u8;p.len()];
    let mut packets=0u64;let mut wire_bytes=0u64;let mut check=0u64;
    let warm_start=Instant::now();
    while warm_start.elapsed()<warm {
        let used=round(kind,p,&mut t_old,&r_old,&mut t_new,&r_new,&mut wire,&mut out);
        check=check.wrapping_add(u64::from(out[(packets as usize)%out.len()]));
        packets+=1;black_box(used);
    }
    let start_cpu=thread_cpu_ns();let start=Instant::now();
    packets=0;
    while start.elapsed()<measure {
        let used=round(kind,p,&mut t_old,&r_old,&mut t_new,&r_new,&mut wire,&mut out);
        check=check.wrapping_add(u64::from(out[(packets as usize)%out.len()]));
        packets+=1;wire_bytes+=used as u64;
        black_box(&out[0]);black_box(&wire[0]);
    }
    let elapsed=start.elapsed().as_nanos();let cpu=thread_cpu_ns().saturating_sub(start_cpu);
    assert_ne!(packets,0);black_box(check);
    println!("{{\"leg\":\"{}\",\"index\":{},\"packets\":{},\"bytes_inner\":{},\"bytes_wire\":{},\"cpu_ns\":{},\"wall_ns\":{},\"rss_kb\":{},\"oracle_eligible_bytes_per_packet\":{},\"copy_bytes_per_packet_tx_rx\":{},\"check\":{}}}",
        kind,id,packets,packets*p.len() as u64,wire_bytes,cpu,elapsed,
        rss_kb(),if kind=="B"{1300}else{0},
        if kind=="B"{2*p.len()}else{2*p.len()},check);
}
fn main(){
    let args:Vec<_>=env::args().collect();
    assert_eq!(args.len(),4,"usage: selective_crypto_cost suite corpus.bin measure_seconds");
    let s=suite(&args[1]);
    let p=packet(&fs::read(&args[2]).expect("real TLS encrypted record corpus"));
    let seconds:u64=args[3].parse().expect("measure seconds");
    assert!((1..=30).contains(&seconds));
    let mut tx=Tx::new(keys(100),1500,s).unwrap();
    let mut a=vec![0u8;OVERHEAD+p.len()];
    let mut b=a.clone();
    let (n1,_,m1)=tx.seal(0,&p,oracle(),&mut a).unwrap();
    let (n2,_,m2)=tx.seal(0,&p,oracle(),&mut b).unwrap();
    assert_ne!(n1,n2); assert_eq!((m1,m2),(Mode::Selective,Mode::Selective));
    let repeat64=a[15..79]==b[15..79];
    let repeat128=a[15..143]==b[15..143];
    assert!(repeat64 && repeat128);
    println!("{{\"counterexample\":\"CONSTRUCTED_DISTINCT_OUTER_PN\",\"pn_distinct\":true,\"same_64\":{},\"same_128\":{},\"real_kernel_capture\":false}}",repeat64,repeat128);
    for (index,kind) in ["A","A-layout","B","B","A-layout","A"].iter().enumerate(){
        leg(kind,index as u8+20,s,&p,Duration::from_secs(2),Duration::from_secs(seconds));
    }
}
