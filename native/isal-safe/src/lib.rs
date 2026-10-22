//! Separate M0-owned safe ISA-L wrapper: codec itself forbids unsafe.
//! Test-only native opt-in: no default production ABI or acceleration claim.
#![deny(unsafe_op_in_unsafe_fn)]
#[derive(Debug,PartialEq,Eq)]
pub enum NativeError {Unavailable,Profile,Shape,Length,Alias}
const MAX:usize=20;
#[cfg(feature="native")]
unsafe extern "C" {
 fn ec_init_tables(k:i32,r:i32,a:*const u8,t:*mut u8);
 fn ec_encode_data(len:i32,k:i32,r:i32,t:*const u8,data:*mut *mut u8,dest:*mut *mut u8);
}
pub struct Tables{
 k:usize,r:usize,
 #[cfg(feature="native")] tbl:Vec<u8>,
}
impl Tables{
 pub fn new(k:usize,r:usize,coeff:&[u8])->Result<Self,NativeError>{
  if k==0||r==0||k>MAX||r>MAX{return Err(NativeError::Profile)}
  if coeff.len()!=k*r{return Err(NativeError::Shape)}
  #[cfg(feature="native")]{
   let mut tbl=vec![0u8;k*r*32];
   unsafe{ec_init_tables(k as i32,r as i32,coeff.as_ptr(),tbl.as_mut_ptr())}
   Ok(Self{k,r,tbl})
  }
  #[cfg(not(feature="native"))]{let _=coeff;Err(NativeError::Unavailable)}
 }
 /// Original byte matrix supplied by caller; no default Cauchy matrix.
 /// Caller may fall back to scalar on Length<64; no dynamic CPU win claim.
 pub fn encode(&self,src:&[&[u8]],dst:&mut [&mut[u8]])->Result<(),NativeError>{
  if src.len()!=self.k||dst.len()!=self.r{return Err(NativeError::Shape)}
  let n=src.first().map_or(0,|b|b.len());
  if !(64..=65_535).contains(&n){return Err(NativeError::Length)}
  if src.iter().any(|b|b.len()!=n)||dst.iter().any(|b|b.len()!=n){return Err(NativeError::Shape)}
  let mut ranges=[(0usize,0usize);40];
  for (i,b) in src.iter().enumerate(){
   let x=b.as_ptr() as usize;ranges[i]=(x,x.checked_add(n).ok_or(NativeError::Alias)?);
  }
  for (j,b) in dst.iter().enumerate(){
   let x=b.as_ptr() as usize;ranges[self.k+j]=(x,x.checked_add(n).ok_or(NativeError::Alias)?);
  }
  for i in 0..self.k+self.r{for j in i+1..self.k+self.r{
   if ranges[i].0<ranges[j].1&&ranges[j].0<ranges[i].1{return Err(NativeError::Alias)}
  }}
  #[cfg(feature="native")]{
   let mut data=[std::ptr::null_mut::<u8>();MAX];let mut coding=[std::ptr::null_mut::<u8>();MAX];
   for (i,b) in src.iter().enumerate(){data[i]=b.as_ptr() as *mut u8;}
   for (j,b) in dst.iter_mut().enumerate(){coding[j]=b.as_mut_ptr();}
   // Synchronous call. C reads k disjoint sources and writes r exclusive
   // destination slices of checked length; no pointer escapes this call.
   unsafe{ec_encode_data(n as i32,self.k as i32,self.r as i32,self.tbl.as_ptr(),data.as_mut_ptr(),coding.as_mut_ptr())}
   Ok(())
  }
  #[cfg(not(feature="native"))]{Err(NativeError::Unavailable)}
 }
}
#[cfg(test)]mod tests{
 use super::*;
 #[test]fn reject_invalid(){
  assert!(matches!(Tables::new(0,1,&[]),Err(NativeError::Profile)));
  assert!(matches!(Tables::new(2,1,&[1]),Err(NativeError::Shape)));
 }
 #[test]#[cfg(feature="native")]fn actual_intel_library_xor(){
  let tbl=Tables::new(2,1,&[1,1]).unwrap();
  let a=[1u8;65];let b=[2u8;65];let mut out=[0u8;65];
  tbl.encode(&[&a,&b],&mut [&mut out]).unwrap();assert_eq!(out,[3u8;65]);
  println!("REAL_ISAL_V2311_EC_ENCODE_DATA_PASS");
 }
 #[test]
 #[cfg(all(feature="native",target_arch="aarch64"))]
 fn actual_arm64_neon_backend_bytes_match_dispatch() {
  // Fixed upstream ISA-L exports this real AArch64 SIMD implementation.
  // It is called directly: this proves execution, not that every AUTO call
  // selected NEON rather than SVE or basic on this particular CPU.
  assert!(std::arch::is_aarch64_feature_detected!("neon"));
  unsafe extern "C" {
   fn ec_encode_data_neon(len:i32,k:i32,rows:i32,t:*const u8,
     data:*mut *mut u8,dest:*mut *mut u8);
  }
  let tables=Tables::new(2,1,&[1,1]).unwrap();
  let a=[0x55u8;128];let b=[0xaau8;128];
  let mut native=[0u8;128];let mut dispatched=[0u8;128];
  let mut src=[a.as_ptr() as *mut u8,b.as_ptr() as *mut u8];
  let mut dst=[native.as_mut_ptr()];
  unsafe {ec_encode_data_neon(128,2,1,tables.tbl.as_ptr(),src.as_mut_ptr(),dst.as_mut_ptr());}
  tables.encode(&[&a,&b],&mut [&mut dispatched]).unwrap();
  assert_eq!(native,[0xff;128]);
  assert_eq!(native,dispatched);
  println!("REAL_ISAL_ARM64_NEON_EXPLICIT_EQUIVALENCE_PASS");
 }

}
