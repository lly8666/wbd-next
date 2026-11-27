//go:build windows

package faketcp

// WinXDP cold endpoint only. The original packet codec is reused unchanged.
// Once TakeNative joins the Go readers/writers, Rust uses these same rings
// directly; no Go per-packet FFI in the steady path.
import (
 "fmt"
 "runtime"
 "sync"
 "syscall"
 "unsafe"
)

type XdpEndpoint struct {
 cfg NpcapConfig
 dll *syscall.DLL
 read,write,close *syscall.Proc
 handles [2]uintptr
 gate *npcapCallGate
 sendMu sync.Mutex
 ipID uint16
 gameIDs [4]uint16
 gameCfgs []NpcapConfig
}

// The production DLL must export this WinXDP cold entry.
func OpenXdpEndpoint(path string,index uint32,cfg NpcapConfig)(*XdpEndpoint,bool,error){
 dll,err:=syscall.LoadDLL(path)
 if err!=nil{return nil,false,err}
 open,err:=dll.FindProc("wbd_m0_win_xdp_open")
 if err!=nil{_ = dll.Release();return nil,false,nil}
 if err=cfg.Validate();err!=nil{_ = dll.Release();return nil,true,err}
 read,err:=dll.FindProc("wbd_m0_win_xdp_read")
 if err!=nil{_ = dll.Release();return nil,true,err}
 write,err:=dll.FindProc("wbd_m0_win_xdp_write")
 if err!=nil{_ = dll.Release();return nil,true,err}
 closeProc,err:=dll.FindProc("wbd_m0_win_xdp_close")
 if err!=nil{_ = dll.Release();return nil,true,err}
 e:=&XdpEndpoint{cfg:cfg,dll:dll,read:read,write:write,close:closeProc,gate:newNpcapCallGate(cfg.Generation),ipID:1}
 rc,_,_:=open.Call(uintptr(index),uintptr(cfg.Flow.LocalPort),uintptr(unsafe.Pointer(&e.handles[0])))
 runtime.KeepAlive(e)
 if int32(rc)!=0{_ = dll.Release();return nil,true,fmt.Errorf("WinXDP open rc=%d",int32(rc))}
 fmt.Printf("WBD_XDP_COLD_OWNER_READY ifindex=%d port=%d\n",index,cfg.Flow.LocalPort)
 return e,true,nil
}
func(e *XdpEndpoint) ReadSegment(generation uint64)(Segment,[]byte,error){
 if err:=e.gate.begin(generation);err!=nil{return Segment{},nil,err}
 defer e.gate.end()
 var frame [4096]byte
 for !e.gate.isClosed(){
  rc,_,_:=e.read.Call(e.handles[0],uintptr(unsafe.Pointer(&frame[0])),uintptr(len(frame)))
  runtime.KeepAlive(&frame)
  n:=int32(rc)
  if n<0{return Segment{},nil,fmt.Errorf("WinXDP cold read rc=%d",n)}
  if n==0{continue}
  seg,packet,ok,err:=decodeNpcapInbound(frame[:int(n)],e.cfg.Flow)
  if err!=nil{return Segment{},nil,err}
  if ok{return seg,packet,nil}
 }
 return Segment{},nil,ErrNpcapClosed
}
func(e *XdpEndpoint) WriteSegment(generation uint64,seg Segment)([]byte,error){
 if err:=e.gate.begin(generation);err!=nil{return nil,err}
 defer e.gate.end()
 e.sendMu.Lock();defer e.sendMu.Unlock()
 packet,frame,err:=encodeNpcapOutbound(seg,e.cfg,e.ipID)
 if err!=nil{return nil,err}
 e.ipID++
 rc,_,_:=e.write.Call(e.handles[1],uintptr(unsafe.Pointer(&frame[0])),uintptr(len(frame)))
 runtime.KeepAlive(frame)
 if int32(rc)!=1{return nil,fmt.Errorf("WinXDP cold write rc=%d",int32(rc))}
 return packet,nil
}
func(e *XdpEndpoint) TakeNative(generation uint64)([2]uintptr,error){
 if generation!=e.cfg.Generation{return [2]uintptr{},ErrNpcapStaleGeneration}
 if !e.gate.close(){return [2]uintptr{},ErrNpcapClosed}
 e.gate.wait()
 // RX's bounded synchronous wait and all TX calls are joined. Nothing
 // reopens the program/socket or drains pending frames in a second reader.
 fmt.Println("WBD_XDP_COLD_HANDOFF same_rx_tx_umem=1")
 return e.handles,nil
}
func(e *XdpEndpoint) Close()error{
 if !e.gate.close(){return nil}
 e.gate.wait()
 return e.CloseAfterRustJoin()
}
// Called only by the original product owner after both Rust workers join,
// or by Close if Go never handed off the endpoint.
func(e *XdpEndpoint) CloseAfterRustJoin()error{
 if e.dll==nil{return nil}
 e.close.Call(e.handles[0],e.handles[1])
 e.handles=[2]uintptr{}
 err:=e.dll.Release()
 e.dll=nil
 return err
}

// One interface-owned pair for the original Game group, not one pair per lane.
// Only this single cold reader calls RX; per-lane association callbacks are
// serialized by the existing cold TX mutex. Rust borrows after all join.
func OpenXdpGameEndpoint(path string,index uint32,cfgs []NpcapConfig)(*XdpEndpoint,bool,error){
 var ports [4]uint16
 for i,cfg:=range cfgs{
  if err:=cfg.Validate();err!=nil{return nil,true,err}
  ports[i]=cfg.Flow.LocalPort
 }
 e,available,err:=openXdpPorts(path,index,ports[:len(cfgs)],false)
 if err!=nil||!available{return e,available,err}
 e.cfg=cfgs[0];e.gameCfgs=cfgs
 for i:=range cfgs{e.gameIDs[i]=1}
 return e,true,nil
}
func openXdpPorts(path string,index uint32,ports []uint16,udp bool)(*XdpEndpoint,bool,error){
 return openXdpPortSet(path,index,ports,udp,nil)
}
// The opt-in carrier uses the same initial cold handoff, but allows a
// later candidate port on the existing XSK. Never silently fall back.
func OpenXdpRotatableGameEndpoint(path string,index uint32,cfgs []NpcapConfig)(*XdpEndpoint,bool,error){
 if len(cfgs)!=4{return nil,true,fmt.Errorf("rotatable Game requires four lanes")}
 var ports [4]uint16
 local:=cfgs[0].Flow.LocalIP
 for i,cfg:=range cfgs{
  if err:=cfg.Validate();err!=nil{return nil,true,err}
  if cfg.Flow.LocalIP!=local{return nil,true,fmt.Errorf("rotatable Game local IPv4 mismatch")}
  ports[i]=cfg.Flow.LocalPort
 }
 e,ok,err:=openXdpPortSet(path,index,ports[:],false,&local)
 if err!=nil||!ok{return e,ok,err}
 e.cfg=cfgs[0];e.gameCfgs=cfgs
 for i:=range cfgs{e.gameIDs[i]=1}
 return e,true,nil
}
func openXdpPortSet(path string,index uint32,ports []uint16,udp bool,local *[4]byte)(*XdpEndpoint,bool,error){
 dll,err:=syscall.LoadDLL(path)
 if err!=nil{return nil,false,err}
 symbol:="wbd_m0_win_xdp_open_ports"
 if local!=nil{symbol="wbd_m0_win_xdp_open_rotatable"}
 open,err:=dll.FindProc(symbol)
 if err!=nil{_ = dll.Release();return nil,false,nil}
 read,err:=dll.FindProc("wbd_m0_win_xdp_read")
 if err!=nil{_ = dll.Release();return nil,true,err}
 write,err:=dll.FindProc("wbd_m0_win_xdp_write")
 if err!=nil{_ = dll.Release();return nil,true,err}
 closeProc,err:=dll.FindProc("wbd_m0_win_xdp_close")
 if err!=nil{_ = dll.Release();return nil,true,err}
 e:=&XdpEndpoint{dll:dll,read:read,write:write,close:closeProc,gate:newNpcapCallGate(1),ipID:1}
 var protocol uintptr
 if udp{protocol=1}
 var rc uintptr
 if local!=nil{
  rc,_,_=open.Call(uintptr(index),uintptr(unsafe.Pointer(&local[0])),uintptr(unsafe.Pointer(&ports[0])),uintptr(len(ports)),uintptr(unsafe.Pointer(&e.handles[0])))
 }else{
  rc,_,_=open.Call(uintptr(index),uintptr(unsafe.Pointer(&ports[0])),uintptr(len(ports)),protocol,uintptr(unsafe.Pointer(&e.handles[0])))
 }
 runtime.KeepAlive(local);runtime.KeepAlive(ports);runtime.KeepAlive(e)
 if int32(rc)!=0{_ = dll.Release();return nil,true,fmt.Errorf("WinXDP ports open rc=%d",int32(rc))}
 fmt.Printf("WBD_XDP_COLD_OWNER_READY ifindex=%d ports=%d udp=%t\n",index,len(ports),udp)
 return e,true,nil
}
func(e *XdpEndpoint) ReadGameSegmentUntil(stop <-chan struct{})(int,Segment,error){
 if err:=e.gate.begin(1);err!=nil{return 0,Segment{},err}
 defer e.gate.end()
 var frame [4096]byte
 for !e.gate.isClosed(){
  select{case <-stop:return 0,Segment{},ErrNpcapClosed;default:}
  n,err:=e.readRaw(frame[:])
  if err!=nil{return 0,Segment{},err}
  if n==0{continue}
  for i,cfg:=range e.gameCfgs{
   seg,_,ok,err:=decodeNpcapInbound(frame[:n],cfg.Flow)
   if err!=nil{return 0,Segment{},err}
   if ok{return i,seg,nil}
  }
 }
 return 0,Segment{},ErrNpcapClosed
}
func(e *XdpEndpoint) WriteGameSegment(i int,seg Segment)([]byte,error){
 if err:=e.gate.begin(1);err!=nil{return nil,err}
 defer e.gate.end()
 e.sendMu.Lock();defer e.sendMu.Unlock()
 packet,frame,err:=encodeNpcapOutbound(seg,e.gameCfgs[i],e.gameIDs[i])
 if err!=nil{return nil,err}
 e.gameIDs[i]++
 return packet,e.writeRaw(frame)
}
func(e *XdpEndpoint) readRaw(frame []byte)(int,error){
 rc,_,_:=e.read.Call(e.handles[0],uintptr(unsafe.Pointer(&frame[0])),uintptr(len(frame)))
 runtime.KeepAlive(frame)
 if int32(rc)<0{return 0,fmt.Errorf("WinXDP cold read rc=%d",int32(rc))}
 return int(int32(rc)),nil
}
func(e *XdpEndpoint) writeRaw(frame []byte)error{
 rc,_,_:=e.write.Call(e.handles[1],uintptr(unsafe.Pointer(&frame[0])),uintptr(len(frame)))
 runtime.KeepAlive(frame)
 if int32(rc)!=1{return fmt.Errorf("WinXDP cold write rc=%d",int32(rc))}
 return nil
}

// One original FakeTCP cold candidate. These procs target the current
// authenticated Game4 runtime, not the ring handles already loaned to Rust.
// The existing native workers remain the sole RX/TX producers/consumers.
type XdpGameCandidate struct{
 group uint64
 cfg NpcapConfig
 port,read,write *syscall.Proc
 gate *npcapCallGate
 sendMu sync.Mutex
 ipID uint16
 native bool // cold serialized transfer; no Go ring access after handoff
}
func BeginXdpGameCandidate(group uint64,cfg NpcapConfig,port,read,write *syscall.Proc)(*XdpGameCandidate,error){
 if group==0||port==nil||read==nil||write==nil{return nil,ErrNpcapClosed}
 if err:=cfg.Validate();err!=nil{return nil,err}
 rc,_,_:=port.Call(uintptr(group),uintptr(cfg.Flow.LocalPort),1)
 if rc!=0{return nil,fmt.Errorf("WinXDP candidate port rc=%d",rc)}
 return &XdpGameCandidate{group:group,cfg:cfg,port:port,read:read,write:write,
  gate:newNpcapCallGate(cfg.Generation),ipID:1},nil
}
func(c *XdpGameCandidate) ReadSegment()(Segment,error){
 if err:=c.gate.begin(c.cfg.Generation);err!=nil{return Segment{},err}
 defer c.gate.end()
 var frame [4096]byte
 for !c.gate.isClosed(){
  rc,_,_:=c.read.Call(uintptr(c.group),uintptr(c.cfg.Flow.LocalPort),uintptr(unsafe.Pointer(&frame[0])),uintptr(len(frame)))
  runtime.KeepAlive(&frame)
  n:=int32(rc)
  if n<0||int(n)>len(frame){return Segment{},fmt.Errorf("WinXDP candidate read rc=%d",n)}
  if n==0{continue}
  seg,_,ok,err:=decodeNpcapInbound(frame[:n],c.cfg.Flow)
  if err!=nil{return Segment{},err}
  if ok{return seg,nil}
 }
 return Segment{},ErrNpcapClosed
}
func(c *XdpGameCandidate) WriteSegment(seg Segment)error{
 if err:=c.gate.begin(c.cfg.Generation);err!=nil{return err}
 defer c.gate.end()
 c.sendMu.Lock();defer c.sendMu.Unlock()
 _,frame,err:=encodeNpcapOutbound(seg,c.cfg,c.ipID)
 if err!=nil{return err}
 c.ipID++
 rc,_,_:=c.write.Call(uintptr(c.group),uintptr(c.cfg.Flow.LocalPort),uintptr(unsafe.Pointer(&frame[0])),uintptr(len(frame)))
 runtime.KeepAlive(frame)
 if int32(rc)!=1{return fmt.Errorf("WinXDP candidate write rc=%d",int32(rc))}
 return nil
}
// Join the original Go candidate reader/writer without releasing the port.
// The native proof command then takes the queued frames from the same RX owner.
func(c *XdpGameCandidate) TakeNative()error{
 if !c.gate.close(){return ErrNpcapClosed}
 c.gate.wait();c.native=true;return nil
}
func(c *XdpGameCandidate) CandidatePort()uint16{return c.cfg.Flow.LocalPort}
// Only an uncommitted candidate is discarded through this interface.
// The future native slot commit must transfer its exact port instead.
func(c *XdpGameCandidate) Close()error{
 if !c.native&&!c.gate.close(){return nil}
 c.gate.wait()
 c.native=false
 rc,_,_:=c.port.Call(uintptr(c.group),uintptr(c.cfg.Flow.LocalPort),0)
 if rc!=0{return fmt.Errorf("WinXDP candidate port retirement rc=%d",rc)}
 return nil
}
