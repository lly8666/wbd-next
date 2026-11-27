//! Native WinXDP cold/steady carrier lease. One RX and one TX SPSC owner.
//! Native Go calls exist only before the authenticated Rust handoff.
use std::{ffi::c_void,ptr::NonNull,slice};
use crate::TxError;
use crate::windows_native_io::{wait_ready,WaitResult};
const BATCH:usize=32;
#[repr(C)]
#[derive(Clone,Copy)]
struct Frame{data:*const u8,len:usize}
extern "C"{
    fn wbd_xdp_driver_status()->i32;
    fn wbd_xdp_open_carrier(index:u32,ports:*const u16,count:u32,udp:i32,handles:*mut *mut c_void)->i32;
    fn wbd_xdp_rx_cold_read(raw:*mut c_void,dst:*mut u8,cap:usize)->i32;
    fn wbd_xdp_tx_cold_write(raw:*mut c_void,bytes:*const u8,len:usize)->i32;
    fn wbd_xdp_rx_close(raw:*mut c_void);
    fn wbd_xdp_tx_close(raw:*mut c_void);
    fn wbd_xdp_rx_borrow(raw:*mut c_void,frames:*mut Frame,max:usize)->usize;
    fn wbd_xdp_rx_release(raw:*mut c_void)->i32;
    fn wbd_xdp_rx_events_after_wait(raw:*mut c_void,events:*mut usize,signaled:u32)->i32;
}
pub fn cold_open(index:u32,port:u16)->Result<(usize,usize),TxError>{
    cold_open_ports(index,&[port],false)
}
pub fn cold_open_ports(index:u32,ports:&[u16],udp:bool)->Result<(usize,usize),TxError>{
    let mut handles=[std::ptr::null_mut();2];
    if unsafe{wbd_xdp_open_carrier(index,ports.as_ptr(),ports.len() as u32,udp as i32,handles.as_mut_ptr())}==0{
        return Err(TxError::IoFailed)
    }
    Ok((handles[0] as usize,handles[1] as usize))
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
pub struct XdpRx{owner:NonNull<c_void>,failed:bool,signaled:u32}
unsafe impl Send for XdpRx{}
impl XdpRx{
    pub unsafe fn from_cold(raw:usize)->Result<Self,TxError>{
        let owner=NonNull::new(raw as *mut c_void).ok_or(TxError::IoFailed)?;
        Ok(Self{owner,failed:false,signaled:0})
    }
    /// Service ready descriptors before arming a driver wait. Under load
    /// this avoids one notify IOCTL + wait syscall for every RX quantum.
    /// Empty rings still use the original event/deadline wait, never poll.
    pub fn next_turn(&mut self,stop:usize,early:usize,wait_ms:u32)->Result<RxTurn<'_>,TxError>{
        if self.failed{return Err(TxError::IoFailed)}
        let mut frames=[Frame{data:std::ptr::null(),len:0};BATCH];
        let mut count=unsafe{wbd_xdp_rx_borrow(self.owner.as_ptr(),frames.as_mut_ptr(),BATCH)};
        if count==0{
            let mut handles=[0usize;crate::windows_native_io::MAX_WAIT_HANDLES];
            handles[0]=stop;
            let signaled=std::mem::take(&mut self.signaled);
            let queue_count=unsafe{wbd_xdp_rx_events_after_wait(self.owner.as_ptr(),handles.as_mut_ptr().add(1),signaled)};
            if queue_count<=0{return Err(TxError::IoFailed)}
            let queue_count=queue_count as usize;
            handles[queue_count+1]=early;
            match wait_ready(&handles[..queue_count+2],wait_ms){
                Ok(WaitResult::Ready(0))=>return Ok(RxTurn::Stop),
                Ok(WaitResult::Ready(i))=>{if i<=queue_count{self.signaled=i as u32;}},
                Ok(WaitResult::Timeout)=>return Ok(RxTurn::Idle),
                _=>return Err(TxError::IoFailed),
            }
            count=unsafe{wbd_xdp_rx_borrow(self.owner.as_ptr(),frames.as_mut_ptr(),BATCH)};
        }
        Ok(RxTurn::Ready(RxBatch{owner:self,frames,count}))
    }
}
pub enum RxTurn<'a>{
    Ready(RxBatch<'a>),
    Stop,
    Idle,
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

pub fn driver_status()->i32{unsafe{wbd_xdp_driver_status()}}
