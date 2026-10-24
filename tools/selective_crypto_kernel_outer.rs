//! Send real kernel-captured inner TCP retransmission pair through laboratory
//! FULL/SELECTIVE outer records on a fresh Linux TCP loopback connection.
#![forbid(unsafe_code)]
use std::{env,fs,io::{Read,Write},net::{TcpListener,TcpStream},thread,time::Duration};
use wbd_codec::record_crypto::{DirectionKeys,LaneTxCrypto,RecordSuite};
use wbd_codec::selective_record_experiment::{Tx,OracleRange,Mode,OVERHEAD};

fn keys(seed:u8)->DirectionKeys {
    DirectionKeys{aead_key:[seed;32],iv:[seed.wrapping_add(1);12],
        hp_key:[seed.wrapping_add(2);32]}
}
fn load_pair(path:&str)->[Vec<u8>;2] {
    let raw=fs::read(path).expect("bounded ephemeral source pair");
    let mut cursor=0usize;
    let mut out:Vec<Vec<u8>>=Vec::with_capacity(2);
    for _ in 0..2 {
        assert!(cursor+2<=raw.len());
        let n=usize::from(u16::from_be_bytes([raw[cursor],raw[cursor+1]]));
        cursor+=2;
        assert!((600..=1427).contains(&n) && cursor+n<=raw.len());
        out.push(raw[cursor..cursor+n].to_vec());cursor+=n;
    }
    assert_eq!(cursor,raw.len());
    out.try_into().unwrap()
}
fn prefix(p:&[u8])->usize{
    assert!(p.len()>=60 && p[0]>>4==4 && p[9]==6);
    let ihl=usize::from(p[0]&15)*4;
    let tcp=usize::from(p[ihl+12]>>4)*4;
    let h=ihl+tcp+5;
    assert!(h<=256 && h+512<=p.len());
    assert_eq!(&p[ihl+tcp..ihl+tcp+3], &[23,3,3]);
    assert_eq!(u16::from_be_bytes([p[2],p[3]]) as usize,p.len());
    h
}
fn main(){
    let args:Vec<_>=env::args().collect();
    assert_eq!(args.len(),3,"usage: selective_crypto_kernel_outer port pair.bin");
    let port:u16=args[1].parse().unwrap();
    let pair=load_pair(&args[2]);let h0=prefix(&pair[0]);let h1=prefix(&pair[1]);
    assert_eq!(h0,h1);
    assert_eq!(pair[0][h0..],pair[1][h1..],"captured genuine kernel TLS body must repeat");
    let ihl=usize::from(pair[0][0]&15)*4;
    assert_eq!(&pair[0][ihl+4..ihl+8],&pair[1][ihl+4..ihl+8],
        "same 32bit inner TCP sequence is mandatory");
    let mut a=LaneTxCrypto::new_for_suite(keys(20),1500,RecordSuite::Aes128Gcm).unwrap();
    let mut b=Tx::new(keys(99),1500,RecordSuite::Aes128Gcm).unwrap();
    let mut records=Vec::new();
    for p in &pair {
        let mut w=vec![0;31+p.len()];
        w[14..14+p.len()].copy_from_slice(p);
        a.seal_in_place(0,&mut w,p.len(),0).unwrap();
        records.push(w);
    }
    for p in &pair {
        let mut w=vec![0;OVERHEAD+p.len()];
        let (_,used,mode)=b.seal(0,p,Some(OracleRange{
            b_start:h0,confirmed_tls_ciphertext:true,
            single_record_suffix:true,protected_edge:false}),&mut w).unwrap();
        assert_eq!(mode,Mode::Selective);
        assert_eq!(used,w.len());
        records.push(w);
    }
    assert_eq!(records[2][15..143],records[3][15..143],
        "untransformed candidate TLS B appears identically under distinct outer PN");
    assert_ne!(records[0][14..142],records[1][14..142]);
    let listener=TcpListener::bind(("127.0.0.1",port)).unwrap();
    let expected:usize=records.iter().map(|r|r.len()).sum();
    let receiver=thread::spawn(move||{
        let (mut socket,_)=listener.accept().unwrap();
        socket.set_read_timeout(Some(Duration::from_secs(5))).unwrap();
        let mut read=0usize;let mut buf=[0u8;8192];
        while read<expected {
            let n=socket.read(&mut buf).unwrap();assert!(n>0);
            read+=n;
        }
        assert_eq!(read,expected);
    });
    let mut socket=TcpStream::connect(("127.0.0.1",port)).unwrap();
    socket.set_nodelay(true).unwrap();
    for r in &records {
        socket.write_all(r).unwrap();
        thread::sleep(Duration::from_millis(80));
    }
    socket.shutdown(std::net::Shutdown::Write).unwrap();
    receiver.join().unwrap();
    println!("NATIVE_INNER_TCP_RETRANSMISSION_OUTER_SENT records=4 inner_same_seq=true \
        ciphertext_128_repeated=true distinct_outer_pn=true bytes={expected}");
}
