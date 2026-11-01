//go:build windows

package windowsclient

import (
 "context"
 "crypto/rand"
 "encoding/hex"
 "net/netip"
 "path/filepath"
 "strconv"
 "time"
 "encoding/json"
 "errors"
 "os"
 "strings"
 "testing"
)

func n4H787FullRouteFixture(t *testing.T,unconfirmed bool)(
 string,N4UnifiedIdentity,*n4FakeGuard,*n4FakeRoute,[]NativeRouteKey,
){
 t.Helper()
 path,id:=n4PreRouteFixture(t,4,"owned")
 j,err:=n4UnifiedRead(path);if err!=nil{t.Fatal(err)}
 id.PnPInstanceSHA256=strings.Repeat("a",64)
 j.Identity=id
 stage,backend,guard,_:=n4TestConcreteRoutes(t)
 stage.Path=path+".routes"
 raw,err:=stage.Snapshot(context.Background(),id);if err!=nil{t.Fatal(err)}
 var baseline n4CompactRouteBaseline
 if err:=json.Unmarshal(raw,&baseline);err!=nil{t.Fatal(err)}
 if unconfirmed{backend.createErrAt=2}
 applied:=stage.Apply(context.Background(),id,raw)
 if unconfirmed && applied==nil{t.Fatal("missing deliberate second route failure")}
 if !unconfirmed && applied!=nil{t.Fatal(applied)}
 state:="owned"
 if unconfirmed{state="intent"}
 j.Records=append(j.Records,n4UnifiedRecord{Name:"routes",State:state,Before:raw})
 if unconfirmed{j.Phase="applying"}else{j.Phase="active"}
 if err:=n4UnifiedWrite(path,j,false);err!=nil{t.Fatal(err)}
 return path,id,guard,backend,baseline.Keys
}
func TestN4OriginalConfirmedFullRouteCrashReplayFakeBackend(t *testing.T){
 t.Run("fully_owned_retires_only_routes_and_keeps_parent_guard",func(t *testing.T){
  path,id,guard,backend,_:=n4H787FullRouteFixture(t,false)
  originalChecks:=0
  verify:=func(context.Context,N4UnifiedIdentity)error{originalChecks++;return nil}
  if err:=n4RetireOriginalConfirmedRouteStage(context.Background(),path,id,guard,backend,verify);err!=nil{
   t.Fatalf("confirmed route replay failed: %v",err)
  }
  if originalChecks<2 || len(backend.existing)!=0 ||
   !guard.active || guard.disarmCount!=0{t.Fatal("route-only recovery lost guard or identity checks")}
  if _,err:=os.Stat(path+".routes");!errors.Is(err,os.ErrNotExist){t.Fatalf("child WAL remained: %v",err)}
  j,err:=n4UnifiedRead(path)
  if err!=nil || j.Phase!="cleaning" || len(j.Records)!=4{
   t.Fatalf("parent pre-route WAL not safely retained: %+v %v",j,err)
  }
 })
 t.Run("ambiguous_intent_never_removes_or_discards_wal",func(t *testing.T){
  path,id,guard,backend,keys:=n4H787FullRouteFixture(t,true)
  backend.existing[keys[1]]=true
  verify:=func(context.Context,N4UnifiedIdentity)error{return nil}
  if err:=n4RetireOriginalConfirmedRouteStage(context.Background(),path,id,guard,backend,verify);
   !errors.Is(err,ErrN4RouteAmbiguous){t.Fatalf("unconfirmed exact route removed: %v",err)}
  if backend.removed!=0 || !guard.active || guard.disarmCount!=0{
   t.Fatal("ambiguous intent mutated routes or disarmed WFP")
  }
  if _,err:=os.Stat(path+".routes");err!=nil{t.Fatal("lost child WAL",err)}
  j,err:=n4UnifiedRead(path)
  if err!=nil || len(j.Records)!=5{t.Fatal("lost parent WAL",err)}
 })
 t.Run("foreign_or_missing_original_identity_is_not_cleanup_permission",func(t *testing.T){
  path,id,guard,backend,_:=n4H787FullRouteFixture(t,false)
  verify:=func(context.Context,N4UnifiedIdentity)error{return ErrN4ForeignRoute}
  if err:=n4RetireOriginalConfirmedRouteStage(context.Background(),path,id,guard,backend,verify);
   !errors.Is(err,ErrN4ForeignRoute){t.Fatalf("foreign original became owned: %v",err)}
  if backend.removed!=0 || !guard.active || guard.disarmCount!=0{t.Fatal("foreign original reached setters")}
  if _,err:=os.Stat(path+".routes");err!=nil{t.Fatal("sidecar disappeared",err)}
 })
}

 // On a real Windows runner, exercise the ORIGINAL Go IP Helper backend with
 // a process-created signed Wintun PnP pin, while touching only a fresh
 // TEST-NET /32 on the independently verified physical underlay. This does
 // not install /1 captures, production WFP, host DNS or a full GameFEC WAL.
func TestN4OriginalConfirmedRouteReplayRealPinnedWintunTestNetOS(t *testing.T){
 if os.Getenv("GITHUB_ACTIONS")!="true" ||
  os.Getenv("WBD_M0_PLAN027_REAL_ROUTE_REPLAY")!="1"{
  t.Skip("NOT_RUN: explicit hosted signed Wintun Win32 CAS only")
 }
 receipt:=map[string]string{
  "schema":"wbd-m0-plan027-real-pinned-route-replay/v1",
  "source_sha":os.Getenv("GITHUB_SHA"),
  "result":"FAIL_UNFINISHED",
  "original_wintun_pnp":"NOT_RUN",
  "intent_present_denied":"NOT_RUN",
  "foreign_pnp_denied":"NOT_RUN",
  "confirmed_route_recovered":"NOT_RUN",
  "wfp":"TEST_ONLY_FAKE_GUARD",
  "captures_1":"NOT_RUN",
  "full_network_wal":"NOT_RUN",
  "game_fec_product":"NOT_RUN",
 }
 defer func(){
  out:=os.Getenv("WBD_M0_PLAN027_ROUTE_REPORT")
  if out==""{t.Error("missing hosted receipt path");return}
  raw,e:=json.MarshalIndent(receipt,"","  ")
  if e!=nil{t.Error(e);return}
  if e=os.MkdirAll(filepath.Dir(out),0700);e!=nil{t.Error(e);return}
  if e=os.WriteFile(out,append(raw,'\n'),0600);e!=nil{t.Error(e)}
 }()
 if receipt["source_sha"]==""{t.Fatal("source absent")}
 physical,err:=strconv.ParseUint(os.Getenv("WBD_M0_ROUTE_TEST_PHYS_IF"),10,32)
 if err!=nil||physical==0{t.Fatalf("not independently pinned physical interface: %v",err)}
 gateway,err:=netip.ParseAddr(os.Getenv("WBD_M0_ROUTE_TEST_PHYS_GW"))
 if err!=nil||!gateway.Is4()||gateway.IsUnspecified(){
  t.Fatalf("not independently pinned physical gateway: %v",err)
 }
 var nonce [8]byte
 if _,err=rand.Read(nonce[:]);err!=nil{t.Fatal(err)}
 tun,err:=OpenTUN("WBD-H790-"+hex.EncodeToString(nonce[:]))
 if err!=nil{t.Fatalf("real signed Wintun is required: %v",err)}
 defer func(){if e:=tun.Close();e!=nil{t.Errorf("Wintun close: %v",e)}}()
 ctx,cancel:=context.WithTimeout(context.Background(),55*time.Second)
 defer cancel()
 native,err:=tun.NativeIdentity(ctx)
 if err!=nil||!native.CreatedByProcess||native.Index==0||
  native.LUID==0||native.Index==uint32(physical){
  t.Fatalf("real original Wintun identity absent or physical conflict: %+v %v",native,err)
 }
 guid,err:=n4NativeInterfaceGUID(native.Index)
 if err!=nil{t.Fatal(err)}
 var install,generation [16]byte
 if _,err=rand.Read(install[:]);err!=nil{t.Fatal(err)}
 if _,err=rand.Read(generation[:]);err!=nil{t.Fatal(err)}
 id:=N4UnifiedIdentity{
  Installation:install,Generation:generation,
  WintunGUID:guid.String(),WintunLUID:native.LUID,
  WintunIndex:native.Index,AdapterAlias:tun.Name(),
 }
 original,err:=n4ProbeOriginalWintunPnP(ctx,id)
 if err!=nil{t.Fatalf("original created PnP not pinned: %v",err)}
 id.PnPInstanceSHA256=original.InstanceSHA256
 if !n4ValidPinnedPnPHash(id.PnPInstanceSHA256){
  t.Fatal("original live PnP hash absent")
 }
 verify:=func(ctx context.Context,current N4UnifiedIdentity)error{
  if e:=n4OriginalWintunPersistedExact(ctx,current);e!=nil{return e}
  _,e:=n4ProbePinnedOriginalWintunPnP(ctx,current)
  return e
 }
 if err:=verify(ctx,id);err!=nil{t.Fatalf("actual original pinned OS PnP mismatch: %v",err)}
 receipt["original_wintun_pnp"]="PASS_EXACT_LIVE_GUID_LUID_INDEX_PNP"
 route:=NativeRouteKey{
  Prefix:netip.MustParsePrefix("203.0.113.251/32"),
  Interface:uint32(physical),NextHop:gateway,Metric:5,
 }
 actual:=N4WindowsRouteBackend{}
 if present,_,e:=actual.Lookup(ctx,route);e!=nil||present{
  t.Fatalf("TEST-NET /32 not empty; refuse foreign route: %v %v",present,e)
 }
 if err:=actual.CreateIfAbsent(ctx,route);err!=nil{
  t.Fatalf("real TEST-NET underlay /32 Win32 CreateIfAbsent: %v",err)
 }
 routeOwned:=true
 defer func(){
  if !routeOwned{return}
  cleanup,done:=context.WithTimeout(context.Background(),15*time.Second)
  defer done()
  if e:=actual.RemoveOwned(cleanup,route);e!=nil{
   t.Errorf("cleanup exact TEST-NET /32 owned route: %v",e)
  }
 }()
 guard:=&n4FakeGuard{durable:true,active:true}
 guarded:=n4OriginalRouteCleanupBackend{
  ID:id,Guard:guard,Route:actual,VerifyOriginal:verify,
 }
 path:=filepath.Join(t.TempDir(),"single-testnet-underlay-route-wal.json")
 record:=n4Journal{Schema:n4JournalSchema,Phase:"cleaning",GuardArmed:true,
  Entries:[]n4Entry{{Key:route,State:"intent"}},
 }
 if err:=n4WriteJournal(path,record);err!=nil{t.Fatal(err)}
 replay:=&N4OwnedRoutes{
  Path:path,Route:guarded,Guard:n4SharedPersistentGuard{parent:guard},
 }
 if err:=replay.Recover(ctx);!errors.Is(err,ErrN4RouteAmbiguous){
  t.Fatalf("real exact route with unconfirmed intent was deleted: %v",err)
 }
 if present,exact,e:=actual.Lookup(ctx,route);e!=nil||!present||!exact{
  t.Fatalf("unconfirmed intent changed physical TEST-NET route: %v %v %v",present,exact,e)
 }
 if _,err:=os.Stat(path);err!=nil{t.Fatalf("unconfirmed route WAL lost: %v",err)}
 receipt["intent_present_denied"]="PASS_WAL_RETAINED_ROUTE_UNCHANGED"
 foreign:=id
 foreign.PnPInstanceSHA256=strings.Repeat("0",64)
 if foreign.PnPInstanceSHA256==id.PnPInstanceSHA256{
  foreign.PnPInstanceSHA256=strings.Repeat("f",64)
 }
 forged:=guarded
 forged.ID=foreign
 if err:=forged.RemoveOwned(ctx,route);err==nil{
  t.Fatal("foreign original PnP acquired route cleanup authority")
 }
 if present,exact,e:=actual.Lookup(ctx,route);e!=nil||!present||!exact{
  t.Fatalf("foreign PnP mutated real route: %v %v %v",present,exact,e)
 }
 receipt["foreign_pnp_denied"]="PASS_REAL_OS_ROUTE_UNCHANGED"
 // The test alone now injects a confirmed original-owned copy receipt,
 // exactly the state the old two-WAL product writes AFTER Win32 Create.
 // No production intent is ever silently upgraded this way.
 record.Entries[0].State="owned"
 if err:=n4WriteJournal(path,record);err!=nil{t.Fatal(err)}
 if err:=replay.Recover(ctx);err!=nil{
  t.Fatalf("original PnP checked real OS Win32 confirmed route replay: %v",err)
 }
 routeOwned=false
 if present,_,e:=actual.Lookup(ctx,route);e!=nil||present{
  t.Fatalf("real native TEST-NET /32 route survived recovery: %v %v",present,e)
 }
 if _,err:=os.Stat(path);!errors.Is(err,os.ErrNotExist){
  t.Fatalf("confirmed exact-owned route WAL not retired: %v",err)
 }
 if !guard.active||guard.disarmCount!=0{
  t.Fatal("route-only cleanup disarmed parent WFP before other WAL stages")
 }
 if err:=verify(ctx,id);err!=nil{t.Fatalf("original Wintun lost across route recovery: %v",err)}
 receipt["confirmed_route_recovered"]="PASS_REAL_WIN32_IP_HELPER_CAS_AND_OS_ABSENT"
 receipt["result"]="PASS_SCOPED_REAL_ORIGINAL_PNP_CONFIRMED_TESTNET_ROUTE_ONLY"
 t.Log("H790_REAL_PINNED_WINTUN_WIN32_CONFIRMED_ROUTE_RECOVER_PASS_NOT_FULL_WAL_NOT_FEC")
}
