//go:build windows && wbd_v4_embedded_go
package realityfront

// Original per-lane TLS+Rust M3 AEAD / one shared Linux GameFecRx.
// Only real native Wintun writes permit the follow-up allCopied commit.
import (
 "context"
 "errors"
 "runtime"
 "syscall"
 "unsafe"
)

type winGameFecFrame struct {
 Length uint32
 Wire [2048]byte
}
type winGameFecBatch struct {
 Count,Pending uint32
 Rows [16]winGameFecFrame
}
func winGameFecOpen(proc *syscall.Proc,group uint64,lane uint32,wire []byte)(
 [][]byte,bool,error,
){
 if proc==nil||group==0||lane==0||len(wire)<32||len(wire)>1536{
  return nil,false,errV4WindowsOwner
 }
 var out winGameFecBatch
 err:=winOwnerCall(proc,uintptr(group),uintptr(lane),
  uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)),
  uintptr(unsafe.Pointer(&out)),uintptr(unsafe.Sizeof(out)))
 runtime.KeepAlive(wire)
 if err!=nil{return nil,false,errors.Join(errV4WindowsOwner,err)}
 if out.Count>16||out.Pending>1||(out.Count!=0&&out.Pending!=1){
  return nil,false,errV4WindowsOwner
 }
 frames:=make([][]byte,0,out.Count)
 for i:=uint32(0);i<out.Count;i++{
  row:=out.Rows[i]
  if row.Length<20||row.Length>2048||row.Wire[0]>>4!=4||row.Wire[0]&15<5{
   return nil,false,errV4WindowsOwner
  }
  frames=append(frames,append([]byte(nil),row.Wire[:row.Length]...))
 }
 return frames,out.Pending==1,nil
}
func winGameFecFinish(proc *syscall.Proc,group uint64,lane uint32,copiedPrefix uint32)error{
 if proc==nil||group==0||lane==0||copiedPrefix>16{return errV4WindowsOwner}
 // Exact prefix count, not an ambiguous all/none boolean. The native
 // Rust owner checks it against the true staged batch before settlement.
 return winOwnerCall(proc,uintptr(group),uintptr(lane),uintptr(copiedPrefix))
}
func(g *V4WindowsAuthenticatedGameGroup) OpenGameFecBatch(
 ctx context.Context,lane uint32,wire []byte,
)([][]byte,bool,error){
 if g==nil{return nil,false,errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 if g.gameFec==0{return nil,false,errV4WindowsOwner}
 loanRelease,loanErr:=g.holdLive(ctx)
 if loanErr!=nil{return nil,false,loanErr}
 defer loanRelease()
 return winGameFecOpen(g.fecOpenProc,g.joined,lane,wire)
}
func(g *V4WindowsAuthenticatedGameGroup) CompleteGameFecBatch(
 ctx context.Context,lane uint32,copiedPrefix uint32,
)error{
 if g==nil{return errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 if g.gameFec==0{return errV4WindowsOwner}
 loanRelease,loanErr:=g.holdLive(ctx)
 if loanErr!=nil{return loanErr}
 defer loanRelease()
 return winGameFecFinish(g.fecFinishProc,g.joined,lane,copiedPrefix)
}
func(g *V4WindowsAuthenticatedGameServerGroup) OpenGameFecBatch(
 ctx context.Context,lane uint32,wire []byte,
)([][]byte,bool,error){
 if g==nil{return nil,false,errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 if g.gameFec==0{return nil,false,errV4WindowsOwner}
 if err:=g.active(ctx);err!=nil{return nil,false,err}
 return winGameFecOpen(g.fecOpenProc,g.joined,lane,wire)
}
func(g *V4WindowsAuthenticatedGameServerGroup) CompleteGameFecBatch(
 ctx context.Context,lane uint32,copiedPrefix uint32,
)error{
 if g==nil{return errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 if g.gameFec==0{return errV4WindowsOwner}
 if err:=g.active(ctx);err!=nil{return err}
 return winGameFecFinish(g.fecFinishProc,g.joined,lane,copiedPrefix)
}

// All ticket accounting is scoped to genuine same-process native Wintun
// and independently authenticated Game2/4 Npcap lanes. The returned
// ciphertext is STAGED, never proof that the Windows kernel copied it.
// Neither API sends a packet itself or claims product/GUI Applied.
func winGameFecParityDue(proc *syscall.Proc,group uint64,capacity uint32)(
 []V4WindowsGameRecord,error,
){
 if proc==nil||group==0||capacity==0||capacity>16{
  return nil,errV4WindowsOwner
 }
 rows:=make([]v4WindowsGameRawRecord,capacity)
 var count uint32
 err:=winOwnerCall(proc,uintptr(group),
  uintptr(unsafe.Pointer(&rows[0])),uintptr(capacity),
  uintptr(unsafe.Pointer(&count)))
 runtime.KeepAlive(rows)
 if err!=nil||count>capacity{return nil,errors.Join(errV4WindowsOwner,err)}
 out:=make([]V4WindowsGameRecord,0,count)
 for _,r:=range rows[:count]{
  if r.Lane==0||r.Lane>4||r.Length<32||r.Length>1536{
   return nil,errV4WindowsOwner
  }
  out=append(out,V4WindowsGameRecord{
   Lane:r.Lane,Length:r.Length,PacketNumber:r.PacketNumber,
   LogicalID:r.LogicalID,Wire:append([]byte(nil),r.Wire[:r.Length]...),
  })
 }
 return out,nil
}
func winGameFecM4SendResult(proc *syscall.Proc,group uint64,
 lane uint32,logicalID,pn uint64,kernelCopied bool)error{
 if proc==nil||group==0||lane==0||lane>4{return errV4WindowsOwner}
 var copied uintptr
 if kernelCopied{copied=1}
 return winOwnerCall(proc,uintptr(group),uintptr(lane),
  uintptr(logicalID),uintptr(pn),copied)
}
// DueGameFecParity returns a bounded batch from the SAME shared Rust
// GameFecTx timed owner used by Linux. Only use after real native
// Npcap has reported all earlier staged send tickets.
func(g *V4WindowsAuthenticatedGameGroup) DueGameFecParity(
 ctx context.Context,capacity uint32,
)([]V4WindowsGameRecord,error){
 if g==nil{return nil,errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 // Same native due-poll ABI handles postponed Game4 off replicas and
 // GameFec parity. The original per-lane NPF result remains mandatory.
 loanRelease,loanErr:=g.holdLive(ctx)
 if loanErr!=nil{return nil,loanErr}
 defer loanRelease()
 return winGameFecParityDue(g.fecParityProc,g.joined,capacity)
}
func(g *V4WindowsAuthenticatedGameGroup) ReportGameFecNpcapCopy(
 ctx context.Context,record V4WindowsGameRecord,copied bool,
)error{
 if g==nil{return errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 // All Game2/4 copy outcomes are authentic NPF kernel callback receipts,
 // including Game/off. Staging into a Go output array cannot grant credit.
 loanRelease,loanErr:=g.holdLive(ctx)
 if loanErr!=nil{return loanErr}
 defer loanRelease()
 // The real per-lane pcap_sendpacket callback must be the sole caller.
 return winGameFecM4SendResult(g.fecM4SendProc,g.joined,
  record.Lane,record.LogicalID,record.PacketNumber,copied)
}
func(g *V4WindowsAuthenticatedGameServerGroup) DueGameFecParity(
 ctx context.Context,capacity uint32,
)([]V4WindowsGameRecord,error){
 if g==nil{return nil,errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 if g.gameFec==0{return nil,errV4WindowsOwner}
 if err:=g.active(ctx);err!=nil{return nil,err}
 return winGameFecParityDue(g.fecParityProc,g.joined,capacity)
}
func(g *V4WindowsAuthenticatedGameServerGroup) ReportGameFecNpcapCopy(
 ctx context.Context,record V4WindowsGameRecord,copied bool,
)error{
 if g==nil{return errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 if g.gameFec==0{return errV4WindowsOwner}
 if err:=g.active(ctx);err!=nil{return err}
 return winGameFecM4SendResult(g.fecM4SendProc,g.joined,
  record.Lane,record.LogicalID,record.PacketNumber,copied)
}
