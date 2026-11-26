//! Experimental WinXDP TX-only carrier. Official SDK shim owns a single
//! AF_XDP socket, registered UMEM and SPSC rings; no Go hot path.
use std::{ffi::c_void,ptr::NonNull,slice};
use crate::{TxBatchOutcome,TxError};
const BATCH:usize=16;
const CHUNK:usize=4096;
extern "C"{
    fn wbd_xdp_tx_open(ip:*const u8,mac:*const u8)->*mut c_void;
    fn wbd_xdp_tx_reserve(owner:*mut c_void,count:usize,frames:*mut *mut u8)->i32;
    fn wbd_xdp_tx_publish(owner:*mut c_void,lengths:*const usize)->i32;
    fn wbd_xdp_tx_close(owner:*mut c_void);
    fn wbd_xdp_tx_report(owner:*mut c_void);
}
pub struct XdpTx{owner:NonNull<c_void>,failed:bool,owned:bool}
unsafe impl Send for XdpTx{}
impl XdpTx{
    pub fn open(ip:[u8;4],mac:[u8;6])->Result<Self,TxError>{
        let owner=NonNull::new(unsafe{wbd_xdp_tx_open(ip.as_ptr(),mac.as_ptr())})
            .ok_or(TxError::IoFailed)?;
        Ok(Self{owner,failed:false,owned:true})
    }
    /// The original cold endpoint retains the socket and UMEM through join.
    pub unsafe fn from_cold(raw:usize)->Result<Self,TxError>{
        let owner=NonNull::new(raw as *mut c_void).ok_or(TxError::IoFailed)?;
        Ok(Self{owner,failed:false,owned:false})
    }
    pub fn reserve(&mut self,count:usize)->Result<XdpBatch<'_>,TxError>{
        if self.failed{return Err(TxError::IoFailed)}
        let mut frames=[std::ptr::null_mut();BATCH];
        if unsafe{wbd_xdp_tx_reserve(self.owner.as_ptr(),count,frames.as_mut_ptr())}==0{
            return Err(TxError::WouldBlock)
        }
        Ok(XdpBatch{tx:self,frames,count})
    }
    pub fn send_batch(&mut self,frames:&[&[u8]])->TxBatchOutcome{
        let mut batch=match self.reserve(frames.len()){
            Ok(b)=>b,Err(e)=>return TxBatchOutcome{accepted_prefix:0,uncertain_index:None,error:Some(e)},
        };
        let mut lengths=[0usize;BATCH];
        for (i,frame) in frames.iter().enumerate(){
            lengths[i]=frame.len();
            batch.frame(i)[..frame.len()].copy_from_slice(frame);
        }
        batch.submit(&lengths[..frames.len()])
    }
    pub fn failed(&self)->bool{self.failed}
}
impl Drop for XdpTx{
    fn drop(&mut self){unsafe{if self.owned{wbd_xdp_tx_close(self.owner.as_ptr())}else{wbd_xdp_tx_report(self.owner.as_ptr())}}}
}
/// Exclusive, unpublished chunk loan. No ring index or free chunk changes
/// until submit; a failed staging turn simply drops the unpublished borrow.
pub struct XdpBatch<'a>{tx:&'a mut XdpTx,frames:[*mut u8;BATCH],count:usize}
impl XdpBatch<'_>{
    #[inline]
    pub fn frame(&mut self,i:usize)->&mut [u8]{
        // C reservation returned count distinct free UMEM chunks. Borrow
        // tied to &mut self; no descriptor is published during this loan.
        unsafe{slice::from_raw_parts_mut(self.frames[..self.count][i],CHUNK)}
    }
    pub fn submit(self,lengths:&[usize])->TxBatchOutcome{
        assert_eq!(lengths.len(),self.count);
        // Existing bounded packet builders supply lengths <= MAX_LINK.
        assert!(lengths.iter().all(|&n|n<=CHUNK));
        let ok=unsafe{wbd_xdp_tx_publish(self.tx.owner.as_ptr(),lengths.as_ptr())}!=0;
        self.tx.failed=!ok;
        // Published prefix is an accepted kernel ring loan, not a completed
        // transmit or remote receipt. STOP log keeps completion separate.
        TxBatchOutcome::copied_all(self.count)
    }
}
