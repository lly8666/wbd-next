//go:build windows && wbd_v4_embedded_go
package realityfront

// PLAN024: a private original-Go credential TLS Game2/4 lane group.
// This is an AEAD/PN record adapter and exact native Rust owner fence,
// not an OS Applied flag or a Wintun/TCP packet delivery claim.
import (
 "context"
 "errors"
 "fmt"
 "runtime"
 "sync"
 "time"
 "syscall"
 "unsafe"
 "github.com/lly8666/wobuzhidao/internal/faketcp"
)
type V4WindowsGameRecord struct{
 Lane uint32
 Length uint32
 PacketNumber uint64
 LogicalID uint64
 Wire []byte
}
type v4WindowsGameRawRecord struct{
 Lane uint32
 Length uint32
 PacketNumber uint64
 LogicalID uint64
 Wire [1536]byte
}
type V4WindowsAuthenticatedGameGroup struct{
 mu sync.Mutex
 members []*V4WindowsAuthenticatedClientOwner
 sessions []*V4ClientSession
 epoch [16]byte
 joined uint64
 stageProc,receiveProc,joinProc,stopProc,effectiveMtuProc *syscall.Proc
 maxIPv4 int
 fecOpenProc,fecFinishProc *syscall.Proc
 fecParityProc,fecM4SendProc *syscall.Proc
 gameFec uint8 // authenticated TLS GameFec=1..7 -> shared fixed profile0..6
 closed bool
}
// Epoch exposes only the negotiated original-Go TLS generation marker,
// never cold key material or a privilege to bind an arbitrary device.
func(g *V4WindowsAuthenticatedGameGroup) Epoch()[16]byte{
 if g==nil{return [16]byte{}}
 g.mu.Lock();defer g.mu.Unlock()
 if g.closed{return [16]byte{}}
 return g.epoch
}
// Each FakeTCP association has completed its real original Go handshake;
// no independent cold248, shared password shortcut, test-only KDF or fake
// Rust owner can be submitted through this API.
func V4WindowsEstablishOriginalGameClientGroup(
 ctx context.Context,dll string,associations []*faketcp.ClientAssociation,
 base ClientAdmissionConfig,gameFec ...uint8,
)(*V4WindowsAuthenticatedGameGroup,error){
 n:=len(associations)
 if len(gameFec)>1{return nil,ErrAdmissionParams}
 var negotiatedFec uint8
 if len(gameFec)==1{negotiatedFec=gameFec[0]}
 if negotiatedFec>7{return nil,ErrAdmissionUnsupported}
 if ctx==nil||(n!=2&&n!=4)||base.Policy.Transport!=TransportGame||
  int(base.Policy.DesiredLanes)!=n||int(base.DesiredLanes)!=n||
  base.Policy.SupportedNow()!=nil{return nil,ErrAdmissionUnsupported}
 g:=&V4WindowsAuthenticatedGameGroup{gameFec:negotiatedFec}
 // Mirror Linux's abortLocked and the Windows server group's rollback:
 // a late lane TLS failure cannot strand previously authenticated Rust
 // owners or leave their exporter-derived keys live across reconnect.
 fail:=func(cause error)(*V4WindowsAuthenticatedGameGroup,error){
  cleanup,cancel:=context.WithTimeout(context.Background(),15*time.Second)
  defer cancel()
  for i:=len(g.members)-1;i>=0;i--{
   if o:=g.members[i];o!=nil{
    cause=errors.Join(cause,o.StopScopedOwner(cleanup))
   }
  }
  return nil,cause
 }
 for i,assoc:=range associations{
  if assoc==nil||assoc.BootstrapConn()==nil{return fail(ErrAdmissionParams)}
  b,e:=newV4WindowsPrivateOwnerBridge(dll)
  if e!=nil{return fail(e)}
  cfg:=base
  cfg.LaneID=uint8(i+1)
  session,e:=EstablishClientV4(ctx,assoc.BootstrapConn(),cfg,
   V4ClientOptions{DataPlaneReady:true,Epoch:g.epoch,
    fec2Product:true,GameFec:g.gameFec})
  if e!=nil{return fail(e)}
  if i==0{g.epoch=session.Epoch}
  if session.Epoch!=g.epoch||g.epoch==[16]byte{}{return fail(ErrAdmissionUnsupported)}
  handoff,e:=assoc.Detach()
  if e!=nil{return fail(e)}
  if e=b.prepareAuthenticatedClient(session,handoff,assoc.Flow());e!=nil{
   // A successful first lane is not a right to retain uncommitted
   // later-lane transport material. Original bridge aborts a failed
   // commit itself; if this lane reached ACTIVE, stop it explicitly.
   if b.committed{
    e=errors.Join(e,b.stopRustOwnerOnly())
   }
   return fail(fmt.Errorf("Game lane %d authentic Rust owner: %w",i+1,e))
  }
  g.members=append(g.members,&V4WindowsAuthenticatedClientOwner{bridge:b})
  g.sessions=append(g.sessions,session)
 }
 return g,nil
}
// BindAndJoinOriginalWintun can only use a SAME-process M4-issued native
// device, checked separately for all original TLS lane epochs. There is
// NO public attach-by-GUID or config-controlled Rust grouped installer.
func(g *V4WindowsAuthenticatedGameGroup) BindAndJoinOriginalWintun(
 ctx context.Context,device V4WindowsCurrentNativeDevice,
 id V4WindowsNativeDeviceIdentity,
)error{
 if ctx==nil||device==nil||g==nil{return errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 if g.closed||g.joined!=0||len(g.members)!=len(g.sessions)||
  (len(g.members)!=2&&len(g.members)!=4)||
  id.Generation!=g.epoch{return errV4WindowsOwner}
 handles:=make([]uint64,0,len(g.members))
 for _,s:=range g.members{
  if s==nil||s.bridge==nil||s.bridge.handle==0||
   !s.bridge.committed||s.bridge.epoch!=g.epoch{
   return errV4WindowsOwner
  }
  // The real five-stage native OS product has already acquired the
  // first lane's exact Wintun hold. The group only binds remaining
  // original TLS lanes and then joins all 2/4 protected Rust owners.
  if s.device==nil{
   if err:=s.BindOriginalM4NativeDevice(ctx,device,id);err!=nil{return err}
  }else if s.device.identity!=id{
   return errV4WindowsOwner
  }
  state,err:=s.OriginalOwnerReadback()
  if err!=nil||!state.OwnerActive||!state.DeviceBound||
   state.DeviceQuiesced||state.ProductApplied{return errV4WindowsOwner}
  handles=append(handles,s.bridge.handle)
 }
 b:=g.members[0].bridge
 for _,item:=range []struct{name string;into **syscall.Proc}{
  {"wbd_m0_win_owner_v4_game_join",&g.joinProc},
  {"wbd_m0_win_owner_v4_game_stage",&g.stageProc},
  {"wbd_m0_win_owner_v4_game_receive",&g.receiveProc},
  {"wbd_m0_win_owner_v4_game_stop",&g.stopProc},
  {"wbd_m0_win_owner_v4_game_effective_mtu",&g.effectiveMtuProc},
  {"wbd_m0_win_owner_v4_game_m4_send_result",&g.fecM4SendProc},
  {"wbd_m0_win_owner_v4_game_fec_parity_due",&g.fecParityProc},
 }{
  p,err:=b.dll.FindProc(item.name)
  if err!=nil{return fmt.Errorf("%w: native Game group ABI %s missing",errV4WindowsOwner,item.name)}
  *item.into=p
 }
 var group uint64
 if err:=winOwnerCall(g.joinProc,uintptr(unsafe.Pointer(&handles[0])),
  uintptr(len(handles)),0,uintptr(unsafe.Pointer(&group)));err!=nil{return err}
 runtime.KeepAlive(handles)
 if group==0{return errV4WindowsOwner}
 g.joined=group
 // Linux authority: each lane's protected GameFec TLS extension matches
 // g.gameFec before Detach. Enable ONE Rust GameFec owner, never Go FEC.
 if g.gameFec!=0{
  open,err:=b.dll.FindProc("wbd_m0_win_owner_v4_game_receive_fec")
  if err!=nil{return errors.Join(errV4WindowsOwner,err)}
  finish,err:=b.dll.FindProc("wbd_m0_win_owner_v4_game_finish_fec")
  if err!=nil{return errors.Join(errV4WindowsOwner,err)}
  fec,err:=b.dll.FindProc("wbd_m0_win_owner_v4_game_fec_enable")
  if err!=nil{return errors.Join(errV4WindowsOwner,err)}
  if err=winOwnerCall(fec,uintptr(group),uintptr(g.gameFec-1));err!=nil{return err}
  g.fecOpenProc=open
  g.fecFinishProc=finish
 }
 // The real Rust joined-owner and OS readback narrow one immutable
 // effective payload bound shared by WinTun ring, Game crypto and CLI.
 var max uint32
 if err:=winOwnerCall(g.effectiveMtuProc,uintptr(g.joined),
  uintptr(unsafe.Pointer(&max)));err!=nil{return err}
 if max<20||max>1536{return errV4WindowsOwner}
 g.maxIPv4=int(max)
 return nil
}
func(g *V4WindowsAuthenticatedGameGroup) EffectiveGamePayloadMTU()(int,error){
 if g==nil{return 0,errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 if g.closed||g.joined==0||g.maxIPv4<20{return 0,errV4WindowsOwner}
 return g.maxIPv4,nil
}
// The only OS lease validation occurs during the genuine TLS+M4 Hold and
// on Stop/reconfiguration. A group packet borrows each pinned lane until
// the Rust Game owner has consumed it. That owner still independently
// enforces group/generation/phase and rejects any revocation or stale PN.
func(g *V4WindowsAuthenticatedGameGroup) holdLive(ctx context.Context)(func(),error){
 if ctx==nil||g==nil||g.closed||g.joined==0{return nil,errV4WindowsOwner}
 if err:=ctx.Err();err!=nil{return nil,err}
 var releases [4]func()
 held:=0
 giveBack:=func(){
  for held>0{held--;releases[held]();releases[held]=nil}
 }
 for _,s:=range g.members{
  if s==nil||s.device==nil||s.bridge==nil||
   s.bridge.epoch!=g.epoch{giveBack();return nil,errV4WindowsOwner}
  release,err:=s.device.borrowHot(ctx)
  if err!=nil{giveBack();return nil,err}
  if held>=len(releases){release();giveBack();return nil,errV4WindowsOwner}
  releases[held]=release;held++
 }
 return giveBack,nil
}
// StageGameRecords copies genuine per-lane Rust AEAD records into bounded
// caller buffers. A Go M4 packet driver MUST actually send and account for
// each packet before it can assert first-delivery or native product Applied.
func(g *V4WindowsAuthenticatedGameGroup) StageGameRecords(
 ctx context.Context,ipv4 []byte,
)([]V4WindowsGameRecord,error){
 if g==nil{return nil,errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 loanRelease,loanErr:=g.holdLive(ctx)
 if loanErr!=nil{return nil,loanErr}
 defer loanRelease()
 if len(ipv4)<20||len(ipv4)>g.maxIPv4||ipv4[0]>>4!=4{return nil,errV4WindowsOwner}
 raw:=make([]v4WindowsGameRawRecord,len(g.members))
 var count uint32
 err:=winOwnerCall(g.stageProc,uintptr(g.joined),
  uintptr(unsafe.Pointer(&ipv4[0])),uintptr(len(ipv4)),
  uintptr(unsafe.Pointer(&raw[0])),uintptr(len(raw)),
  uintptr(unsafe.Pointer(&count)))
 runtime.KeepAlive(ipv4);runtime.KeepAlive(raw)
 if err!=nil||count>uint32(len(raw)){return nil,errors.Join(errV4WindowsOwner,err)}
 // The shared Rust Game4 owner may return only first-due replicas;
 // later copies remain scheduled without blocking the logical source.
 return decodeOriginalGameStagedRecords(raw,count)
}
// A source acceptance is not proof that every Linux Game4 scheduled copy
// is due in this same 2ms turn. Validate only returned native rows without
// inventing the other lanes or claiming their original NPF copied tickets.
func decodeOriginalGameStagedRecords(raw []v4WindowsGameRawRecord,
 count uint32)([]V4WindowsGameRecord,error){
 if count>uint32(len(raw))||len(raw)>4{return nil,errV4WindowsOwner}
 out:=make([]V4WindowsGameRecord,0,count)
 var mask uint8
 for _,record:=range raw[:count]{
  if record.Lane==0||int(record.Lane)>len(raw)||
   record.Length<32||record.Length>1536{return nil,errV4WindowsOwner}
  bit:=uint8(1)<<(record.Lane-1)
  if mask&bit!=0{return nil,errV4WindowsOwner}
  mask|=bit
  out=append(out,V4WindowsGameRecord{
   Lane:record.Lane,Length:record.Length,
   PacketNumber:record.PacketNumber,LogicalID:record.LogicalID,
   Wire:append([]byte(nil),record.Wire[:record.Length]...),
  })
 }
 return out,nil
}
// OpenGameRecord applies Rust AEAD+PN replay admission and Game first-delivery
// dedup. A zero-length plaintext is a legitimate already-delivered packet.
func(g *V4WindowsAuthenticatedGameGroup) OpenGameRecord(
 ctx context.Context,lane uint32,wire []byte,
)([]byte,error){
 if g==nil{return nil,errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 loanRelease,loanErr:=g.holdLive(ctx)
 if loanErr!=nil{return nil,loanErr}
 defer loanRelease()
 if g.gameFec!=0{return nil,errV4WindowsOwner}
 if lane==0||int(lane)>len(g.members)||len(wire)<32||len(wire)>1536{
  return nil,errV4WindowsOwner
 }
 out:=make([]byte,1536)
 var used uintptr
 err:=winOwnerCall(g.receiveProc,uintptr(g.joined),uintptr(lane),
  uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)),
  uintptr(unsafe.Pointer(&out[0])),uintptr(len(out)),
  uintptr(unsafe.Pointer(&used)))
 runtime.KeepAlive(wire);runtime.KeepAlive(out)
 if err!=nil{return nil,err}
 if used==0{return nil,nil}
 if used<20||used>uintptr(g.maxIPv4)||out[0]>>4!=4||out[0]&15<5{return nil,errV4WindowsOwner}
 return out[:used],nil
}
// The caller MUST join all M4 native socket and kernel packet workers BEFORE
// this crypto-only Stop. This cannot certify WFP, OS routes or GUI Disconnect.
func(g *V4WindowsAuthenticatedGameGroup) StopCryptoAfterDriverDrain(
 ctx context.Context,
)error{
 if g==nil||ctx==nil{return errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 if g.closed{return nil}
 if err:=ctx.Err();err!=nil{return err}
 if g.joined==0{return errV4WindowsOwner}
 for _,s:=range g.members{
  if s==nil||s.device==nil||s.bridge==nil{return errV4WindowsOwner}
  lease:=s.device;b:=s.bridge
  if err:=lease.device.VerifyCurrentNative(ctx,lease.identity);err!=nil{return err}
  if err:=winOwnerCall(b.quiesceWintunProc,uintptr(b.handle),
   uintptr(unsafe.Pointer(&b.epoch[0])),16,
   uintptr(lease.identity.LUID),uintptr(lease.identity.InterfaceIndex));err!=nil{
   return err
  }
  runtime.KeepAlive(b.epoch)
 }
 if err:=winOwnerCall(g.stopProc,uintptr(g.joined));err!=nil{return err}
 for _,s:=range g.members{
  if err:=s.StopScopedOwner(ctx);err!=nil{return err}
 }
 g.closed=true;g.joined=0
 return nil
}

// FirstOriginalOwner anchors the existing one-Wintun native OS/WAL lease.
// It does not substitute the first lane for the authenticated Game group.
func(g *V4WindowsAuthenticatedGameGroup) FirstOriginalOwner()*V4WindowsAuthenticatedClientOwner{
 if g==nil{return nil}
 g.mu.Lock();defer g.mu.Unlock()
 if g.closed||len(g.members)<2{return nil}
 return g.members[0]
}
func(g *V4WindowsAuthenticatedGameGroup) OriginalGameTCPBoundaries()([][2]uint32,error){
 if g==nil{return nil,errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 if g.closed||len(g.members)<2{return nil,errV4WindowsOwner}
 v:=make([][2]uint32,0,len(g.members))
 for _,o:=range g.members{
  tx,rx,err:=o.OriginalVerifiedTCPBoundaries()
  if err!=nil{return nil,err}
  v=append(v,[2]uint32{tx,rx})
 }
 return v,nil
}
