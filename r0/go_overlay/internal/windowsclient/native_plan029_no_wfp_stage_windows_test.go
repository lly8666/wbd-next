//go:build windows

package windowsclient

import (
 "context"
 "errors"
 "net/netip"
 "testing"
)

// Pure state-machine test only: it deliberately NEVER opens real Win32
// routes/adapter. Real signed OS Apply, Stop and crash partial remain OPEN.
type p029RouteView struct{
 present map[NativeRouteKey]bool
 exact map[NativeRouteKey]bool
 writes int
}
func(b *p029RouteView) Lookup(_ context.Context,k NativeRouteKey)(bool,bool,error){
 return b.present[k],b.exact[k],nil
}
func(b *p029RouteView) CreateIfAbsent(context.Context,NativeRouteKey)error{
 b.writes++;return errors.New("test-only backend may never mutate")
}
func(b *p029RouteView) RemoveOwned(context.Context,NativeRouteKey)error{
 b.writes++;return errors.New("test-only backend may never mutate")
}
func TestPlan029NoWFPRoutesPartialIsNeverClaimedFullyOwned(t *testing.T){
 keys:=[]NativeRouteKey{
  {Prefix:netip.MustParsePrefix("203.0.113.12/32"),Interface:9,
   NextHop:netip.MustParseAddr("192.0.2.1"),Metric:5},
  {Prefix:netip.MustParsePrefix("0.0.0.0/1"),Interface:21,
   NextHop:netip.MustParseAddr("0.0.0.0"),Metric:5},
  {Prefix:netip.MustParsePrefix("128.0.0.0/1"),Interface:21,
   NextHop:netip.MustParseAddr("0.0.0.0"),Metric:5},
 }
 fake:=&p029RouteView{present:map[NativeRouteKey]bool{},exact:map[NativeRouteKey]bool{}}
 stage:=n4WindowsNoWFPRouteStage{Backend:fake}
 check:=func(want N4UnifiedState){
  t.Helper()
  got,err:=stage.inspectKeys(context.Background(),keys)
  if err!=nil||got!=want{t.Fatalf("route state %v expected %v: %v",got,want,err)}
  if fake.writes!=0{t.Fatal("read-only classification changed routes")}
 }
 check(N4UnifiedAbsent)
 fake.present[keys[0]]=true;fake.exact[keys[0]]=true
 check(N4UnifiedPartial)
 fake.present[keys[1]]=true;fake.exact[keys[1]]=true
 fake.present[keys[2]]=true;fake.exact[keys[2]]=true
 check(N4UnifiedOwned)
 fake.exact[keys[2]]=false
 check(N4UnifiedForeign)
}
func TestPlan029NoWFPAssemblerCannotActivateWithoutOwnedRealWintun(t *testing.T){
 _,err:=n4AssembleWindowsNoWFPNativeTxn(context.Background(),nil,NetworkPlan{},N4UnifiedIdentity{})
 if !errors.Is(err,ErrN4ForeignRoute){t.Fatalf("nil/borrowed Wintun unexpectedly assembled: %v",err)}
}
