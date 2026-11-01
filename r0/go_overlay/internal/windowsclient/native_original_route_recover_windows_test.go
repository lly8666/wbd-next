//go:build windows

package windowsclient

import (
 "context"
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
