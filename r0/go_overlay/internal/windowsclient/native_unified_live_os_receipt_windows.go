//go:build windows

package windowsclient

import (
  "context"
  "encoding/json"
  "errors"
  "os"
)

// N4NativeLiveOSReceipt is an independently verified, *live* Win32 state
// certificate for the five durable native stages. It is not proof that
// original-Go credentials, Rust AEAD, business I/O or WinForms are connected.
// Product admission must join this receipt to its active TLS/Rust owner on
// the SAME installation/generation before publishing Applied.
type N4NativeLiveOSReceipt struct {
 Schema string `json:"schema"`
 Phase string `json:"phase"`
 WintunIndex uint32 `json:"wintun_index"`
 WintunLUID uint64 `json:"wintun_luid"`
 GuardOwned bool `json:"guard_owned"`
 LeaseOwned bool `json:"lease_owned"`
 MTUOwned bool `json:"mtu_owned"`
 DNSOwned bool `json:"dns_owned"`
 RoutesOwned bool `json:"routes_owned"`
 AllNativeOSApplied bool `json:"all_native_os_applied"`
}
const N4NativeLiveOSSchema = "wbd-n4-live-os-owned/v1"

// VerifyLiveOSApplied never assumes that a valid disk WAL equals an OS
// installation. With the same cross-process gate and LIVE Wintun reservation
// held across all five independent native reads, even one foreign/missing
// WFP/lease/MTU/DNS/route rejects Applied.
func (n *N4NativeUnifiedTxn) VerifyLiveOSApplied(ctx context.Context)(N4NativeLiveOSReceipt,error){
 result:=N4NativeLiveOSReceipt{Schema:N4NativeLiveOSSchema}
 if n==nil||n.assemblyOnly||ctx==nil{return result,ErrN4NativeGuard}
 n.mu.Lock();defer n.mu.Unlock()
 release,err:=n.withGate(ctx);if err!=nil{return result,err}
 defer release()
 j,err:=n4UnifiedRead(n.Path);if err!=nil{return result,err}
 if j.Identity!=n.Identity || j.Phase!="active" ||
  len(j.Records)!=len(n4UnifiedOrder){return result,ErrN4JournalConflict}
 for i,s:=range n.Stages{
  if j.Records[i].State!="owned"||j.Records[i].Name!=n4UnifiedOrder[i]{
   return result,ErrN4JournalConflict
  }
  if err:=ctx.Err();err!=nil{return result,err}
  status,err:=s.Inspect(ctx,n.Identity,j.Records[i].Before)
  if err!=nil{return result,err}
  if status==N4UnifiedForeign{return result,ErrN4ForeignRoute}
  if status!=N4UnifiedOwned{return result,ErrN4NativeGuard}
 }
 result.Phase="active"
 result.WintunIndex=n.Identity.WintunIndex
 result.WintunLUID=n.Identity.WintunLUID
 result.GuardOwned=true;result.LeaseOwned=true;result.MTUOwned=true
 result.DNSOwned=true;result.RoutesOwned=true
 result.AllNativeOSApplied=true
 return result,ctx.Err()
}

// VerifyLiveOSDisconnected is the *post-Stop* readback. Reuse the SAME
// machine mutex/current Wintun OS generation, reject any surviving WAL,
// route intent or pre-existing/foreign native WFP/route/lease/DNS settings.
// Never claim disconnected just because a process exited or a file vanished.
// The caller is responsible for draining authenticated Rust/kernel loans
// BEFORE invoking the original Recover/Stop and this final readback.
func (n *N4NativeUnifiedTxn) VerifyLiveOSDisconnected(ctx context.Context)error{
 if n==nil||n.assemblyOnly||ctx==nil{return ErrN4NativeGuard}
 n.mu.Lock();defer n.mu.Unlock()
 release,err:=n.withGate(ctx);if err!=nil{return err}
 defer release()
 if _,err:=os.Lstat(n.Path);err==nil{return ErrN4JournalConflict
 }else if !errors.Is(err,os.ErrNotExist){return err}
 for _,path:=range []string{n.Path+".routes"}{
  if _,err:=os.Lstat(path);err==nil{return ErrN4JournalConflict
  }else if !errors.Is(err,os.ErrNotExist){return err}
 }
 for _,s:=range n.Stages{
  if err:=ctx.Err();err!=nil{return err}
  // Snapshot is an OS-native read-only absence preflight; unlike a disk
  // absence check, it fails on existing foreign WFP, DNS, route and lease.
  receipt,err:=s.Snapshot(ctx,n.Identity)
  if err!=nil{return err}
  if len(receipt)==0||!json.Valid(receipt){return ErrN4NativeGuard}
 }
 return ctx.Err()
}
