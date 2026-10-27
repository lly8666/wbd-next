//go:build windows && wbd_v4_embedded_go
package realityfront

import (
 "context"
 "sync/atomic"
 "testing"
 "time"
)
type hotLeaseFakeNative struct{audits atomic.Int64}
func(f *hotLeaseFakeNative) HoldCurrentNative(context.Context,V4WindowsNativeDeviceIdentity)(func(),error){
 return func(){},nil
}
func(f *hotLeaseFakeNative) VerifyCurrentNative(context.Context,V4WindowsNativeDeviceIdentity)error{
 f.audits.Add(1);return nil
}
func TestM0RemediationVerifiedRealHandleHotBorrowBlocksOwnedStop(t *testing.T){
 ep:=[16]byte{1}
 b:=&v4WindowsNativeOwnerBridge{handle:99,committed:true,epoch:ep}
 dev:=&hotLeaseFakeNative{}
 l:=&v4WindowsRealDeviceLease{bridge:b,device:dev,
  identity:V4WindowsNativeDeviceIdentity{Generation:ep},release:func(){}}
 l.lastAuditNS.Store(time.Now().UnixNano())
 done,e:=l.borrowHot(context.Background());if e!=nil{t.Fatal(e)}
 entered:=make(chan struct{});completed:=make(chan struct{})
 go func(){
  close(entered)
  l.mu.Lock();l.stopped=true;l.invalid.Store(true);l.mu.Unlock()
  close(completed)
 }()
 <-entered
 select{case <-completed:t.Fatal("Stop bypassed active authenticated packet borrow")
 case <-time.After(5*time.Millisecond):}
 done()
 select{case <-completed:case <-time.After(time.Second):t.Fatal("Stop did not drain borrow")}
 if extra,e:=l.borrowHot(context.Background());e==nil{
  extra();t.Fatal("revoked generation loan accepted")
 }
 if dev.audits.Load()!=0{t.Fatal("per packet OS query incurred on freshly verified lease")}
}
