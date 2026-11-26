//! Native WinXDP cold/steady carrier lease. One RX and one TX SPSC owner.
//! Native Go calls exist only before the authenticated Rust handoff.
use std::{ffi::c_void,ptr::NonNull,slice};
use crate::TxError;
const BATCH:usize=32;
#[repr(C)]
#[derive(Clone,Copy)]
struct Frame{data:*const u8,len:usize}
extern "C"{
    fn wbd_xdp_rx_open(index:u32,port:u16)->*mut c_void;
    fn wbd_xdp_tx_open_index(index:u32)->*mut c_void;
    fn wbd_xdp_rx_cold_read(raw:*mut c_void,dst:*mut u8,cap:usize)->i32;
    fn wbd_xdp_tx_cold_write(raw:*mut c_void,bytes:*const u8,len:usize)->i32;
    fn wbd_xdp_rx_close(raw:*mut c_void);
    fn wbd_xdp_tx_close(raw:*mut c_void);
    fn wbd_xdp_rx_borrow(raw:*mut c_void,frames:*mut Frame,max:usize)->usize;
    fn wbd_xdp_rx_release(raw:*mut c_void)->i32;
    fn wbd_xdp_rx_arm(raw:*mut c_void)->*mut c_void;
}
pub fn cold_open(index:u32,port:u16)->Result<(usize,usize),TxError>{
    let rx=NonNull::new(unsafe{wbd_xdp_rx_open(index,port)}).ok_or(TxError::IoFailed)?;
    let tx=match NonNull::new(unsafe{wbd_xdp_tx_open_index(index)}){
        Some(v)=>v,None=>{unsafe{wbd_xdp_rx_close(rx.as_ptr())};return Err(TxError::IoFailed)}
    };
    Ok((rx.as_ptr() as usize,tx.as_ptr() as usize))
}
pub unsafe fn cold_read(raw:usize,dst:*mut u8,cap:usize)->i32{
    unsafe{wbd_xdp_rx_cold_read(raw as *mut c_void,dst,cap)}
}
pub unsafe fn cold_write(raw:usize,bytes:*const u8,len:usize)->i32{
    unsafe{wbd_xdp_tx_cold_write(raw as *mut c_void,bytes,len)}
}
pub unsafe fn close_after_join(rx:usize,tx:usize){
    unsafe{wbd_xdp_rx_close(rx as *mut c_void);wbd_xdp_tx_close(tx as *mut c_void)}
}
pub struct XdpRx{owner:NonNull<c_void>,failed:bool}
unsafe impl Send for XdpRx{}
impl XdpRx{
    pub unsafe fn from_cold(raw:usize)->Result<Self,TxError>{
        let owner=NonNull::new(raw as *mut c_void).ok_or(TxError::IoFailed)?;
        Ok(Self{owner,failed:false})
    }
    /// One overlapped XSK wait, reused across Stop/Direct/early wakeups.
    pub fn arm(&mut self)->Result<usize,TxError>{
        if self.failed{return Err(TxError::IoFailed)}
        NonNull::new(unsafe{wbd_xdp_rx_arm(self.owner.as_ptr())})
            .map(|v|v.as_ptr() as usize).ok_or(TxError::IoFailed)
    }
    pub fn borrow(&mut self)->RxBatch<'_>{
        let mut frames=[Frame{data:std::ptr::null(),len:0};BATCH];
        let count=unsafe{wbd_xdp_rx_borrow(self.owner.as_ptr(),frames.as_mut_ptr(),BATCH)};
        RxBatch{owner:self,frames,count}
    }
}
/// RX descriptor loan. One release/fill publication for a ready batch,
/// including all early returns, not one C call or packet copy per frame.
pub struct RxBatch<'a>{owner:&'a mut XdpRx,frames:[Frame;BATCH],count:usize}
impl RxBatch<'_>{
    pub fn len(&self)->usize{self.count}
    #[inline] pub fn frame(&self,i:usize)->&[u8]{
        let f=self.frames[..self.count][i];
        unsafe{slice::from_raw_parts(f.data,f.len)}
    }
}
impl Drop for RxBatch<'_>{
    fn drop(&mut self){
        if self.count>0&&unsafe{wbd_xdp_rx_release(self.owner.owner.as_ptr())}==0{
            self.owner.failed=true;
        }
    }
}
