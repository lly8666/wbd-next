//go:build windows

package windowsclient

import (
 "context"
 "errors"
 "net/netip"
 "os"
 "path/filepath"
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

 // Pure route sidecar harness: exact keys and backend, zero Win32/WFP calls.
 // Inject failures on either side of CreateIfAbsent's ownership boundary.
type p029JournalRouteBackend struct{
 present map[NativeRouteKey]bool
 foreign map[NativeRouteKey]bool
 creates,removes,failBefore,failAfter int
}
func p029NewJournalRouteBackend()*p029JournalRouteBackend{
 return &p029JournalRouteBackend{
  present:make(map[NativeRouteKey]bool),foreign:make(map[NativeRouteKey]bool),
 }
}
func(b *p029JournalRouteBackend) Lookup(_ context.Context,k NativeRouteKey)(bool,bool,error){
 return b.present[k],!b.foreign[k],nil
}
func(b *p029JournalRouteBackend) CreateIfAbsent(_ context.Context,k NativeRouteKey)error{
 b.creates++
 if b.failBefore==b.creates{return errors.New("injected before CreateIfAbsent")}
 if b.present[k]{return ErrN4ForeignRoute}
 b.present[k]=true
 if b.failAfter==b.creates{return errors.New("injected after CreateIfAbsent")}
 return nil
}
func(b *p029JournalRouteBackend) RemoveOwned(_ context.Context,k NativeRouteKey)error{
 if !b.present[k]||b.foreign[k]{return ErrN4ForeignRoute}
 delete(b.present,k);b.removes++;return nil
}
func p029V2RouteKeys()[]NativeRouteKey{return []NativeRouteKey{
 {Prefix:netip.MustParsePrefix("203.0.113.12/32"),Interface:9,
  NextHop:netip.MustParseAddr("192.0.2.1"),Metric:5},
 {Prefix:netip.MustParsePrefix("0.0.0.0/1"),Interface:21,
  NextHop:netip.MustParseAddr("0.0.0.0"),Metric:5},
 {Prefix:netip.MustParsePrefix("128.0.0.0/1"),Interface:21,
  NextHop:netip.MustParseAddr("0.0.0.0"),Metric:5},
}}
func TestPlan029NoWFPV2RouteSidecarFullAndPartialOwnedRecovery(t *testing.T){
 ctx:=context.Background()
 id:=n4TestConcreteNativeIdentity()
 keys:=p029V2RouteKeys()
 if e:=n4ValidateRouteBatch(keys);e!=nil{t.Fatal(e)}
 path:=filepath.Join(t.TempDir(),"v2.routes")
 b:=p029NewJournalRouteBackend()
 if err:=n4NoWFPApplyRoutes(ctx,path,id,keys,b);err!=nil{t.Fatal(err)}
 ledger,err:=n4NoWFPReadRouteSidecar(path,id,keys)
 if err!=nil||ledger.Phase!="active"||len(ledger.Entries)!=3{
  t.Fatalf("missing confirmed route evidence %+v %v",ledger,err)
 }
 if err:=n4NoWFPApplyRoutes(ctx,path,id,keys,b);err==nil{
  t.Fatal("O_EXCL accepted second route owner")
 }
 if err:=n4NoWFPRecoverRoutes(ctx,path,id,keys,b);err!=nil{t.Fatal(err)}
 if b.removes!=3||len(b.present)!=0{t.Fatal("confirmed routes not exactly removed",b)}
 if err:=n4NoWFPRecoverRoutes(ctx,path,id,keys,b);err!=nil{t.Fatal(err)}
 if _,err:=os.Lstat(path);!errors.Is(err,os.ErrNotExist){t.Fatal("child WAL still present",err)}
 // The second row failed BEFORE its OS setter: only the first durable
 // owned row can be removed. The unconfirmed absent intent is retired.
 b=p029NewJournalRouteBackend();b.failBefore=2
 if err:=n4NoWFPApplyRoutes(ctx,path,id,keys,b);err==nil{
  t.Fatal("failure injection lost")
 }
 ledger,err=n4NoWFPReadRouteSidecar(path,id,keys)
 if err!=nil||len(ledger.Entries)!=2||ledger.Entries[0].State!="owned"||
  ledger.Entries[1].State!="intent"{t.Fatalf("partial evidence %+v %v",ledger,err)}
 if err:=n4NoWFPRecoverRoutes(ctx,path,id,keys,b);err!=nil{t.Fatal(err)}
 if b.removes!=1||len(b.present)!=0{t.Fatal("partial recovery touched an unowned key",b)}
 if _,err:=os.Lstat(path);!errors.Is(err,os.ErrNotExist){t.Fatal(err)}
}
func TestPlan029NoWFPV2RouteUnconfirmedAndForeignNeverGuessedOwned(t *testing.T){
 ctx:=context.Background()
 id:=n4TestConcreteNativeIdentity()
 keys:=p029V2RouteKeys()
 path:=filepath.Join(t.TempDir(),"v2.routes")
 b:=p029NewJournalRouteBackend()
 b.failAfter=1
 if err:=n4NoWFPApplyRoutes(ctx,path,id,keys,b);err==nil{
  t.Fatal("failed-after-create injection not reported")
 }
 if err:=n4NoWFPRecoverRoutes(ctx,path,id,keys,b);!errors.Is(err,ErrN4RouteAmbiguous){
  t.Fatalf("present INTENT must not be guessed owned: %v",err)
 }
 if b.removes!=0||!b.present[keys[0]]{t.Fatal("unknown route was deleted")}
 if _,err:=os.Stat(path);err!=nil{t.Fatal("ambiguous receipt lost",err)}
 wrong:=id;wrong.Generation[0]^=1
 if err:=n4NoWFPRecoverRoutes(ctx,path,wrong,keys,b);!errors.Is(err,ErrN4JournalConflict){
  t.Fatalf("foreign generation adopted: %v",err)
 }
 // Separately: when all routes were confirmed, a foreign row preflight
 // must stop BEFORE any otherwise-owned row is removed.
 foreignPath:=filepath.Join(t.TempDir(),"foreign.routes")
 owned:=p029NewJournalRouteBackend()
 if err:=n4NoWFPApplyRoutes(ctx,foreignPath,id,keys,owned);err!=nil{t.Fatal(err)}
 owned.foreign[keys[0]]=true
 if err:=n4NoWFPRecoverRoutes(ctx,foreignPath,id,keys,owned);!errors.Is(err,ErrN4ForeignRoute){
  t.Fatalf("foreign key not refused: %v",err)
 }
 if owned.removes!=0||len(owned.present)!=len(keys){t.Fatal("partial rollback despite foreign key")}
 if _,err:=os.Stat(foreignPath);err!=nil{t.Fatal("foreign ledger lost",err)}
 owned.foreign[keys[0]]=false
 if err:=n4NoWFPRecoverRoutes(ctx,foreignPath,id,keys,owned);err!=nil{t.Fatal(err)}
 if owned.removes!=len(keys){t.Fatal("confirmed foreign-reset routes not all removed")}
}
