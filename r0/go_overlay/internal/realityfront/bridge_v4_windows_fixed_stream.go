//go:build windows && wbd_v4_embedded_go
package realityfront
// Windows thin native NPF sender for the frozen W168 Linux FixedStream owner.
// All block/index, RS16, parity deadline and mature M2 policy is native Rust.
import (
 "context"
 "errors"
 "runtime"
 "sync"
 "unsafe"
)
type V4WindowsFixedMatureReadback struct{
 Version,Size,Applied,Censored uint32
 CopiedSource,CopiedParity,ReverseReports,Positive2s,Covered2s uint64
}
type V4WindowsFixedParity struct{
 Wire []byte
 Seq uint32
 PN uint64
}
type winFec2NativeParityRow struct{
 Used,Seq uint32
 PN uint64
 Wire [2048]byte
}
type winFec2NativeParityBatch struct{
 Count,Reserved uint32
 Rows [4]winFec2NativeParityRow
}
// The native Rust entry writes the COMPLETE 4-row C struct each call,
// including unused rows. Reuse this 8KiB output allocation; returned
// independent record slices are deep-copied before releasing the buffer.
var winFec2ParityPool=sync.Pool{New:func()any{
 return new(winFec2NativeParityBatch)
}}
func(s *V4WindowsAuthenticatedClientOwner) SealBoundOriginalFixedSource(
 ctx context.Context,ipv4 []byte,
)([]byte,uint32,uint64,error){
 if s==nil||s.bridge==nil||s.device==nil||ctx==nil||
  len(ipv4)<20||len(ipv4)+41>2048||len(ipv4)>s.device.maxIPv4{
  return nil,0,0,errV4WindowsOwner
 }
 if err:=ctx.Err();err!=nil{return nil,0,0,err}
 if err:=s.device.device.VerifyCurrentNative(ctx,s.device.identity);err!=nil{
  return nil,0,0,errors.Join(errV4WindowsOwner,err)
 }
 proc,err:=s.bridge.fixedProc("wbd_m0_win_owner_v8_fixed_stage_source")
 if err!=nil{return nil,0,0,err}
 wire:=make([]byte,len(ipv4)+41)
 var used uintptr
 var seq uint32
 var pn uint64
 err=winOwnerCall(proc,uintptr(s.bridge.handle),
  uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
  uintptr(s.device.identity.LUID),uintptr(s.device.identity.InterfaceIndex),
  uintptr(unsafe.Pointer(&ipv4[0])),uintptr(len(ipv4)),
  uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)),
  uintptr(unsafe.Pointer(&used)),uintptr(unsafe.Pointer(&seq)),
  uintptr(unsafe.Pointer(&pn)))
 runtime.KeepAlive(s.bridge.epoch);runtime.KeepAlive(ipv4);runtime.KeepAlive(wire)
 if err!=nil||used==0||used>uintptr(len(wire)){
  return nil,0,0,errors.Join(errV4WindowsOwner,err)
 }
 return wire[:used],seq,pn,nil
}
func(s *V4WindowsAuthenticatedClientOwner) NextBoundOriginalFixedParity(
 ctx context.Context,
)([]V4WindowsFixedParity,error){
 if s==nil||s.bridge==nil||s.device==nil||ctx==nil{return nil,errV4WindowsOwner}
 if err:=ctx.Err();err!=nil{return nil,err}
 if err:=s.device.device.VerifyCurrentNative(ctx,s.device.identity);err!=nil{
  return nil,errors.Join(errV4WindowsOwner,err)
 }
 proc,err:=s.bridge.fixedProc("wbd_m0_win_owner_v8_fixed_parity_due")
 if err!=nil{return nil,err}
 batch:=winFec2ParityPool.Get().(*winFec2NativeParityBatch)
 defer winFec2ParityPool.Put(batch)
 err=winOwnerCall(proc,uintptr(s.bridge.handle),
  uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
  uintptr(s.device.identity.LUID),uintptr(s.device.identity.InterfaceIndex),
  uintptr(unsafe.Pointer(batch)),uintptr(unsafe.Sizeof(*batch)))
 runtime.KeepAlive(s.bridge.epoch)
 if err!=nil||batch.Count>4||batch.Reserved!=0{return nil,errors.Join(errV4WindowsOwner,err)}
 out:=make([]V4WindowsFixedParity,0,batch.Count)
 for i:=uint32(0);i<batch.Count;i++{
  row:=batch.Rows[i]
  if row.Used<51||row.Used>2048{return nil,errV4WindowsOwner}
  out=append(out,V4WindowsFixedParity{
   Wire:append([]byte(nil),row.Wire[:row.Used]...),Seq:row.Seq,PN:row.PN})
 }
 return out,nil
}
func(s *V4WindowsAuthenticatedClientOwner) CompleteBoundOriginalFixedParity(
 ctx context.Context,copied,notSent,uncertain uint32,
)error{
 if s==nil||s.bridge==nil||s.device==nil||ctx==nil||
  copied+notSent+uncertain==0||copied+notSent+uncertain>4{
  return errV4WindowsOwner
 }
 if err:=ctx.Err();err!=nil{return err}
 proc,err:=s.bridge.fixedProc("wbd_m0_win_owner_v8_fixed_parity_result")
 if err!=nil{return err}
 err=winOwnerCall(proc,uintptr(s.bridge.handle),
  uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
  uintptr(s.device.identity.LUID),uintptr(s.device.identity.InterfaceIndex),
  uintptr(copied),uintptr(notSent),uintptr(uncertain))
 runtime.KeepAlive(s.bridge.epoch)
 return err
}
func(s *V4WindowsAuthenticatedClientOwner) ReadBoundOriginalFixedMature(
 ctx context.Context,
)(V4WindowsFixedMatureReadback,error){
 var out V4WindowsFixedMatureReadback
 if s==nil||s.bridge==nil||s.device==nil||ctx==nil{return out,errV4WindowsOwner}
 if err:=ctx.Err();err!=nil{return out,err}
 proc,err:=s.bridge.fixedProc("wbd_m0_win_owner_v8_fixed_mature_readback")
 if err!=nil{return out,err}
 err=winOwnerCall(proc,uintptr(s.bridge.handle),
  uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
  uintptr(s.device.identity.LUID),uintptr(s.device.identity.InterfaceIndex),
  uintptr(unsafe.Pointer(&out)),uintptr(unsafe.Sizeof(out)))
 runtime.KeepAlive(s.bridge.epoch)
 if err!=nil||out.Version!=1||out.Size!=uint32(unsafe.Sizeof(out))||
  out.Applied>1||out.Censored>1{
  return V4WindowsFixedMatureReadback{},errors.Join(errV4WindowsOwner,err)
 }
 return out,nil
}

// RequestBoundOriginalFEC2Revision reuses the ORIGINAL Linux FixedStream
// profile/revision transition. Only the protected, committed Go TLS owner
// and SAME M4-created live Wintun can issue a private pending request.
// The request itself is never an Applied acknowledgment: the independent
// mature M2 + copied source/parity + native Stop gates remain mandatory.
// Auto policy decisions MUST come from the shared Linux FecV2 controller,
// never an invented Windows periodic scheduler.
func(s *V4WindowsAuthenticatedClientOwner) RequestBoundOriginalFEC2Revision(
 ctx context.Context,profile FecV2Profile,revision uint64,
)error{
 if ctx==nil||s==nil||s.bridge==nil||s.device==nil||
  !profile.Valid()||revision==0{return errV4WindowsOwner}
 if err:=ctx.Err();err!=nil{return err}
 if err:=s.device.device.VerifyCurrentNative(ctx,s.device.identity);err!=nil{
  return errors.Join(errV4WindowsOwner,err)
 }
 state,err:=s.OriginalOwnerReadback()
 if err!=nil||!state.OwnerActive||!state.DeviceBound||
  state.DeviceQuiesced||state.ProductApplied{
  return errV4WindowsOwner
 }
 proc,err:=s.bridge.fixedProc("wbd_m0_win_owner_v8_fixed_change_revision")
 if err!=nil{return errors.Join(errV4WindowsOwner,err)}
 err=winOwnerCall(proc,uintptr(s.bridge.handle),
  uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
  uintptr(s.device.identity.LUID),
  uintptr(s.device.identity.InterfaceIndex),
  uintptr(profile),uintptr(revision))
 runtime.KeepAlive(s.bridge.epoch)
 return err
}

// SelectBoundOriginalFEC2Initial binds the actual selected Linux FEC2
// Fixed/Auto profile at protected revision1 BEFORE any M4 NPF DATA stage.
// In particular Auto starts at Linux Strong=5 rather than hardcoded
// Maximum=6; neither the selection nor a profile change grants Applied.
func(s *V4WindowsAuthenticatedClientOwner) SelectBoundOriginalFEC2Initial(
 ctx context.Context,profile FecV2Profile,
)error{
 if ctx==nil||s==nil||s.bridge==nil||s.device==nil||!profile.Valid(){
  return errV4WindowsOwner
 }
 if err:=ctx.Err();err!=nil{return err}
 if err:=s.device.device.VerifyCurrentNative(ctx,s.device.identity);err!=nil{
  return errors.Join(errV4WindowsOwner,err)
 }
 state,err:=s.OriginalOwnerReadback()
 if err!=nil||!state.OwnerActive||!state.DeviceBound||
  state.DeviceQuiesced||state.ProductApplied{
  return errV4WindowsOwner
 }
 proc,err:=s.bridge.fixedProc("wbd_m0_win_owner_v8_fixed_select_initial")
 if err!=nil{return errors.Join(errV4WindowsOwner,err)}
 err=winOwnerCall(proc,uintptr(s.bridge.handle),
  uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
  uintptr(s.device.identity.LUID),
  uintptr(s.device.identity.InterfaceIndex),uintptr(profile))
 runtime.KeepAlive(s.bridge.epoch)
 return err
}
