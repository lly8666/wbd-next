//! Experimental Linux TCP exit: kernel TCP endpoints, two kernel pipes,
 //! single readiness owner. No WBD packet reader or user-space payload copy.
use std::{collections::HashMap, ffi::{c_int,c_void}, io, net::{TcpListener,TcpStream,SocketAddr},
    os::fd::{AsRawFd,FromRawFd,OwnedFd,RawFd}, thread::{self,JoinHandle}};
const IN:u32=1; const OUT:u32=4; const ERR:u32=8; const HUP:u32=16; const RDHUP:u32=0x2000;
const NB:i32=0x800; const CE:i32=0x80000;
const EINTR:i32=4; const EAGAIN:i32=11; const EINPROGRESS:i32=115;
const QUANTUM:usize=65536;
#[cfg_attr(target_arch="x86_64",repr(C,packed))]
#[cfg_attr(not(target_arch="x86_64"),repr(C))]
#[derive(Clone,Copy)]
struct Event { events:u32, token:u64 }
#[repr(C)]
struct Addr4 { family:u16, port:u16, addr:u32, pad:[u8;8] }
unsafe extern "C" {
    fn epoll_create1(flags:c_int)->c_int;
    fn epoll_ctl(ep:c_int,op:c_int,fd:c_int,event:*mut Event)->c_int;
    fn epoll_wait(ep:c_int,events:*mut Event,max:c_int,timeout:c_int)->c_int;
    fn eventfd(init:u32,flags:c_int)->c_int;
    fn pipe2(fds:*mut c_int,flags:c_int)->c_int;
    fn socket(domain:c_int,kind:c_int,protocol:c_int)->c_int;
    fn connect(fd:c_int,addr:*const c_void,len:u32)->c_int;
    fn getsockopt(fd:c_int,level:c_int,name:c_int,val:*mut c_void,len:*mut u32)->c_int;
    fn setsockopt(fd:c_int,level:c_int,name:c_int,val:*const c_void,len:u32)->c_int;
    fn fcntl(fd:c_int,cmd:c_int,...)->c_int;
    fn splice(input:c_int,inoff:*mut i64,output:c_int,outoff:*mut i64,len:usize,flags:u32)->isize;
    fn shutdown(fd:c_int,how:c_int)->c_int;
    fn write(fd:c_int,buf:*const c_void,len:usize)->isize;
}
fn fd(n:i32)->io::Result<OwnedFd>{if n<0{Err(io::Error::last_os_error())}else{Ok(unsafe{OwnedFd::from_raw_fd(n)})}}
fn ok(n:i32)->io::Result<()>{if n<0{Err(io::Error::last_os_error())}else{Ok(())}}
fn change(ep:RawFd,op:i32,s:RawFd,token:u64,events:u32)->io::Result<()> {
    let mut e=Event{events,token};ok(unsafe{epoll_ctl(ep,op,s,&mut e)})
}
fn get_error(s:RawFd)->io::Result<()> {
    let mut e=0i32;let mut len=4u32;
    ok(unsafe{getsockopt(s,1,4,(&mut e as *mut i32).cast(),&mut len)})?;
    if e==0{Ok(())}else{Err(io::Error::from_raw_os_error(e))}
}
fn set_cc(s:RawFd,cc:&[u8])->io::Result<()> {
    ok(unsafe{setsockopt(s,6,13,cc.as_ptr().cast(),cc.len() as u32)})
}
fn read_cc(s:RawFd)->io::Result<String>{
    let mut b=[0u8;32];let mut n=b.len() as u32;
    ok(unsafe{getsockopt(s,6,13,b.as_mut_ptr().cast(),&mut n)})?;
    let n=b.iter().position(|v|*v==0).unwrap_or(b.len());
    Ok(String::from_utf8_lossy(&b[..n]).into_owned())
}
fn connect_target(target:SocketAddr)->io::Result<(OwnedFd,bool)>{
    let SocketAddr::V4(a)=target else{return Err(io::Error::new(io::ErrorKind::InvalidInput,"IPv4 only"))};
    let s=fd(unsafe{socket(2,1|NB|CE,6)})?;
    let addr=Addr4{family:2,port:a.port().to_be(),addr:u32::from_ne_bytes(a.ip().octets()),pad:[0;8]};
    let n=unsafe{connect(s.as_raw_fd(),(&addr as *const Addr4).cast(),16)};
    if n==0{return Ok((s,true))}
    let e=io::Error::last_os_error();
    if e.raw_os_error()==Some(EINPROGRESS){Ok((s,false))}else{Err(e)}
}
struct Pipe{r:OwnedFd,w:OwnedFd,pending:usize,eof:bool,bytes:u64}
impl Pipe{
    fn new()->io::Result<Self>{
        let mut f=[-1;2];ok(unsafe{pipe2(f.as_mut_ptr(),NB|CE)})?;
        let r=fd(f[0])?;let w=fd(f[1])?;
        // Best effort increase from small default pipe capacity, no payload copy.
        unsafe{fcntl(w.as_raw_fd(),1031,QUANTUM as c_int)};
        Ok(Self{r,w,pending:0,eof:false,bytes:0})
    }
    fn pump(&mut self,src:RawFd,dst:RawFd)->io::Result<()> {
        if self.eof{return Ok(())}
        let mut budget=QUANTUM*4;
        while budget>0 {
            if self.pending==0 {
                match move_bytes(src,self.w.as_raw_fd(),budget.min(QUANTUM))?{
                    None=>break,
                    Some(0)=>{self.eof=true;unsafe{shutdown(dst,1)};break},
                    Some(n)=>self.pending=n,
                }
            }
            match move_bytes(self.r.as_raw_fd(),dst,self.pending)?{
                None=>break,
                Some(0)=>return Err(io::Error::new(io::ErrorKind::WriteZero,"splice pipe drain")),
                Some(n)=>{self.pending-=n;self.bytes+=n as u64;budget=budget.saturating_sub(n)}
            }
        }
        Ok(())
    }
}
fn move_bytes(a:RawFd,b:RawFd,n:usize)->io::Result<Option<usize>>{
    loop {
        let k=unsafe{splice(a,std::ptr::null_mut(),b,std::ptr::null_mut(),n,3)};
        if k>=0{return Ok(Some(k as usize))}
        let e=io::Error::last_os_error();
        match e.raw_os_error(){Some(EINTR)=>continue,Some(EAGAIN)=>return Ok(None),_=>return Err(e)}
    }
}
struct Flow{client:TcpStream,remote:OwnedFd,ready:bool,up:Pipe,down:Pipe,interest:[u32;2]}
impl Flow{
    fn sockets(&self)->[RawFd;2]{[self.client.as_raw_fd(),self.remote.as_raw_fd()]}
    fn desired(&self)->[u32;2]{
        if !self.ready{return [0,OUT]}
        let read=|p:&Pipe|if !p.eof&&p.pending==0{IN|RDHUP}else{0};
        let wr=|p:&Pipe|if p.pending>0{OUT}else{0};
        [read(&self.up)|wr(&self.down),read(&self.down)|wr(&self.up)]
    }
    fn service(&mut self,side:usize,events:u32)->io::Result<bool>{
        let [c,r]=self.sockets();
        if !self.ready{
            if side!=1{return Ok(true)}
            get_error(r)?;self.ready=true;
        }
        if events&ERR!=0{get_error(if side==0{c}else{r})?}
        self.up.pump(c,r)?;self.down.pump(r,c)?;
        Ok(!(self.up.eof&&self.down.eof))
    }
    fn update(&mut self,ep:RawFd,id:u64,first:bool)->io::Result<()>{
        let wanted=self.desired();
        for (i,s) in self.sockets().into_iter().enumerate(){
            if first||wanted[i]!=self.interest[i]{
                change(ep,if first{1}else{3},s,id*2+i as u64,wanted[i])?;
                self.interest[i]=wanted[i];
            }
        }
        Ok(())
    }
}
fn run(listener:TcpListener,ep:OwnedFd,stop:RawFd,cc:Vec<u8>)->io::Result<()>{
    let e=ep.as_raw_fd();
    let mut flows=HashMap::<u64,Flow>::new();let mut id=1u64;
    let mut events=[Event{events:0,token:0};128];
    loop{
        let n=unsafe{epoll_wait(e,events.as_mut_ptr(),events.len() as i32,-1)};
        if n<0{let er=io::Error::last_os_error();if er.raw_os_error()==Some(EINTR){continue}return Err(er)}
        for ev in events.iter().take(n as usize){
            let token=ev.token;let bits=ev.events;
            if token==1 { // stop eventfd
                for (_,f) in flows.drain(){eprintln!("WBD_TCP_SPLICE_DONE up={} down={}",f.up.bytes,f.down.bytes)}
                let _=stop;return Ok(())
            }
            if token==0{
                for _ in 0..32{
                    let c=match listener.accept(){Ok((s,_))=>s,Err(x) if x.kind()==io::ErrorKind::WouldBlock=>break,Err(x)=>return Err(x)};
                    if let Err(x)=(|| ->io::Result<()>{
                        c.set_nonblocking(true)?;
                        let target=c.local_addr()?;
                        set_cc(c.as_raw_fd(),&cc)?;
                        let actual=read_cc(c.as_raw_fd())?;
                        let (remote,ready)=connect_target(target)?;
                        let mut f=Flow{client:c,remote,ready,up:Pipe::new()?,down:Pipe::new()?,interest:[0;2]};
                        id+=1;
                        f.update(e,id,true)?;
                        eprintln!("WBD_TCP_SPLICE_ACCEPT target={} cc={}",target,actual);
                        flows.insert(id,f);Ok(())
                    })(){eprintln!("WBD_TCP_SPLICE_CONNECT_ERROR {x}")}
                }
                continue
            }
            let key=token/2;
            let outcome=match flows.get_mut(&key){
                None=>continue,
                Some(f)=>f.service((token%2) as usize,bits).and_then(|live|{
                    if live{f.update(e,key,false)?}Ok(live)
                }),
            };
            if !matches!(outcome,Ok(true)){
                if let Some(f)=flows.remove(&key){
                    eprintln!("WBD_TCP_SPLICE_DONE up={} down={} result={:?}",f.up.bytes,f.down.bytes,outcome);
                }
            }
        }
    }
}
struct Owner{stop:OwnedFd,thread:JoinHandle<io::Result<()>>}
/// Cold-only C ABI; duplicates listener and owns all accepted sockets.
#[no_mangle]
pub unsafe extern "C" fn wbd_linux_tcp_splice_start(listener:i32,cc:*const std::ffi::c_char)->*mut c_void{
    let start=|| ->io::Result<Owner>{
        let cc=unsafe{std::ffi::CStr::from_ptr(cc)}.to_bytes_with_nul().to_vec();
        let l=fd(unsafe{fcntl(listener,1030,0)})?;
        let listener=TcpListener::from(l);listener.set_nonblocking(true)?;
        let ep=fd(unsafe{epoll_create1(CE)})?;
        let stop=fd(unsafe{eventfd(0,NB|CE)})?;
        let stopfd=stop.as_raw_fd();
        change(ep.as_raw_fd(),1,listener.as_raw_fd(),0,IN)?;
        change(ep.as_raw_fd(),1,stopfd,1,IN)?;
        let thread=thread::Builder::new().name("wbd-tcp-splice".into()).spawn(move||run(listener,ep,stopfd,cc))?;
        Ok(Owner{stop,thread})
    };
    match start(){Ok(o)=>Box::into_raw(Box::new(o)).cast(),Err(e)=>{eprintln!("WBD_TCP_SPLICE_START_ERROR {e}");std::ptr::null_mut()}}
}
#[no_mangle]
pub unsafe extern "C" fn wbd_linux_tcp_splice_stop(p:*mut c_void)->i32{
    let o=unsafe{Box::from_raw(p.cast::<Owner>())};
    let one=1u64;
    loop{
        let n=unsafe{write(o.stop.as_raw_fd(),(&one as *const u64).cast(),8)};
        if n==8{break}
        if io::Error::last_os_error().raw_os_error()!=Some(EINTR){return -1}
    }
    match o.thread.join(){Ok(Ok(()))=>0,_=>-1}
}
