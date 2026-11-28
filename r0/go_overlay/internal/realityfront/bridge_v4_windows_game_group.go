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
 anchor *V4WindowsAuthenticatedClientOwner
 staged,retiring *V4WindowsGameLaneCandidate
 epoch [16]byte
 authenticatedLease string
 authenticatedCipher uint8
 joined uint64
 stageProc,receiveProc,offFinishProc,joinProc,stopProc,effectiveMtuProc *syscall.Proc
 maxIPv4 int
 fecOpenProc,fecFinishProc *syscall.Proc
 fecParityProc,fecM4SendProc *syscall.Proc
 gameFec uint8 // authenticated TLS GameFec=1..7 -> shared fixed profile0..6
 paddingMode uint8 // one client-selected protected value on every Game lane
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
 if len(gameFec)>2{return nil,ErrAdmissionParams}
 var negotiatedFec uint8
 if len(gameFec)>0{negotiatedFec=gameFec[0]}
 var startupPadding uint8
 if len(gameFec)==2{startupPadding=gameFec[1]}
 if negotiatedFec>7||startupPadding>2{return nil,ErrAdmissionUnsupported}
 if ctx==nil||(n!=2&&n!=4)||base.Policy.Transport!=TransportGame||
  int(base.Policy.DesiredLanes)!=n||int(base.DesiredLanes)!=n||
  base.Policy.SupportedNow()!=nil{return nil,ErrAdmissionUnsupported}
 g:=&V4WindowsAuthenticatedGameGroup{gameFec:negotiatedFec,paddingMode:startupPadding}
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
  session,e:=establishWindowsGameLaneTLS(ctx,assoc,cfg,g.epoch,g.gameFec,g.paddingMode)
  if e!=nil{return fail(e)}
  if i==0{g.epoch=session.Epoch}
  if session.Epoch!=g.epoch||g.epoch==[16]byte{}{return fail(ErrAdmissionUnsupported)}
  lease,leaseErr:=session.AuthenticatedLeaseIPv4()
  snap,snapErr:=session.ColdSnapshot()
  if leaseErr!=nil||snapErr!=nil||snap.Cipher()!=base.Policy.Cipher||
     snap.StartupPaddingMode()!=g.paddingMode{
   return fail(fmt.Errorf("Game protected per-lane network selection mismatch: %w",ErrAdmissionUnsupported))
  }
  if i==0{g.authenticatedLease=lease;g.authenticatedCipher=snap.Cipher()
  }else if lease!=g.authenticatedLease||snap.Cipher()!=g.authenticatedCipher{
   return fail(ErrAdmissionUnsupported)
  }
  handoff,e:=assoc.Detach()
  if e!=nil{return fail(e)}
  // No extra RTT or delay: repeat the already-earned final TLS ACK
  // twice before this cold association moves to the native owner.
  for j:=0;j<2;j++{_,_=assoc.RepeatGameColdFinalACK(nil)}
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
// AuthenticatedNetworkSelection is read only after all sibling TLS lanes
// commit the SAME protected address and cipher. It is not a Wintun grant.
func(g *V4WindowsAuthenticatedGameGroup) AuthenticatedNetworkSelection()(string,uint8,error){
 if g==nil{return "",0,errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 if g.closed||len(g.sessions)!=len(g.members)||
  (len(g.members)!=2&&len(g.members)!=4)||g.authenticatedCipher==0{
  return "",0,errV4WindowsOwner
 }
 return g.authenticatedLease,g.authenticatedCipher,nil
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
  {"wbd_m0_win_owner_v4_game_prepare_off",&g.receiveProc},
  {"wbd_m0_win_owner_v4_game_finish_off",&g.offFinishProc},
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
 g.anchor=g.members[0]
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
// One true current per-lane Rust budget snapshot, under the original
// live M4-created Wintun lease and the same native Game group. Call only
// at low frequency or an owned path-reconfiguration boundary, never on
// every logical Game/NPF source packet. Does not edit OS MTU/route/WFP.
func(g *V4WindowsAuthenticatedGameGroup) RefreshGamePayloadMTU(
 ctx context.Context,
)(int,error){
 if g==nil||ctx==nil{return 0,errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 if g.closed||g.joined==0||g.effectiveMtuProc==nil{return 0,errV4WindowsOwner}
 release,err:=g.holdLive(ctx)
 if err!=nil{return 0,err}
 defer release()
 var cap uint32
 err=winOwnerCall(g.effectiveMtuProc,uintptr(g.joined),
  uintptr(unsafe.Pointer(&cap)))
 if err!=nil||cap<20||cap>1536-31-16{
  return 0,errors.Join(errV4WindowsOwner,err)
 }
 g.maxIPv4=int(cap)
 return int(cap),nil
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
// OpenGameRecord now STAGES (never confirms) an authenticated Game/off first
// logical candidate in the original Rust owner. Positive bytes require an
// exact one-packet CompleteGameOff after real Wintun write; zero means no
// pending candidate and no copy. This Go path cannot claim a success early.
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
// CompleteGameOff is called once per successfully prepared off candidate,
// including definite kernel Wintun copy failures. No new Go packet pump.
func(g *V4WindowsAuthenticatedGameGroup) CompleteGameOff(
 ctx context.Context,lane uint32,copied uint32,
)error{
 if g==nil||ctx==nil||copied>1{return errV4WindowsOwner}
 g.mu.Lock();defer g.mu.Unlock()
 release,err:=g.holdLive(ctx)
 if err!=nil{return err}
 defer release()
 if g.gameFec!=0||g.offFinishProc==nil||lane==0||
  int(lane)>len(g.members){return errV4WindowsOwner}
 return winOwnerCall(g.offFinishProc,uintptr(g.joined),uintptr(lane),
  uintptr(copied))
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
 owners:=append([]*V4WindowsAuthenticatedClientOwner(nil),g.members...)
 if g.anchor!=nil{owners=append(owners,g.anchor)}
 if g.staged!=nil{owners=append(owners,g.staged.owner)}
 if g.retiring!=nil{owners=append(owners,g.retiring.old)}
 seen:=map[*V4WindowsAuthenticatedClientOwner]bool{}
 unique:=owners[:0]
 for _,s:=range owners{if !seen[s]{seen[s]=true;unique=append(unique,s)}}
 for _,s:=range unique{
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
 for _,s:=range unique{
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
 if g.anchor!=nil{return g.anchor}
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

func establishWindowsGameLaneTLS(ctx context.Context,assoc *faketcp.ClientAssociation,
 cfg ClientAdmissionConfig,epoch [16]byte,gameFec,paddingMode uint8,
)(*V4ClientSession,error){
  // The SYN loop has finished, but each lane still has real TLS DATA
  // in the original FakeTCP Sender. Drive its RTO until TLS returns,
  // then join before Detach so no Go send can race the Rust owner.
  pumpCtx,stopPump:=context.WithCancel(ctx)
  type coldResult struct{copied uint64;err error}
  pumpDone:=make(chan coldResult,1)
  go func(){
   ticker:=time.NewTicker(100*time.Millisecond)
   defer ticker.Stop()
   var copied uint64
   for{
    select{
    case <-pumpCtx.Done():pumpDone<-coldResult{copied:copied};return
    case <-ticker.C:
     if assoc.State()!=faketcp.ClientAssociationEstablished{
      pumpDone<-coldResult{copied:copied};return
     }
     sent,err:=assoc.EmitRetransmitDue(time.Now())
     if err!=nil{assoc.Close();pumpDone<-coldResult{copied,err};return}
     if sent{copied++}
    }
   }
  }()
  session,e:=EstablishClientV4(ctx,assoc.BootstrapConn(),cfg,
   V4ClientOptions{DataPlaneReady:true,Epoch:epoch,
    fec2Product:true,GameFec:gameFec,StartupPadding:paddingMode})
  stopPump()
  pump:=<-pumpDone
  fmt.Printf("WBD_WINDOWS_GAME_COLD_TLS_LANE lane=%d rto_copied=%d joined=1 result=%t\n",cfg.LaneID,pump.copied,e==nil&&pump.err==nil)
  if e!=nil||pump.err!=nil{return nil,fmt.Errorf("Game lane %d original TLS: %w",cfg.LaneID,errors.Join(e,pump.err))}
 return session,nil
}

// The candidate is still not a physical M4 member. The caller must stop
// its original cold reader before native staging, and the Rust workers
// must independently prove its new AEAD path before publishing it.
type V4WindowsGameLaneCandidate struct{
 lane uint8
 old,owner *V4WindowsAuthenticatedClientOwner
 session *V4ClientSession
}
// Stage only after the original candidate association has detached and its
// Go reader/writer has joined. Readiness is the original native worker's
// accepted copy plus the candidate's own authenticated reverse record.
func(g *V4WindowsAuthenticatedGameGroup) StageNativeLaneCandidate(ctx context.Context,c *V4WindowsGameLaneCandidate,transport *faketcp.XdpGameCandidate,peerPort uint16)error{
 if g==nil||c==nil||transport==nil||ctx==nil||peerPort==0{return errV4WindowsOwner}
 if err:=ctx.Err();err!=nil{return err}
 tx,rx,err:=c.TCPBoundaries();if err!=nil{return err}
 g.mu.Lock();defer g.mu.Unlock()
 if g.closed||g.joined==0||c.lane<1||int(c.lane)>len(g.members)||g.members[c.lane-1]!=c.old{return errV4WindowsOwner}
 if g.staged!=nil||g.retiring!=nil{return errV4WindowsOwner}
 g.staged=c
 proc,err:=c.old.bridge.fixedProc("wbd_m0_win_game_candidate_stage");if err!=nil{return err}
 if err=transport.TakeNative();err!=nil{return err}
 return winOwnerCall(proc,uintptr(g.joined),uintptr(c.lane),uintptr(c.old.bridge.handle),uintptr(c.owner.bridge.handle),uintptr(transport.CandidatePort()),uintptr(peerPort),uintptr(tx),uintptr(rx))
}
func(g *V4WindowsAuthenticatedGameGroup) NativeLaneCandidateReady(ctx context.Context,c *V4WindowsGameLaneCandidate,transport *faketcp.XdpGameCandidate)(bool,error){
 if g==nil||ctx==nil||c==nil||transport==nil{return false,errV4WindowsOwner}
 if err:=ctx.Err();err!=nil{return false,err}
 g.mu.Lock();defer g.mu.Unlock()
 if g.closed||g.joined==0||c.lane<1||int(c.lane)>len(g.members)||g.members[c.lane-1]!=c.old{return false,errV4WindowsOwner}
 proc,err:=c.old.bridge.fixedProc("wbd_m0_win_game_candidate_ready");if err!=nil{return false,err}
 rc,_,_:=proc.Call(uintptr(g.joined),uintptr(transport.CandidatePort()))
 if int32(rc)!=0&&int32(rc)!=1{return false,errV4WindowsOwner}
 return rc==1,nil
}
func(c *V4WindowsGameLaneCandidate) TCPBoundaries()(uint32,uint32,error){
 if c==nil||c.owner==nil{return 0,0,errV4WindowsOwner}
 return c.owner.OriginalVerifiedTCPBoundaries()
}
// Only legal before native selected-slot commit. A committed physical lane
// is retired by the existing group/worker ownership transaction instead.
func(c *V4WindowsGameLaneCandidate) Abort(ctx context.Context)error{
 if c==nil||c.owner==nil{return errV4WindowsOwner}
 return c.owner.StopScopedOwner(ctx)
}

// Authenticate one same-epoch original Go TLS association just like the
// Linux ReplaceClientGameLane. Do not hold g.mu across network or TLS:
// the old group and all siblings remain live. The caller serializes
// turns and supplies the actual candidate-only FakeTCP reader/writer.
func(g *V4WindowsAuthenticatedGameGroup) PrepareOriginalGameLaneCandidate(
 ctx context.Context,assoc *faketcp.ClientAssociation,base ClientAdmissionConfig,lane uint8,
)(*V4WindowsGameLaneCandidate,error){
 if g==nil||ctx==nil||assoc==nil||assoc.BootstrapConn()==nil||
    lane<1||lane>base.DesiredLanes||base.Policy.Transport!=TransportGame||
    (base.DesiredLanes!=2&&base.DesiredLanes!=4)||base.Policy.DesiredLanes!=base.DesiredLanes||base.Policy.SupportedNow()!=nil{
  return nil,ErrAdmissionParams
 }
 if err:=ctx.Err();err!=nil{return nil,err}
 i:=int(lane)-1
 g.mu.Lock()
 if g.closed||g.joined==0||len(g.members)!=int(base.DesiredLanes)||len(g.sessions)!=len(g.members)||g.staged!=nil||g.retiring!=nil{
  g.mu.Unlock();return nil,ErrAdmissionUnsupported
 }
 old:=g.members[i];previous:=g.sessions[i]
 if old==nil||old.bridge==nil||old.device==nil||previous==nil{
  g.mu.Unlock();return nil,errV4WindowsOwner
 }
 sessions:=append([]*V4ClientSession(nil),g.sessions...)
 epoch,fec,padding,lease,cipher:=g.epoch,g.gameFec,g.paddingMode,g.authenticatedLease,g.authenticatedCipher
 library:=old.bridge.dll.Name
 device:=old.device
 joined:=g.joined
 g.mu.Unlock()
 prior,e:=previous.ColdSnapshot()
 if e!=nil{return nil,e}
 base.LaneID=lane
 session,e:=establishWindowsGameLaneTLS(ctx,assoc,base,epoch,fec,padding)
 if e!=nil{return nil,e}
 fresh,e:=session.ColdSnapshot()
 actualLease,le:=session.AuthenticatedLeaseIPv4()
 if e!=nil||le!=nil||session.Epoch!=epoch||fresh.Cipher()!=cipher||
    fresh.StartupPaddingMode()!=padding||actualLease!=lease||
    prior.laneID!=lane||fresh.laneID!=lane||
    prior.server!=fresh.server||prior.principal!=fresh.principal||
    prior.tunnelID!=fresh.tunnelID||prior.epoch!=fresh.epoch||
    prior.features!=fresh.features||prior.cipher!=fresh.cipher||
    prior.clientLimit!=fresh.clientLimit||prior.serverLimit!=fresh.serverLimit||
    prior.incarnation==fresh.incarnation||prior.keys.C2S==fresh.keys.C2S||
    prior.keys.S2C==fresh.keys.S2C{
  return nil,ErrAdmissionParams
 }
 // Reuse complete group identity/key uniqueness check for every sibling.
 sessions[i]=session
 if _,e=v4OriginalGameClientColdSet(sessions...);e!=nil{return nil,e}
 b,e:=newV4WindowsPrivateOwnerBridge(library)
 if e!=nil{return nil,e}
 owner:=&V4WindowsAuthenticatedClientOwner{bridge:b}
 fail:=func(cause error)(*V4WindowsGameLaneCandidate,error){
  stop,cancel:=context.WithTimeout(context.Background(),15*time.Second);defer cancel()
  if b.committed{cause=errors.Join(cause,owner.StopScopedOwner(stop))}
  if b.handle==0{_ = b.dll.Release()}
  return nil,cause
 }
 handoff,e:=assoc.Detach();if e!=nil{return fail(e)}
 for j:=0;j<2;j++{_,_=assoc.RepeatGameColdFinalACK(nil)}
 if e=b.prepareAuthenticatedClient(session,handoff,assoc.Flow());e!=nil{return fail(e)}
 // Pin the exact existing Wintun; retain the original authenticated
 // budget inputs rather than rebinding it using an unrelated inner MTU.
 var geometry []uint32
 if device.originalGeometry[0]!=0{geometry=device.originalGeometry[:]}
 held,e:=b.holdOriginalCreatedWintunBudget(ctx,device.device,device.identity,device.originalPathMTU,geometry...)
 if held!=nil{owner.device=held}
 if e!=nil{return fail(e)}
 if held.maxIPv4!=device.maxIPv4{return fail(ErrAdmissionParams)}
 g.mu.Lock()
 unchanged:=!g.closed&&g.joined==joined&&g.members[i]==old&&g.sessions[i]==previous
 g.mu.Unlock()
 if !unchanged{return fail(ErrAdmissionUnsupported)}
 return &V4WindowsGameLaneCandidate{lane:lane,old:old,owner:owner,session:session},nil
}

func(g *V4WindowsAuthenticatedGameGroup) OfferNativeGameCandidateEarly(c *V4WindowsGameLaneCandidate,port uint16,seq uint32,wire []byte)error{
 g.mu.Lock();defer g.mu.Unlock()
 if g.staged!=c||len(wire)==0{return errV4WindowsOwner}
 proc,err:=c.owner.bridge.fixedProc("wbd_m0_win_game_candidate_early");if err!=nil{return err}
 err=winOwnerCall(proc,uintptr(g.joined),uintptr(port),uintptr(seq),uintptr(unsafe.Pointer(&wire[0])),uintptr(len(wire)))
 runtime.KeepAlive(wire);return err
}
func(g *V4WindowsAuthenticatedGameGroup) PromoteNativeGameLane(ctx context.Context,c *V4WindowsGameLaneCandidate,port uint16,grace time.Duration)error{
 g.mu.Lock();defer g.mu.Unlock()
 if g.staged!=c||g.retiring!=nil{return errV4WindowsOwner}
 proc,err:=c.owner.bridge.fixedProc("wbd_m0_win_game_candidate_promote");if err!=nil{return err}
 if err=winOwnerCall(proc,uintptr(g.joined),uintptr(port),uintptr(grace.Milliseconds()));err!=nil{return err}
 status,err:=c.owner.bridge.fixedProc("wbd_m0_win_game_candidate_status");if err!=nil{return err}
 tick:=time.NewTicker(25*time.Millisecond);defer tick.Stop()
 for{
  rc,_,_:=status.Call(uintptr(g.joined),uintptr(c.old.bridge.handle),uintptr(c.owner.bridge.handle))
  if int32(rc)<0{return errV4WindowsOwner}
  if rc>=1{break}
  select{case <-ctx.Done():return ctx.Err();case <-tick.C:}
 }
 g.members[c.lane-1]=c.owner;g.sessions[c.lane-1]=c.session
 g.retiring=c;g.staged=nil
 return nil
}
func(g *V4WindowsAuthenticatedGameGroup) RetireNativeGameLane(ctx context.Context)(bool,error){
 g.mu.Lock();defer g.mu.Unlock()
 c:=g.retiring;if c==nil{return true,nil}
 status,err:=c.owner.bridge.fixedProc("wbd_m0_win_game_candidate_status");if err!=nil{return false,err}
 rc,_,_:=status.Call(uintptr(g.joined),uintptr(c.old.bridge.handle),uintptr(c.owner.bridge.handle))
 if int32(rc)<0{return false,errV4WindowsOwner};if rc!=2{return false,nil}
 if c.old!=g.anchor{if err=c.old.StopScopedOwner(ctx);err!=nil{return false,err}}
 g.retiring=nil;return true,nil
}
