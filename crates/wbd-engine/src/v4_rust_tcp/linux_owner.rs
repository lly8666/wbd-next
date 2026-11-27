//! Linux Normal business TCP owned by the existing native TX thread.
use std::{collections::{BTreeSet,HashMap},io,os::fd::{AsRawFd,FromRawFd,OwnedFd,RawFd},
    sync::{Arc,atomic::{AtomicBool,Ordering}},time::{Duration,Instant}};
use super::{flow::{ClientFlow,ClientOutput,ServerFlow},ipv4::{self,Packet,Tuple}};
use super::pktkit::vtcp::{flags,Segment};
use std::net::{Ipv4Addr,SocketAddrV4};

const IN:u32=1; const OUT:u32=4; const ERR:u32=8; const HUP:u32=16; const RDHUP:u32=0x2000;
const CE:i32=0x80000; const NB:i32=0x800;
#[cfg_attr(target_arch="x86_64",repr(C,packed))]
#[cfg_attr(not(target_arch="x86_64"),repr(C))]
#[derive(Clone,Copy)]
struct Event{events:u32,token:u64}
#[repr(C)]
struct PollFd{fd:i32,events:i16,revents:i16}
#[repr(C)]
struct Timespec{sec:i64,nsec:i64}
unsafe extern "C"{
    fn epoll_create1(flags:i32)->i32;
    fn epoll_ctl(ep:i32,op:i32,fd:i32,event:*mut Event)->i32;
    fn epoll_wait(ep:i32,events:*mut Event,max:i32,timeout:i32)->i32;
    fn eventfd(init:u32,flags:i32)->i32;
    fn ppoll(fds:*mut PollFd,n:usize,timeout:*const Timespec,mask:*const std::ffi::c_void)->i32;
    fn read(fd:i32,buf:*mut std::ffi::c_void,n:usize)->isize;
    fn write(fd:i32,buf:*const std::ffi::c_void,n:usize)->isize;
}
fn owned(fd:i32)->io::Result<OwnedFd>{
    if fd<0{Err(io::Error::last_os_error())}else{Ok(unsafe{OwnedFd::from_raw_fd(fd)})}
}
fn change(ep:RawFd,op:i32,fd:RawFd,token:u64,events:u32)->io::Result<()>{
    let mut ev=Event{events,token};
    if unsafe{epoll_ctl(ep,op,fd,&mut ev)}<0{Err(io::Error::last_os_error())}else{Ok(())}
}
/// Both existing ingress producers publish before signaling. Coalesce
/// readiness, not packets. The consumer clears before draining the queue.
pub(crate) struct Wake{fd:OwnedFd,armed:AtomicBool}
impl Wake{
    pub(crate) fn new()->io::Result<Arc<Self>>{
        Ok(Arc::new(Self{fd:owned(unsafe{eventfd(0,NB|CE)})?,armed:AtomicBool::new(false)}))
    }
    pub(crate) fn signal(&self){
        if self.armed.swap(true,Ordering::AcqRel){return}
        let one=1u64;
        loop{
            let n=unsafe{write(self.fd.as_raw_fd(),(&one as *const u64).cast(),8)};
            if n==8{return}
            if io::Error::last_os_error().kind()!=io::ErrorKind::Interrupted{return}
        }
    }
    fn clear(&self){
        let mut value=0u64;
        loop{
            let n=unsafe{read(self.fd.as_raw_fd(),(&mut value as *mut u64).cast(),8)};
            if n==8{break}
            if io::Error::last_os_error().kind()!=io::ErrorKind::Interrupted{break}
        }
        // Read before disarming: a producer that publishes in this gap
        // is seen by the following queue drain, and a later producer signals.
        self.armed.store(false,Ordering::Release);
    }
}
enum Flow{Client(ClientFlow),Server(ServerFlow)}
struct Entry{flow:Flow,tuple:Tuple,deadline:Option<Instant>,interest:u32}
impl Entry{
    fn deadline(&self)->Option<Instant>{match &self.flow{
        Flow::Client(f)=>f.next_deadline(),Flow::Server(f)=>f.next_deadline()}}
    fn finished(&self)->bool{match &self.flow{
        Flow::Client(f)=>f.finished(),Flow::Server(f)=>f.finished()}}
}
// Count real TCP at the already parsed ingress and serialized egress.
// No new parser, packet logging, worker or wake.
#[derive(Default,Debug)]
struct TcpWireCount{ack_only:u64,data:u64,data_bytes:u64,psh_data:u64,
    lt256:u64,lt1024:u64,ge1024:u64,control:u64}
impl TcpWireCount{
    fn add(&mut self,fl:u8,n:usize){
        if n!=0{
            self.data+=1;self.data_bytes+=n as u64;
            self.psh_data+=u64::from(fl&flags::PSH!=0);
            if n<256{self.lt256+=1}else if n<1024{self.lt1024+=1}else{self.ge1024+=1}
        }else if fl&flags::ACK!=0&&fl&(flags::SYN|flags::FIN|flags::RST)==0{
            self.ack_only+=1;
        }else{self.control+=1}
    }
    fn output(&mut self,packets:&[Vec<u8>]){
        for p in packets{
            let hdr=20+(p[32]>>4) as usize*4;
            self.add(p[33],p.len()-hdr);
        }
    }
}
pub(crate) struct Owner{
    server:bool,local_mtu:u16,middle_mtu:u16,
    ep:OwnedFd,wake:Arc<Wake>,next_id:u64,
    keys:HashMap<Tuple,u64>,flows:HashMap<u64,Entry>,
    deadlines:BTreeSet<(Instant,u64)>,scratch:Vec<u8>,
    local_in:TcpWireCount,local_out:TcpWireCount,middle_in:TcpWireCount,middle_out:TcpWireCount,
    probe_next:Option<Instant>,
    parity:bool,parse_scratch:Segment,
}
impl Owner{
    pub(crate) fn new(server:bool,local_mtu:u16,middle_mtu:u16,wake:Arc<Wake>)->io::Result<Self>{
        let ep=owned(unsafe{epoll_create1(CE)})?;
        change(ep.as_raw_fd(),1,wake.fd.as_raw_fd(),0,IN)?;
        Ok(Self{server,local_mtu,middle_mtu,ep,wake,next_id:1,keys:HashMap::new(),
            flows:HashMap::new(),deadlines:BTreeSet::new(),scratch:vec![0;65536],
            local_in:Default::default(),local_out:Default::default(),middle_in:Default::default(),middle_out:Default::default(),
            probe_next:std::env::var_os("WBD_M0_ACK_PROBE").map(|_|Instant::now()),
            parity:std::env::var_os("WBD_M0_LINUX_PARITY").as_deref()==Some(std::ffi::OsStr::new("1")),parse_scratch:Segment::default()})
    }
    fn insert(&mut self,tuple:Tuple,flow:Flow)->io::Result<()>{
        let id=self.next_id;self.next_id+=1;
        self.keys.insert(tuple,id);
        self.flows.insert(id,Entry{flow,tuple,deadline:None,interest:0});
        self.refresh(id)
    }
    fn refresh(&mut self,id:u64)->io::Result<()>{
        let e=self.flows.get_mut(&id).unwrap();
        if e.finished(){
            if let Some(d)=e.deadline.take(){self.deadlines.remove(&(d,id));}
            if let Flow::Server(f)=&e.flow{
                if e.interest!=0{change(self.ep.as_raw_fd(),2,f.socket().as_raw_fd(),id,0)?;}
            }
            self.keys.remove(&e.tuple);self.flows.remove(&id);return Ok(())
        }
        let next=e.deadline();if next!=e.deadline{
            if let Some(d)=e.deadline.take(){self.deadlines.remove(&(d,id));}
            if let Some(d)=next{self.deadlines.insert((d,id));}e.deadline=next;
        }
        if let Flow::Server(f)=&e.flow{
            let i=f.interest();
            let next=(if i.read{IN|RDHUP}else{0})|(if i.write{OUT}else{0});
            if next!=e.interest{
                let op=if e.interest==0{1}else if next==0{2}else{3};
                change(self.ep.as_raw_fd(),op,f.socket().as_raw_fd(),id,next)?;
                e.interest=next;
            }
        }
        Ok(())
    }
    /// Returns None for non-TCP or for server's normal TUN output.
    pub(crate) fn local(&mut self,ip:&[u8])->io::Result<Option<ClientOutput>>{
        if self.server{return Ok(None)}
        let Some(p)=Packet::parse_reuse(ip,&mut self.parse_scratch)? else{return Ok(None)};
        self.local_in.add(p.segment.flags,p.segment.payload.len());
        let mut out=ClientOutput::default();
        if let Some(&id)=self.keys.get(&p.tuple){
            let Flow::Client(f)=&mut self.flows.get_mut(&id).unwrap().flow else{unreachable!()};
            out=f.on_local(&p)?;self.refresh(id)?;
        }else if p.initial_syn(){
            let (f,o)=ClientFlow::open(&p,self.local_mtu,self.middle_mtu)?;
            self.insert(p.tuple,Flow::Client(f))?;out=o;
        }else if !p.segment.has_flag(flags::RST){
            if self.parity{eprintln!("WBD_M0_TCP_RESET_NO_FLOW leg=local tuple={:?} flags={} seq={} ack={}",p.tuple,p.segment.flags,p.segment.seq,p.segment.ack);}
            out.local.push(ipv4::reset_for(&p,self.local_mtu)?);
        }
        self.parse_scratch=p.segment;
        self.local_out.output(&out.local);self.middle_out.output(&out.tunnel);
        Ok(Some(out))
    }
    /// Caller is the same generation's post-authentication LINK path.
    pub(crate) fn middle(&mut self,ip:&[u8])->io::Result<ClientOutput>{
        let Some(p)=Packet::parse_reuse(ip,&mut self.parse_scratch)? else{return Err(io::ErrorKind::InvalidData.into())};
        self.middle_in.add(p.segment.flags,p.segment.payload.len());
        let mut out=ClientOutput::default();
        let tuple=if self.server{p.tuple}else{p.tuple.reverse()};
        if let Some(&id)=self.keys.get(&tuple){
            match &mut self.flows.get_mut(&id).unwrap().flow{
                Flow::Client(f)=>out=f.on_middle(&p)?,
                Flow::Server(f)=>out.tunnel=f.on_packet(&p)?,
            }
            self.refresh(id)?;
        }else if self.server&&p.initial_syn(){
            match ServerFlow::open(&p,self.middle_mtu){
                Ok((f,packets))=>{self.insert(tuple,Flow::Server(f))?;out.tunnel=packets;}
                Err(_)=>out.tunnel.push(ipv4::reset_for(&p,self.middle_mtu)?),
            }
        }else if !p.segment.has_flag(flags::RST){
            if self.parity{eprintln!("WBD_M0_TCP_RESET_NO_FLOW leg=middle tuple={:?} flags={} seq={} ack={}",p.tuple,p.segment.flags,p.segment.seq,p.segment.ack);}
            out.tunnel.push(ipv4::reset_for(&p,self.middle_mtu)?);
        }
        self.parse_scratch=p.segment;
        self.local_out.output(&out.local);self.middle_out.output(&out.tunnel);
        Ok(out)
    }
    /// Receipt for a generated inner DATA datagram at the actual TUN
    /// write attempt or original M1 slab acceptance boundary.
    pub(crate) fn admit(&mut self,local:bool,ip:&[u8],now:Instant)->io::Result<()>{
        self.admit_header(local,ip,ip.len(),now)
    }
    pub(crate) fn admit_header(&mut self,local:bool,ip:&[u8],packet_len:usize,now:Instant)->io::Result<()>{
        if !self.parity||ip.len()<40{return Ok(())}
        let h=20+usize::from(ip[32]>>4)*4;
        if h>=packet_len||ip[33]&(flags::SYN|flags::FIN|flags::RST)!=0{return Ok(())}
        let tuple=Tuple{src:SocketAddrV4::new(Ipv4Addr::new(ip[12],ip[13],ip[14],ip[15]),u16::from_be_bytes([ip[20],ip[21]])),dst:SocketAddrV4::new(Ipv4Addr::new(ip[16],ip[17],ip[18],ip[19]),u16::from_be_bytes([ip[22],ip[23]]))};
        let tuple=if local||self.server{tuple.reverse()}else{tuple};
        let Some(&id)=self.keys.get(&tuple)else{return Ok(())};
        let seq=u32::from_be_bytes(ip[24..28].try_into().unwrap());let len=(packet_len-h) as u32;
        let e=self.flows.get_mut(&id).unwrap();let changed=match &mut e.flow{Flow::Client(f)=>f.admit(local,seq,len,now),Flow::Server(f)=>f.admit(seq,len,now)};
        if changed{self.refresh(id)?;}Ok(())
    }
    // Experiment only: sample during existing owner service turns; no extra wake/deadline.
    fn probe(&mut self,now:Instant) {
        if !self.probe_next.is_some_and(|next|now>=next){return}
        self.probe_next=Some(now+Duration::from_secs(1));
        let wall_ns=std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_nanos();
        eprintln!("WBD_M0_TCP_OWNER wall_ns={} role={} flows={} deadlines={} local_in={:?} local_out={:?} middle_in={:?} middle_out={:?}",
            wall_ns,if self.server{"server"}else{"client"},self.flows.len(),self.deadlines.len(),self.local_in,self.local_out,self.middle_in,self.middle_out);
        for (&id,entry) in &self.flows {
            eprintln!("WBD_M0_TCP_FLOW wall_ns={} id={} tuple={:?} interest={} deadline_in_us={:?}",
                wall_ns,id,entry.tuple,entry.interest,entry.deadline.map(|d|d.saturating_duration_since(now).as_micros()));
            match &entry.flow{
                Flow::Client(f)=>f.probe(id,wall_ns),
                Flow::Server(f)=>f.probe(id,wall_ns),
            }
        }
    }
    /// Real readiness or earliest TCP/outer deadline. No per-flow scan.
    /// A zero duration services only already-ready work.
    pub(crate) fn service(&mut self,wait:Duration)->io::Result<ClientOutput>{
        let now=Instant::now();
        if self.parity&&!self.server&&wait.is_zero()&&self.deadlines.first().is_none_or(|(d,_)|*d>now){return Ok(ClientOutput::default());}
        let wait=self.deadlines.first().map_or(wait,|(d,_)|wait.min(d.saturating_duration_since(now)));
        if !wait.is_zero(){
            let mut fd=PollFd{fd:self.ep.as_raw_fd(),events:1,revents:0};
            let ts=Timespec{sec:wait.as_secs() as i64,nsec:wait.subsec_nanos() as i64};
            let n=unsafe{ppoll(&mut fd,1,&ts,std::ptr::null())};
            if n<0&&io::Error::last_os_error().kind()!=io::ErrorKind::Interrupted{return Err(io::Error::last_os_error())}
        }
        let mut out=ClientOutput::default();
        let mut events=[Event{events:0,token:0};32];
        let n=unsafe{epoll_wait(self.ep.as_raw_fd(),events.as_mut_ptr(),32,0)};
        if n<0{
            let e=io::Error::last_os_error();if e.kind()!=io::ErrorKind::Interrupted{return Err(e)}
        }
        for ev in events.iter().take(n.max(0) as usize){
            let id=ev.token;let bits=ev.events;
            if id==0{self.wake.clear();continue}
            let Some(e)=self.flows.get_mut(&id)else{continue};
            let Flow::Server(f)=&mut e.flow else{unreachable!()};
            out.tunnel.extend(f.on_socket_ready(bits&(IN|RDHUP|HUP|ERR)!=0,bits&(OUT|HUP|ERR)!=0,&mut self.scratch)?);
            self.refresh(id)?;
            if self.parity&&out.tunnel.len()+out.local.len()>=64{break;}
        }
        let now=Instant::now();
        // Each due connection at most once this turn; the next deadline
        // may legitimately be immediately ready and is served next turn.
        let due:Vec<_>=self.deadlines.range(..=(now,u64::MAX)).take(32).copied().collect();
        for (_,id) in due{
            let Some(e)=self.flows.get_mut(&id)else{continue};
            match &mut e.flow{
                Flow::Client(f)=>{let o=f.tick(now)?;out.local.extend(o.local);out.tunnel.extend(o.tunnel);}
                Flow::Server(f)=>out.tunnel.extend(f.tick(now)?),
            }
            self.refresh(id)?;
            if self.parity&&out.tunnel.len()+out.local.len()>=64{break;}
        }
        self.local_out.output(&out.local);self.middle_out.output(&out.tunnel);
        self.probe(Instant::now());
        Ok(out)
    }
}
impl Drop for Owner{
    fn drop(&mut self){
        eprintln!("WBD_DUAL_TCP_WIRE role={} local_in={:?} local_out={:?} middle_in={:?} middle_out={:?}",
            if self.server{"server"}else{"client"},self.local_in,self.local_out,self.middle_in,self.middle_out);
    }
}
