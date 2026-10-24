//! Bounded lab fixture: identical inner TCP Seq/TLS ciphertext written twice
//! under new outer PN and new kernel TCP stream positions. Not kernel TUN,
//! not a live inner TCP retransmission or authenticated Go TLS bootstrap.
use std::{env,fs,io::{Read,Write},net::{TcpListener,TcpStream},thread,time::Duration};
use wbd_codec::record_crypto::{DirectionKeys,LaneTxCrypto,RecordSuite};
use wbd_codec::selective_record_experiment::{Tx,OracleRange,Mode,OVERHEAD};

fn keys(seed:u8)->DirectionKeys {
    DirectionKeys{aead_key:[seed;32],iv:[seed.wrapping_add(1);12],
        hp_key:[seed.wrapping_add(2);32]}
}
fn main() {
    let args:Vec<String>=env::args().collect();
    assert_eq!(args.len(),3,"usage: selective_crypto_capture port tls_record.bin");
    let port:u16=args[1].parse().unwrap();
    let tls=fs::read(&args[2]).unwrap();
    assert!(tls.len()>=1305 && tls[..3]==[23,3,3]);
    let rec_size=u16::from_be_bytes([tls[3],tls[4]]) as usize;
    assert!(rec_size>=1300 && tls.len()>=5+rec_size);
    let mut inner=vec![0u8;1345];
    inner[0]=0x45;
    inner[2..4].copy_from_slice(&(inner.len() as u16).to_be_bytes());
    inner[6]=0x40;inner[8]=64;inner[9]=6;
    inner[12..16].copy_from_slice(&[10,11,12,13]);
    inner[16..20].copy_from_slice(&[10,21,22,23]);
    inner[24..28].copy_from_slice(&0x0102_0304u32.to_be_bytes()); // fixed inner TCP sequence
    inner[32]=0x50;
    inner[40..45].copy_from_slice(&tls[..5]);
    inner[45..].copy_from_slice(&tls[5..1305]);
    let s=RecordSuite::Aes128Gcm;
    let mut original=LaneTxCrypto::new_for_suite(keys(22),1500,s).unwrap();
    let mut candidate=Tx::new(keys(77),1500,s).unwrap();
    let mut records=Vec::new();
    for i in 0..4 {
        if i<2 {
            let mut w=vec![0u8;31+inner.len()];
            w[14..14+inner.len()].copy_from_slice(&inner);
            original.seal_in_place(0,&mut w,inner.len(),0).unwrap();
            records.push(w);
        }else{
            let mut w=vec![0u8;OVERHEAD+inner.len()];
            let (_,len,mode)=candidate.seal(0,&inner,Some(OracleRange{
                b_start:45,confirmed_tls_ciphertext:true,single_record_suffix:true,protected_edge:false}),&mut w).unwrap();
            assert_eq!(len,w.len());
            assert_eq!(mode,Mode::Selective);
            records.push(w);
        }
    }
    assert_eq!(&records[2][15..143],&records[3][15..143]);
    assert_ne!(&records[0][14..142],&records[1][14..142]);
    let listener=TcpListener::bind(("127.0.0.1",port)).unwrap();
    let expected:usize=records.iter().map(|v|v.len()).sum();
    let reader=thread::spawn(move||{
        let (mut stream,_)=listener.accept().unwrap();
        stream.set_read_timeout(Some(Duration::from_secs(4))).unwrap();
        let mut bytes=0usize;
        let mut buf=[0u8;8192];
        while bytes<expected {
            let n=stream.read(&mut buf).expect("reader");
            assert_ne!(n,0);bytes+=n;
        }
        assert_eq!(bytes,expected);
    });
    let mut stream=TcpStream::connect(("127.0.0.1",port)).unwrap();
    stream.set_nodelay(true).unwrap();
    for rec in &records {
        stream.write_all(rec).unwrap();
        thread::sleep(Duration::from_millis(75));
    }
    stream.shutdown(std::net::Shutdown::Write).unwrap();
    reader.join().unwrap();
    println!("LAB_CAPTURE_SENT records=4 inner_same_tcp_seq=true B_PN_distinct=true total_wire_bytes={expected}");
}
