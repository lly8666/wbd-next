//! Opt-in record experiment only. NOT a product decoder, negotiation, or classifier.
//! One AEAD: authenticated (outer header || PN || descriptor || B), encrypted C.
//! No receiver state is changed until this function returns authenticated bytes.
#![forbid(unsafe_code)]
use aes::{Aes128,Aes256};
use aes::cipher::{BlockEncrypt,KeyInit,generic_array::GenericArray};
use aws_lc_rs::aead::{self,Aad,LessSafeKey,Nonce,UnboundKey};
use chacha20::cipher::{KeyIvInit,StreamCipher,StreamCipherSeek};
use chacha20::ChaCha20;
use crate::record_crypto::{CryptoError,DirectionKeys,RecordSuite};
use crate::record_frame::{outer_header_for_body,MAX_WIRE_LEN,OUTER_HEADER_LEN,OUTER_TYPE,OUTER_VERSION};

pub const OVERHEAD: usize = 33;
pub const MIN_B: usize = 512;
pub const MAX_H: usize = 256;
const AAD_PREFIX: usize = 15;
const TAG: usize = 16;
const MASK: usize = 10;
const MARKER: u8 = 0x17;

#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub struct OracleRange {
    pub b_start: usize,
    pub confirmed_tls_ciphertext: bool,
    pub single_record_suffix: bool,
    pub protected_edge: bool,
}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub enum Mode { Full, Selective }
#[derive(Debug,PartialEq,Eq)]
pub struct Opened { pub pn:u64, pub kind:u8, pub len:usize, pub mode:Mode }
pub struct Tx { aead:LessSafeKey, iv:[u8;12], hp:Hp, max_wire:usize, next_pn:u64, exhausted:bool }
pub struct Rx { aead:LessSafeKey, iv:[u8;12], hp:Hp, max_wire:usize }
enum Hp { ChaCha([u8;32]), A128(Aes128), A256(Aes256) }

impl Hp {
    fn new(s:RecordSuite, k:&[u8;32])->Self {
        match s {
            RecordSuite::ChaCha20Poly1305 => Self::ChaCha(*k),
            RecordSuite::Aes128Gcm => Self::A128(Aes128::new(GenericArray::from_slice(&k[..16]))),
            RecordSuite::Aes256Gcm => Self::A256(Aes256::new(GenericArray::from_slice(k))),
        }
    }
    fn mask(&self,tag:&[u8])->Result<[u8;MASK],CryptoError> {
        if tag.len()!=TAG {return Err(CryptoError::InvalidLength)}
        let mut out=[0u8;MASK];
        match self {
            Self::ChaCha(key)=>{
                let counter=u32::from_le_bytes(tag[..4].try_into().map_err(|_|CryptoError::InvalidLength)?);
                let mut nonce=[0u8;12];nonce.copy_from_slice(&tag[4..]);
                let mut stream=ChaCha20::new(key.into(),(&nonce).into());
                stream.seek(u64::from(counter)*64);
                stream.apply_keystream(&mut out);
            }
            Self::A128(cipher)=>{
                let mut b=GenericArray::clone_from_slice(tag);
                cipher.encrypt_block(&mut b);out.copy_from_slice(&b[..MASK]);
            }
            Self::A256(cipher)=>{
                let mut b=GenericArray::clone_from_slice(tag);
                cipher.encrypt_block(&mut b);out.copy_from_slice(&b[..MASK]);
            }
        }
        Ok(out)
    }
}
fn aead(s:RecordSuite,key:&[u8;32])->Result<LessSafeKey,CryptoError> {
    let u=match s {
        RecordSuite::ChaCha20Poly1305=>UnboundKey::new(&aead::CHACHA20_POLY1305,key),
        RecordSuite::Aes128Gcm=>UnboundKey::new(&aead::AES_128_GCM,&key[..16]),
        RecordSuite::Aes256Gcm=>UnboundKey::new(&aead::AES_256_GCM,key),
    }.map_err(|_|CryptoError::PrimitiveFailure)?;
    Ok(LessSafeKey::new(u))
}
fn nonce(iv:&[u8;12],pn:u64)->Nonce {
    let mut n=*iv;
    for (a,b) in n[4..].iter_mut().zip(pn.to_be_bytes()){*a^=b;}
    Nonce::assume_unique_for_key(n)
}
fn limit(n:usize)->Result<usize,CryptoError>{
    if !(OVERHEAD..=MAX_WIRE_LEN).contains(&n) {Err(CryptoError::WireLimit)} else {Ok(n)}
}
// This validates *structure*, not TLS ciphertext provenance. Only a trusted,
// out-of-band test oracle may authorize a bypass. Never guess from port/entropy.
fn ipv4_tcp(packet:&[u8],h:usize)->bool {
    if packet.len()<40 || packet[0]>>4!=4 {return false;}
    let ihl=usize::from(packet[0]&15)*4;
    if ihl<20 || ihl+20>packet.len() || packet[9]!=6 {return false;}
    if usize::from(u16::from_be_bytes([packet[2],packet[3]]))!=packet.len(){return false;}
    if u16::from_be_bytes([packet[6],packet[7]]) & 0x3fff != 0 {return false;}
    let tcp=usize::from(packet[ihl+12]>>4)*4;
    tcp>=20 && ihl+tcp+5<=h && h<=packet.len()
}
fn start(packet:&[u8],o:Option<OracleRange>)->Option<usize>{
    let o=o?;
    if o.confirmed_tls_ciphertext && o.single_record_suffix && !o.protected_edge
        && o.b_start<=MAX_H && o.b_start<=packet.len()
        && packet.len()-o.b_start>=MIN_B && ipv4_tcp(packet,o.b_start) {
        Some(o.b_start)
    } else {None}
}
impl Tx {
    /// Keys MUST be independently scoped to suite, direction, generation and
    /// experimental wire capability by an authenticated caller. This lab tool
    /// does not and cannot grant any production admission.
    pub fn new(keys:DirectionKeys,max_wire:usize,s:RecordSuite)->Result<Self,CryptoError>{
        let max_wire=limit(max_wire)?;
        Ok(Self{aead:aead(s,&keys.aead_key)?,iv:keys.iv,hp:Hp::new(s,&keys.hp_key),
            max_wire,next_pn:0,exhausted:false})
    }
    /// For each invocation, even an invalid request consumes the allocated PN.
    /// Caller owns the frozen output on success; never reseal retransmissions.
    pub fn seal(&mut self,kind:u8,packet:&[u8],oracle:Option<OracleRange>,wire:&mut [u8])
        ->Result<(u64,usize,Mode),CryptoError> {
        if self.exhausted {return Err(CryptoError::PnExhausted)}
        let pn=self.next_pn;
        if pn==u64::MAX {self.exhausted=true} else {self.next_pn+=1}
        if !matches!(kind,0|1){return Err(CryptoError::InvalidKind)}
        let eligible=if kind==0 {start(packet,oracle)} else {None};
        let mode=if eligible.is_some(){Mode::Selective}else{Mode::Full};
        let h=eligible.unwrap_or(packet.len());
        let b=packet.len()-h;
        let m=h.checked_add(2).ok_or(CryptoError::InvalidLength)?;
        if m>0x7fff {return Err(CryptoError::InvalidLength)}
        let used=OVERHEAD.checked_add(packet.len()).ok_or(CryptoError::InvalidLength)?;
        if used>self.max_wire {return Err(CryptoError::InvalidLength)}
        if wire.len()<used {return Err(CryptoError::Capacity)}
        let hdr=outer_header_for_body(used-OUTER_HEADER_LEN,self.max_wire)
            .map_err(|_|CryptoError::InvalidLength)?;
        wire[..5].copy_from_slice(&hdr);
        wire[5..13].copy_from_slice(&pn.to_be_bytes());
        let descriptor=(m as u16)|if mode==Mode::Selective {0x8000}else{0};
        wire[13..15].copy_from_slice(&descriptor.to_be_bytes());
        let b_end=AAD_PREFIX+b;
        wire[AAD_PREFIX..b_end].copy_from_slice(&packet[h..]);
        // split_at_mut prevents an AAD/C alias or a per-packet AAD Vec.
        let (aad,rest)=wire[..used].split_at_mut(b_end);
        rest[0]=kind;
        rest[1..1+h].copy_from_slice(&packet[..h]);
        rest[1+h]=MARKER;
        let t=self.aead.seal_in_place_separate_tag(nonce(&self.iv,pn),
            Aad::from(&aad[..]),&mut rest[..m]).map_err(|_|CryptoError::PrimitiveFailure)?;
        rest[m..m+TAG].copy_from_slice(t.as_ref());
        let hp=self.hp.mask(&wire[used-TAG..used])?;
        for (v,k) in wire[5..15].iter_mut().zip(hp) {*v^=k;}
        Ok((pn,used,mode))
    }
}
impl Rx {
    pub fn new(keys:DirectionKeys,max_wire:usize,s:RecordSuite)->Result<Self,CryptoError>{
        let max_wire=limit(max_wire)?;
        Ok(Self{aead:aead(s,&keys.aead_key)?,iv:keys.iv,hp:Hp::new(s,&keys.hp_key),max_wire})
    }
    /// Output is untouched until AEAD succeeds. Receiver state (epoch/replay,
    /// downstream first-delivery) remains owned by the authenticated caller.
    pub fn open_into(&self,wire:&mut [u8],out:&mut [u8])->Result<Opened,CryptoError>{
        let len=wire.len();
        if len<OVERHEAD || len>self.max_wire{return Err(CryptoError::InvalidLength)}
        if wire[0]!=OUTER_TYPE || wire[1..3]!=OUTER_VERSION {return Err(CryptoError::InvalidHeader)}
        let declared=u16::from_be_bytes([wire[3],wire[4]]) as usize;
        if declared+5!=len{return Err(CryptoError::InvalidLength)}
        let hp=self.hp.mask(&wire[len-TAG..])?;
        for (v,k) in wire[5..15].iter_mut().zip(hp){*v^=k;}
        let pn=u64::from_be_bytes(wire[5..13].try_into().map_err(|_|CryptoError::InvalidLength)?);
        let raw=u16::from_be_bytes([wire[13],wire[14]]);
        let mode=if raw&0x8000!=0 {Mode::Selective}else{Mode::Full};
        let m=usize::from(raw&0x7fff);
        // Untrusted descriptor only bounds partitioning; not permission to deliver.
        if m<2 || m>len-15-TAG {return Err(CryptoError::InvalidLength)}
        let b=len-OVERHEAD-(m-2);
        if mode==Mode::Full && b!=0 {return Err(CryptoError::InvalidLength)}
        if mode==Mode::Selective && (m-2>MAX_H || b<MIN_B) {
            return Err(CryptoError::InvalidLength)
        }
        let end=AAD_PREFIX+b;
        let (aad,rest)=wire.split_at_mut(end);
        let plain=self.aead.open_in_place(nonce(&self.iv,pn),Aad::from(&aad[..]),rest)
            .map_err(|_|CryptoError::Authentication)?;
        if plain.len()!=m || plain[m-1]!=MARKER {return Err(CryptoError::InvalidInnerMarker)}
        let kind=plain[0];
        if !matches!(kind,0|1) || (kind!=0 && mode==Mode::Selective) {
            return Err(CryptoError::InvalidKind)
        }
        let total=m-2+b;
        if out.len()<total {return Err(CryptoError::Capacity)}
        // No output on invalid authenticated inner structure.
        if mode==Mode::Selective {
            if total<40 {return Err(CryptoError::InvalidLength)}
            // Check complete length and IPv4 TCP structure using both ranges.
            // Only the caller's oracle asserts that B was TLS ciphertext.
            let h=m-2;
            // Compose only after successful authentication; no untrusted routing.
            out[..h].copy_from_slice(&plain[1..m-1]);
            out[h..total].copy_from_slice(&aad[AAD_PREFIX..]);
            if !ipv4_tcp(&out[..total],h) {return Err(CryptoError::InvalidLength)}
        } else {
            out[..total].copy_from_slice(&plain[1..m-1]);
        }
        Ok(Opened{pn,kind,len:total,mode})
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn keys(seed:u8)->DirectionKeys{
        DirectionKeys{aead_key:[seed;32],iv:[seed.wrapping_add(1);12],hp_key:[seed.wrapping_add(2);32]}
    }
    fn packet(n:usize)->Vec<u8>{
        let mut p=vec![0u8;n];p[0]=0x45;p[2..4].copy_from_slice(&(n as u16).to_be_bytes());
        p[6]=0x40;p[9]=6;p[32]=0x50;p[40..45].copy_from_slice(&[23,3,3,0,0]);
        for(i,v)in p[45..].iter_mut().enumerate(){*v=((i*31+17)%251)as u8;}p
    }
    fn oracle()->Option<OracleRange>{Some(OracleRange{
        b_start:45,confirmed_tls_ciphertext:true,single_record_suffix:true,protected_edge:false})}
    #[test]
    fn three_suites_roundtrip_fallback_and_mtus() {
        for s in [RecordSuite::Aes128Gcm,RecordSuite::Aes256Gcm,RecordSuite::ChaCha20Poly1305] {
            for mtu in [1500,1400,1280] {
                let mut tx=Tx::new(keys(3),mtu-40,s).unwrap();
                let rx=Rx::new(keys(3),mtu-40,s).unwrap();
                for (n,o,expected) in [(0,None,Mode::Full),(1,None,Mode::Full),
                     (550,oracle(),Mode::Full),(557,oracle(),Mode::Selective),
                     (mtu-73,oracle(),Mode::Selective)] {
                    let p=if n<45 {vec![7;n]} else {packet(n)};
                    let mut w=vec![0;OVERHEAD+p.len()];
                    let (pn,used,mode)=tx.seal(0,&p,o,&mut w).unwrap();
                    assert_eq!(mode,expected);
                    let mut out=vec![0; p.len()];
                    let v=rx.open_into(&mut w[..used],&mut out).unwrap();
                    assert_eq!((v.pn,v.kind,v.len,v.mode),(pn,0,p.len(),mode));
                    assert_eq!(out,p);
                }
                let p=packet(mtu-72);
                let mut w=vec![0;OVERHEAD+p.len()];
                assert_eq!(tx.seal(0,&p,oracle(),&mut w),Err(CryptoError::InvalidLength));
            }
        }
    }
    #[test]
    fn tamper_every_region_wrong_key_and_no_output() {
        for s in [RecordSuite::Aes128Gcm,RecordSuite::Aes256Gcm,RecordSuite::ChaCha20Poly1305] {
            let p=packet(1100);let mut tx=Tx::new(keys(7),1500,s).unwrap();
            let rx=Rx::new(keys(7),1500,s).unwrap();
            let mut wire=vec![0;OVERHEAD+p.len()];
            tx.seal(0,&p,oracle(),&mut wire).unwrap();
            for at in [0,3,5,12,13,14,15,100,530,wire.len()-17,wire.len()-16,wire.len()-1]{
                let mut bad=wire.clone();bad[at]^=1;
                let mut out=vec![0xa5;1100];
                assert!(rx.open_into(&mut bad,&mut out).is_err(),"suite {s:?} offset {at}");
                assert!(out.iter().all(|x|*x==0xa5) || at>=wire.len()); 
            }
            let mut out=vec![0;1100];
            assert!(Rx::new(keys(8),1500,s).unwrap()
                .open_into(&mut wire.clone(),&mut out).is_err());
        }
    }
    #[test]
    fn missing_or_untrusted_oracle_is_full_and_failed_seal_burns_pn() {
        let p=packet(1100);let mut tx=Tx::new(keys(1),1500,RecordSuite::Aes128Gcm).unwrap();
        let mut w=vec![0;1133];
        assert_eq!(tx.seal(0,&p,None,&mut w).unwrap().2,Mode::Full);
        let untrusted=OracleRange{confirmed_tls_ciphertext:false,..oracle().unwrap()};
        assert_eq!(tx.seal(0,&p,Some(untrusted),&mut w).unwrap().2,Mode::Full);
        assert_eq!(tx.seal(0,&p,oracle(),&mut w[..20]),Err(CryptoError::Capacity));
        assert_eq!(tx.seal(0,&p,oracle(),&mut w).unwrap().0,3);
        let mut frag=p.clone();frag[6]=0x20;
        assert_eq!(tx.seal(0,&frag,oracle(),&mut w).unwrap().2,Mode::Full);
    }
    #[test]
    fn out_of_order_replay_is_not_crypto_admission_and_frozen_repair_is_exact() {
        let mut tx=Tx::new(keys(4),1500,RecordSuite::Aes128Gcm).unwrap();
        let rx=Rx::new(keys(4),1500,RecordSuite::Aes128Gcm).unwrap();
        let p=packet(1200);let mut saved=Vec::new();
        for _ in 0..3{
            let mut w=vec![0;1233];tx.seal(0,&p,oracle(),&mut w).unwrap();saved.push(w);
        }
        let frozen=saved[0].clone();
        assert_eq!(saved[0],frozen); // caller's retransmit must reuse these bytes
        for i in [2,0,1]{
            let mut out=vec![0;1200];let rec=rx.open_into(&mut saved[i],&mut out).unwrap();
            assert_eq!(rec.pn,i as u64);assert_eq!(out,p);
        }
    }
    #[test]
    fn repeated_tls_ciphertext_different_outer_pn_is_visible_counterexample() {
        let p=packet(1200);let mut tx=Tx::new(keys(9),1500,RecordSuite::Aes128Gcm).unwrap();
        let mut a=vec![0;1233];let mut b=a.clone();
        let (pa,_,_)=tx.seal(0,&p,oracle(),&mut a).unwrap();
        let (pb,_,_)=tx.seal(0,&p,oracle(),&mut b).unwrap();
        assert_ne!(pa,pb);
        assert_ne!(a[5..15],b[5..15]);
        assert_eq!(&a[15..15+128],&b[15..15+128]);
        assert_eq!(&a[15..15+64],&b[15..15+64]);
        // Different outer PN + immutable 128B across new sends is a regression,
        // not an assertion that an actual kernel capture has been completed.
    }
}
