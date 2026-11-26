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
}

// Only a deliberately built native-XDP DLL exposes this cold entry. Missing
// symbol selects the original product's Npcap carrier, not a runtime
// fallback after XDP activation failed.
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
