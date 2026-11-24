//go:build windows
package windowsclient

import(
 "context"
 "crypto/rand"
 "encoding/hex"
 "encoding/json"
 "errors"
 "net/netip"
 "os"
 "os/exec"
 "path/filepath"
 "testing"
 "time"
)

// Real signed Wintun child, same production v2 writers and WAL format.
// Use one isolated TEST-NET /32 route, never a runner default route.
func TestM0CrashV2NativeRecovery(t *testing.T){
 if os.Getenv("WBD_M0_CRASH_CHILD")=="1"{
  ctx,cancel:=context.WithTimeout(context.Background(),40*time.Second);defer cancel()
  path:=os.Getenv("WBD_M0_CRASH_PATH")
  tun,err:=OpenTUN(os.Getenv("WBD_M0_CRASH_ALIAS"));if err!=nil{t.Fatal(err)}
  actual,err:=tun.NativeIdentity(ctx);if err!=nil||!actual.CreatedByProcess{t.Fatal(actual,err)}
  guid,err:=n4NativeInterfaceGUID(actual.Index);if err!=nil{t.Fatal(err)}
  id:=N4UnifiedIdentity{WintunGUID:guid.String(),WintunLUID:actual.LUID,WintunIndex:actual.Index,AdapterAlias:tun.Name()}
  if _,err=rand.Read(id.Installation[:]);err!=nil{t.Fatal(err)}
  if _,err=rand.Read(id.Generation[:]);err!=nil{t.Fatal(err)}
  pin,err:=n4ProbeOriginalWintunPnP(ctx,id);if err!=nil{t.Fatal(err)};id.PnPInstanceSHA256=pin.InstanceSHA256
  owner:=N4WindowsCreatedWintunReservation{Tunnel:tun,Installation:id.Installation,Generation:id.Generation}
  release,err:=(N4WindowsMachineGate{}).Acquire(ctx);if err!=nil{t.Fatal(err)}
  wal:=path+".n4-owned-wal"
  j:=n4UnifiedJournal{Schema:n4UnifiedSchemaNoWFP,Identity:id,Phase:"applying"}
  if err=n4UnifiedWrite(wal,j,true);err!=nil{t.Fatal(err)}
  stages:=[]N4UnifiedStage{
   n4WindowsNoWFPLeaseStage{Lease:N4NativeLeaseIntent{InterfaceIndex:actual.Index,Prefix:netip.MustParsePrefix("198.18.18.77/32")},Owner:owner,WALPath:wal},
   n4WindowsNoWFPMTUStage{Target:1249,Owner:owner,WALPath:wal},
   n4WindowsNoWFPDNSStage{Servers:[]netip.Addr{netip.MustParseAddr("1.1.1.1")},Owner:owner,WALPath:wal},
  }
  for _,s:=range stages{
   before,err:=s.Snapshot(ctx,id);if err!=nil{t.Fatal(s.Name(),err)}
   j.Records=append(j.Records,n4UnifiedRecord{Name:s.Name(),State:"intent",Before:before})
   if err=n4UnifiedWrite(wal,j,false);err!=nil{t.Fatal(err)}
   if err=s.Apply(ctx,id,before);err!=nil{t.Fatal(s.Name(),err)}
   j.Records[len(j.Records)-1].State="owned"
   if err=n4UnifiedWrite(wal,j,false);err!=nil{t.Fatal(err)}
  }
  keys:=[]NativeRouteKey{{Prefix:netip.MustParsePrefix("198.18.18.78/32"),Interface:actual.Index,NextHop:netip.IPv4Unspecified(),Metric:5}}
  raw,err:=json.Marshal(n4CompactRouteBaseline{Keys:keys});if err!=nil{t.Fatal(err)}
  j.Records=append(j.Records,n4UnifiedRecord{Name:"routes",State:"intent",Before:raw})
  if err=n4UnifiedWrite(wal,j,false);err!=nil{t.Fatal(err)}
  if err=n4NoWFPApplyRoutes(ctx,wal+".routes",id,keys,N4WindowsRouteBackend{});err!=nil{t.Fatal(err)}
  j.Records[3].State="owned";j.Phase="active"
  if err=n4UnifiedWrite(wal,j,false);err!=nil{t.Fatal(err)}
  release()
  if err=os.WriteFile(path+".ready",[]byte("ready"),0600);err!=nil{t.Fatal(err)}
  for{time.Sleep(time.Second)}
 }
 if os.Getenv("WBD_M0_CRASH_REAL")!="1"{t.Skip("requires disposable Windows runner and signed Wintun")}
 var salt [8]byte;if _,err:=rand.Read(salt[:]);err!=nil{t.Fatal(err)}
 path:=filepath.Join(t.TempDir(),"network-state.json")
 child:=exec.Command(os.Args[0],"-test.run=^TestM0CrashV2NativeRecovery$","-test.v","-test.timeout=3m")
 child.Env=append(os.Environ(),"WBD_M0_CRASH_CHILD=1","WBD_M0_CRASH_PATH="+path,"WBD_M0_CRASH_ALIAS=WBD-CRASH-"+hex.EncodeToString(salt[:]))
 child.Stdout=os.Stdout;child.Stderr=os.Stderr
 if err:=child.Start();err!=nil{t.Fatal(err)}
 stopped:=false;defer func(){if !stopped{_ =child.Process.Kill();_ =child.Wait()}}()
 until:=time.Now().Add(40*time.Second)
 for{if _,err:=os.Stat(path+".ready");err==nil{break};if time.Now().After(until){t.Fatal("real child not ready")};time.Sleep(100*time.Millisecond)}
 j,err:=n4UnifiedRead(path+".n4-owned-wal");if err!=nil||len(j.Records)!=4||j.Phase!="active"{t.Fatal("real v2 four stages not active",err)}
 if err=child.Process.Kill();err!=nil{t.Fatal(err)}
 if err=child.Wait();err==nil{t.Fatal("child did not crash")};stopped=true
 ctx,cancel:=context.WithTimeout(context.Background(),30*time.Second);defer cancel()
 if err=N4NativeRecoverState(ctx,path);err!=nil{t.Fatal("new process could not recover actual v2 WAL",err)}
 for _,s:=range []string{".n4-owned-wal",".n4-owned-wal.routes"}{if _,err=os.Stat(path+s);!errors.Is(err,os.ErrNotExist){t.Fatal("residual",s,err)}}
 if err=N4NativeRecoverState(ctx,path);err!=nil{t.Fatal("second recovery",err)}
 t.Log("M0_REAL_V2_WINTUN_CHILD_CRASH_NATIVE_RECOVERY_PASS")
}
