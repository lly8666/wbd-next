//go:build windows && wbd_v4_embedded_go
package realityfront

// Original credential TLS -> exact Rust mature M2 / k histogram ->
// the ALREADY validated Linux FecV2Step shared Go controller.
import(
 "context"
 "errors"
 "fmt"
 "runtime"
 "time"
 "unsafe"
)
type V4WindowsAutoQuality struct {
 Version,Size uint32
 Revision uint64
 Counters [30]uint64
}
func(s *V4WindowsAuthenticatedClientOwner) ReadBoundOriginalAutoQuality(
 ctx context.Context,
)(V4WindowsAutoQuality,error){
 var v V4WindowsAutoQuality
 if ctx==nil||s==nil||s.bridge==nil||s.device==nil{return v,errV4WindowsOwner}
 if err:=s.device.device.VerifyCurrentNative(ctx,s.device.identity);err!=nil{return v,err}
 proc,err:=s.bridge.dll.FindProc("wbd_m0_win_owner_v8_fec2_auto_quality")
 if err!=nil{return v,err}
 err=winOwnerCall(proc,uintptr(s.bridge.handle),
  uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
  uintptr(s.device.identity.LUID),uintptr(s.device.identity.InterfaceIndex),
  uintptr(unsafe.Pointer(&v)),uintptr(unsafe.Sizeof(v)))
 runtime.KeepAlive(s.bridge.epoch)
 if err!=nil||v.Version!=1||v.Size!=uint32(unsafe.Sizeof(v))||v.Revision==0{
  return V4WindowsAutoQuality{},errors.Join(errV4WindowsOwner,err)
 }
 return v,nil
}
type winAutoPoint struct{at time.Duration;v V4WindowsAutoQuality}
type winAutoBackend struct {
 owner *V4WindowsAuthenticatedClientOwner
 epoch [16]byte
 client string
 revision uint64
 profile FecV2Profile
 history []winAutoPoint
}
func(b *winAutoBackend) withRead()(V4WindowsAutoQuality,error){
 ctx,cancel:=context.WithTimeout(context.Background(),8*time.Second)
 defer cancel()
 return b.owner.ReadBoundOriginalAutoQuality(ctx)
}
func(b *winAutoBackend) Stage(epoch [16]byte,intent FecV2Intent)error{
 if epoch!=b.epoch||intent.Client!=b.client||
  intent.Direction!=FecV2C2S||!intent.Profile.Valid(){return ErrFecV2Scope}
 ctx,cancel:=context.WithTimeout(context.Background(),8*time.Second)
 defer cancel()
 if intent.Revision==1 {
  // Native revision1 already selected before any kernel first-send.
  v,err:=b.owner.ReadBoundOriginalAutoQuality(ctx)
  if err!=nil||v.Revision!=1{return errors.Join(ErrFecV2Revision,err)}
 }else{
  if err:=b.owner.RequestBoundOriginalFEC2Revision(ctx,intent.Profile,intent.Revision);err!=nil{
   return err
  }
 }
 b.revision,b.profile=intent.Revision,intent.Profile
 return nil
}
func(b *winAutoBackend) Readback(epoch [16]byte,client string,
 direction FecV2Direction)(FecV2Ack,error){
 ack:=FecV2Ack{Client:client,Direction:direction,Revision:b.revision,Profile:b.profile}
 if epoch!=b.epoch||client!=b.client||direction!=FecV2C2S{return ack,ErrFecV2Scope}
 if b.revision==0{return ack,nil}
 q,err:=b.withRead()
 if err!=nil{return ack,err}
 if q.Revision!=b.revision{return ack,nil}
 ctx,cancel:=context.WithTimeout(context.Background(),8*time.Second)
 defer cancel()
 m,err:=b.owner.ReadBoundOriginalFixedMature(ctx)
 if err!=nil{return ack,err}
 ack.Applied=m.Applied==1&&m.Censored==0
 return ack,nil
}
func winAutoDiff(then,now uint64)(uint64,bool){
 if now<then{return 0,false}
 return now-then,true
}
func winAutoWindow(now,then [30]uint64,start int)(FecV2Window,bool){
 var d [5]uint64
 for i:=0;i<5;i++{
  n,ok:=winAutoDiff(then[start+i],now[start+i])
  if !ok{return FecV2Window{},false}
  d[i]=n
 }
 return FecV2Window{
  FirstSent:d[0],Observed:d[1]+d[2],Missing:d[2],Unknown:d[3]+d[4],
 },d[0]==d[1]+d[2]+d[3]+d[4]
}
func(b *winAutoBackend) Observe(epoch [16]byte,client string,
 direction FecV2Direction,now time.Duration)(FecV2Snapshot,error){
 s:=FecV2Snapshot{Client:client,Direction:direction,At:now,Validity:FecV2Unknown}
 if epoch!=b.epoch||client!=b.client||direction!=FecV2C2S{return s,ErrFecV2Scope}
 q,err:=b.withRead()
 if err!=nil{return s,err}
 b.history=append(b.history,winAutoPoint{now,q})
 if len(b.history)>12{b.history=b.history[len(b.history)-12:]}
 floor:=func(age time.Duration)([30]uint64,bool){
  for i:=len(b.history)-1;i>=0;i--{
   if b.history[i].at<=now-age{return b.history[i].v.Counters,true}
  }
  return [30]uint64{},false
 }
 fast,okFast:=floor(2*time.Second)
 slow,okSlow:=floor(8*time.Second)
 hist,okHist:=floor(16*time.Second)
 if !okFast||!okSlow||!okHist{return s,nil}
 raw:=q.Counters
 var ok bool
 s.Fast,ok=winAutoWindow(raw,fast,0);if !ok{return s,nil}
 s.Slow,ok=winAutoWindow(raw,slow,5);if !ok{return s,nil}
 for k:=0;k<16;k++{
  n,valid:=winAutoDiff(hist[14+k],slow[14+k])
  if !valid{return s,nil}
  s.ActualK[k]=n
 }
 capacity,valid:=winAutoDiff(hist[11],raw[11])
 if !valid{return s,nil}
 if capacity!=0{s.Validity=FecV2HostCapacity;s.HostDrops=capacity;return s,nil}
 receipts,valid:=winAutoDiff(slow[10],raw[10])
 if !valid||receipts==0{return s,nil}
 lag,valid:=winAutoDiff(slow[12],raw[12]);if !valid{return s,nil}
 count,valid:=winAutoDiff(slow[13],raw[13])
 if !valid||count==0||lag/count>uint64((1<<63)-1){return s,nil}
 s.SRTT=time.Duration(lag/count);s.Validity=FecV2Valid
 return s,nil
}
type V4WindowsOriginalFEC2AutoController struct{core *fecV2ControlRuntime}
func NewV4WindowsOriginalFEC2AutoController(
 owner *V4WindowsAuthenticatedClientOwner,policy FecV2AutoPolicy,
 initial FecV2Profile,
)(*V4WindowsOriginalFEC2AutoController,error){
 if owner==nil||owner.bridge==nil||owner.device==nil||!initial.Valid(){
  return nil,errV4WindowsOwner
 }
 epoch:=owner.bridge.epoch
 client:=fmt.Sprintf("%x",epoch)
 backend:=&winAutoBackend{owner:owner,epoch:epoch,client:client,
  history:make([]winAutoPoint,0,12)}
 cfg:=FecV2Config{
  Client:client,Direction:FecV2C2S,Transport:FecV2Normal,
  Mode:FecV2Auto,AutoPolicy:policy,StartProfile:&initial,ConfigRevision:1,
 }
 core,err:=newFecV2ControlRuntime(cfg,epoch,backend)
 if err!=nil{return nil,err}
 return &V4WindowsOriginalFEC2AutoController{core:core},nil
}
func(c *V4WindowsOriginalFEC2AutoController) Start()error{
 if c==nil||c.core==nil{return errV4WindowsOwner}
 if err:=c.core.Tick(0);err!=nil{return err}
 return c.core.Start()
}
func(c *V4WindowsOriginalFEC2AutoController) Stop(){
 if c!=nil&&c.core!=nil{c.core.Stop()}
}
func(c *V4WindowsOriginalFEC2AutoController) Snapshot()(FecV2State,error){
 if c==nil||c.core==nil{return FecV2State{},errV4WindowsOwner}
 return c.core.Snapshot()
}
