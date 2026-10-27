//go:build windows && wbd_v4_embedded_go
package realityfront

// PLAN024: actual original Go protected SERVER credential TLS lanes into
// the same native Rust 2/4 GameAdapter. No unauthenticated cold construction,
// public network Applied grant, M4 packet driver success or UI status here.
import(
 "context"
 "errors"
 "fmt"
 "runtime"
 "sync"
 "syscall"
 "unsafe"
 "github.com/lly8666/wobuzhidao/internal/faketcp"
)
type V4WindowsAuthenticatedGameServerGroup struct{
 mu sync.Mutex
 owners []*V4WindowsAuthenticatedServerOwner
 sessions []*V4ServerSession
 epoch [16]byte
 joined uint64
 stageProc,openProc,joinProc,stopProc *syscall.Proc
 fecOpenProc,fecFinishProc *syscall.Proc
 fecParityProc,fecM4SendProc *syscall.Proc
 gameFec uint8 // protected client/server GameFec, same for all independent TLS lanes
 closed bool
}
func V4WindowsEstablishOriginalGameServerGroup(
 ctx context.Context,library string,assocs []*faketcp.ServerAssociation,
 cfg ServerAdmissionConfig,epochs *V4EpochStore,gameFec ...uint8,
)(*V4WindowsAuthenticatedGameServerGroup,error){
 n:=len(assocs)
 if len(gameFec)>1{return nil,ErrAdmissionParams}
 var negotiatedFec uint8
 if len(gameFec)==1{negotiatedFec=gameFec[0]}
 if negotiatedFec>7{return nil,ErrAdmissionUnsupported}
 if ctx==nil||epochs==nil||(n!=2&&n!=4){return nil,ErrAdmissionParams}
 g:=&V4WindowsAuthenticatedGameServerGroup{gameFec:negotiatedFec}
 fail:=func(cause error)(*V4WindowsAuthenticatedGameServerGroup,error){
  cleanup,cancel:=context.WithTimeout(context.Background(),15*1000000000)
  defer cancel()
  for i:=len(g.owners)-1;i>=0;i--{
   if o:=g.owners[i];o!=nil{
    cause=errors.Join(cause,o.StopScopedOwner(cleanup))
   }
  }
  return nil,cause
 }
 for i,assoc:=range assocs{
  if assoc==nil{return fail(ErrAdmissionParams)}
  owner,e:=newV4WindowsPrivateOwnerBridge(library)
  if e!=nil{return fail(e)}
  lane:=uint8(i+1)
  scoped:=cfg
  allow:=cfg.PolicyAllow
  validate:=cfg.ValidateRequest
  scoped.PolicyAllow=func(policy AdmissionPolicy)error{
   if policy.Transport!=TransportGame||policy.DesiredLanes!=uint8(n)||
    policy.FECMode!=FECOff{return ErrAdmissionUnsupported}
   if allow!=nil{return allow(policy)}
   return nil
  }
  scoped.ValidateRequest=func(req AdmissionRequest)error{
   if req.LaneID!=lane||req.DesiredLanes!=uint8(n){
    return ErrAdmissionUnsupported
   }
   if validate!=nil{return validate(req)}
   return nil
  }
  opts:=V4ServerOptions{
   DataPlaneReady:true,Epochs:epochs,ownerBridge:owner,
   fec2Product:true,GameFec:g.gameFec,
  }
  session,e:=EstablishServerV4(ctx,assoc,scoped,opts)
  if e!=nil{return fail(e)}
  st,e:=owner.state()
  if e!=nil||st.phase!=2||st.server!=1||st.generation==0||
   st.applied!=0||!owner.committed{
   // A post-TLS owner may be ACTIVE but not yet added to the full
   // authenticated group. Do not leak it on a readback mismatch.
   if owner.committed{
    return fail(errors.Join(errV4WindowsOwner,owner.stopRustOwnerOnly()))
   }
   return fail(errV4WindowsOwner)
  }
  if i==0{g.epoch=session.Epoch}
  if session.Epoch!=g.epoch||g.epoch==[16]byte{}{
   return fail(errors.Join(ErrAdmissionUnsupported,owner.stopRustOwnerOnly()))
  }
  g.owners=append(g.owners,&V4WindowsAuthenticatedServerOwner{bridge:owner})
  g.sessions=append(g.sessions,session)
 }
 return g,nil
}
func(g *V4WindowsAuthenticatedGameServerGroup) BindAndJoinOriginalWintun(
 ctx context.Context,device V4WindowsCurrentNativeDevice,
 id V4WindowsNativeDeviceIdentity,
)error{
 if ctx==nil||device==nil||g==nil{return errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 if g.closed||g.joined!=0||id.Generation!=g.epoch||
  (len(g.owners)!=2&&len(g.owners)!=4){return errV4WindowsOwner}
 handles:=make([]uint64,0,len(g.owners))
 for _,o:=range g.owners{
  if o==nil||o.bridge==nil||o.bridge.handle==0||
   !o.bridge.committed||o.bridge.epoch!=g.epoch{
   return errV4WindowsOwner
  }
  if err:=o.BindOriginalM4NativeDevice(ctx,device,id);err!=nil{return err}
  if err:=o.checkedBound(ctx);err!=nil{return err}
  handles=append(handles,o.bridge.handle)
 }
 dll:=g.owners[0].bridge.dll
 for _,row:=range []struct{name string;dest **syscall.Proc}{
  {"wbd_m0_win_owner_v4_game_join",&g.joinProc},
  {"wbd_m0_win_owner_v4_game_stage",&g.stageProc},
  {"wbd_m0_win_owner_v4_game_receive",&g.openProc},
  {"wbd_m0_win_owner_v4_game_stop",&g.stopProc},
 }{
  proc,err:=dll.FindProc(row.name)
  if err!=nil{return fmt.Errorf("%w: real Rust Windows group ABI %s",errV4WindowsOwner,row.name)}
  *row.dest=proc
 }
 var group uint64
 err:=winOwnerCall(g.joinProc,uintptr(unsafe.Pointer(&handles[0])),
  uintptr(len(handles)),1,uintptr(unsafe.Pointer(&group)))
 runtime.KeepAlive(handles)
 if err!=nil||group==0{return errors.Join(errV4WindowsOwner,err)}
 g.joined=group
 // Linux's one shared authenticated Game fixed FEC owner, installed
 // strictly after all protected per-lane TLS and bound native identities.
 if g.gameFec!=0{
  open,err:=dll.FindProc("wbd_m0_win_owner_v4_game_receive_fec")
  if err!=nil{return errors.Join(errV4WindowsOwner,err)}
  finish,err:=dll.FindProc("wbd_m0_win_owner_v4_game_finish_fec")
  if err!=nil{return errors.Join(errV4WindowsOwner,err)}
  parity,err:=dll.FindProc("wbd_m0_win_owner_v4_game_fec_parity_due")
  if err!=nil{return errors.Join(errV4WindowsOwner,err)}
  receipt,err:=dll.FindProc("wbd_m0_win_owner_v4_game_m4_send_result")
  if err!=nil{return errors.Join(errV4WindowsOwner,err)}
  fec,err:=dll.FindProc("wbd_m0_win_owner_v4_game_fec_enable")
  if err!=nil{return errors.Join(errV4WindowsOwner,err)}
  if err=winOwnerCall(fec,uintptr(group),uintptr(g.gameFec-1));err!=nil{return err}
  g.fecOpenProc=open
  g.fecFinishProc=finish
  g.fecParityProc=parity
  g.fecM4SendProc=receipt
 }
 return nil
}
func(g *V4WindowsAuthenticatedGameServerGroup) active(ctx context.Context)error{
 if ctx==nil||g==nil||g.closed||g.joined==0{return errV4WindowsOwner}
 if err:=ctx.Err();err!=nil{return err}
 for _,o:=range g.owners{
  if o==nil||o.bridge==nil||o.device==nil||o.bridge.epoch!=g.epoch{return errV4WindowsOwner}
  if err:=o.checkedBound(ctx);err!=nil{return err}
 }
 return nil
}
func(g *V4WindowsAuthenticatedGameServerGroup) StageGameRecords(
 ctx context.Context,ipv4 []byte,
)([]V4WindowsGameRecord,error){
 if g==nil{return nil,errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 if err:=g.active(ctx);err!=nil{return nil,err}
 if len(ipv4)<20||len(ipv4)>1200||ipv4[0]>>4!=4{return nil,errV4WindowsOwner}
 raw:=make([]v4WindowsGameRawRecord,len(g.owners))
 var count uint32
 err:=winOwnerCall(g.stageProc,uintptr(g.joined),
  uintptr(unsafe.Pointer(&ipv4[0])),uintptr(len(ipv4)),
  uintptr(unsafe.Pointer(&raw[0])),uintptr(len(raw)),
  uintptr(unsafe.Pointer(&count)))
 runtime.KeepAlive(ipv4);runtime.KeepAlive(raw)
 if err!=nil||int(count)!=len(raw){return nil,errors.Join(errV4WindowsOwner,err)}
 out:=make([]V4WindowsGameRecord,0,count)
 for _,rec:=range raw{
  if rec.Lane==0||int(rec.Lane)>len(raw)||rec.Length<32||rec.Length>1536{
   return nil,errV4WindowsOwner
  }
  out=append(out,V4WindowsGameRecord{
   Lane:rec.Lane,Length:rec.Length,PacketNumber:rec.PacketNumber,
   LogicalID:rec.LogicalID,Wire:append([]byte(nil),rec.Wire[:rec.Length]...),
  })
 }
 return out,nil
}
func(g *V4WindowsAuthenticatedGameServerGroup) OpenGameRecord(
 ctx context.Context,lane uint32,wire []byte,
)([]byte,error){
 if g==nil{return nil,errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 if err:=g.active(ctx);err!=nil{return nil,err}
 if g.gameFec!=0{return nil,errV4WindowsOwner}
 if lane==0||int(lane)>len(g.owners)||len(wire)<32||len(wire)>1536{
  return nil,errV4WindowsOwner
 }
 plain:=make([]byte,1536)
 var used uintptr
 err:=winOwnerCall(g.openProc,uintptr(g.joined),uintptr(lane),
  uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)),
  uintptr(unsafe.Pointer(&plain[0])),uintptr(len(plain)),
  uintptr(unsafe.Pointer(&used)))
 runtime.KeepAlive(wire);runtime.KeepAlive(plain)
 if err!=nil{return nil,err}
 if used==0{return nil,nil}
 if used<20||used>1200||plain[0]>>4!=4||plain[0]&15<5{return nil,errV4WindowsOwner}
 return plain[:used],nil
}
func(g *V4WindowsAuthenticatedGameServerGroup) StopCryptoAfterDriverDrain(
 ctx context.Context,
)error{
 if g==nil||ctx==nil{return errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 if g.closed{return nil}
 if g.joined==0{return errV4WindowsOwner}
 for _,o:=range g.owners{
  if o==nil||o.device==nil||o.bridge==nil{return errV4WindowsOwner}
  lease,b:=o.device,o.bridge
  if err:=lease.device.VerifyCurrentNative(ctx,lease.identity);err!=nil{return err}
  if err:=winOwnerCall(b.quiesceWintunProc,uintptr(b.handle),
   uintptr(unsafe.Pointer(&b.epoch[0])),16,
   uintptr(lease.identity.LUID),uintptr(lease.identity.InterfaceIndex));err!=nil{return err}
  runtime.KeepAlive(b.epoch)
 }
 if err:=winOwnerCall(g.stopProc,uintptr(g.joined));err!=nil{return err}
 for _,o:=range g.owners{
  if err:=o.StopScopedOwner(ctx);err!=nil{return err}
 }
 g.closed=true;g.joined=0
 return nil
}
