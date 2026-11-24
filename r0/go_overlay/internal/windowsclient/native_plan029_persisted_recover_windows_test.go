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

 "golang.org/x/sys/windows"
)

var m0CrashDNSFailure=errors.New("test DNS prewrite interruption")
type m0CrashBeforeDNS struct{N4UnifiedStage}
func(m0CrashBeforeDNS) Apply(context.Context,N4UnifiedIdentity,json.RawMessage)error{return m0CrashDNSFailure}

// Real signed Wintun child with the existing compact capture and escape routes.
// Run only on disposable Windows Actions runners.
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
  // A stale GUID with a real currently occupied interface index/LUID is
  // absent for v2 recovery; it must not adopt the other adapter.
  stale:=id
  staleGUID,err:=windows.GUIDFromString("{0f853251-6cf5-49a7-9884-7f93d0782413}")
  if err!=nil{t.Fatal(err)}
  stale.WintunGUID=staleGUID.String()
  state,err:=n4InspectOriginalWintunForRecovery(ctx,stale)
  if err!=nil||state!=N4UnifiedAbsent{t.Fatal("stale GUID with reused index",state,err)}
  owner:=N4WindowsCreatedWintunReservation{Tunnel:tun,Installation:id.Installation,Generation:id.Generation}
  // Reuse H1697's real original compact plan and stage assembler; a
  // one-route fake plan is not accepted by production route grammar.
  peer:=netip.MustParseAddr("203.0.113.250")
  adapters,err:=nativeIPv4Adapters();if err!=nil{t.Fatal(err)}
  candidates,err:=nativeIPv4Routes(adapters,peer,actual.Index);if err!=nil{t.Fatal(err)}
  selected,err:=selectPhysicalRoute(candidates);if err!=nil{t.Fatal(err)}
  hop:=selected.nextHop;if !hop.IsValid()||hop.IsUnspecified(){hop=peer}
  plan,err:=BuildCompactNetworkPlan(Config{AdapterAlias:tun.Name(),Lease4:netip.MustParsePrefix("198.18.18.77/32"),Server4:peer,Physical:PhysicalPath{InterfaceIndex:selected.interfaceIndex,NextHop4:hop},DNSServers4:[]netip.Addr{netip.MustParseAddr("1.1.1.1")},StatePath:path,TunnelMTU:1249})
  if err!=nil{t.Fatal(err)}
  txn,err:=n4AssembleWindowsNoWFPNativeTxn(ctx,tun,plan,id);if err!=nil{t.Fatal(err)}
  txn.assemblyOnly=false
  _=owner // same original reservation in assembled txn
  scene:=os.Getenv("WBD_M0_CRASH_SCENE")
  if scene=="partial"{
   // Same real lease/MTU prefix, failed DNS prewrite, no routes created.
   txn.Stages[2]=m0CrashBeforeDNS{txn.Stages[2]}
   if err=txn.Apply(ctx);!errors.Is(err,m0CrashDNSFailure){t.Fatal("partial",err)}
  }else{
   if err=txn.Apply(ctx);err!=nil{t.Fatal("actual full compact Apply",err)}
   if scene=="gone"{
    // Emulate OS removal before WAL retirement, leaving the physical escape receipt.
    if err=tun.Close();err!=nil{t.Fatal("remove original Wintun",err)}
   }
   if scene=="normal"{
    if err=txn.Recover(ctx);err!=nil{t.Fatal(err)}
    if err=txn.VerifyLiveOSDisconnected(ctx);err!=nil{t.Fatal(err)}
    if err=tun.Close();err!=nil{t.Fatal(err)}
    return
   }
  }
  if err=os.WriteFile(path+".ready",[]byte("ready"),0600);err!=nil{t.Fatal(err)}
  for{time.Sleep(time.Second)}
 }
 if os.Getenv("WBD_M0_CRASH_REAL")!="1"||os.Getenv("GITHUB_ACTIONS")!="true"{t.Skip("requires disposable Windows runner and signed Wintun")}
 for _,scene:=range []string{"normal","partial","full","gone"}{t.Run(scene,func(t *testing.T){m0CrashScenario(t,scene)})}
}
func m0CrashScenario(t *testing.T,scene string){
 var salt [8]byte;if _,err:=rand.Read(salt[:]);err!=nil{t.Fatal(err)}
 path:=filepath.Join(t.TempDir(),"network-state.json")
 child:=exec.Command(os.Args[0],"-test.run=^TestM0CrashV2NativeRecovery$","-test.v","-test.timeout=3m")
 child.Env=append(os.Environ(),"WBD_M0_CRASH_CHILD=1","WBD_M0_CRASH_SCENE="+scene,"WBD_M0_CRASH_PATH="+path,"WBD_M0_CRASH_ALIAS=WBD-CRASH-"+hex.EncodeToString(salt[:]))
 child.Stdout=os.Stdout;child.Stderr=os.Stderr
 if err:=child.Start();err!=nil{t.Fatal(err)}
 if scene=="normal"{if err:=child.Wait();err!=nil{t.Fatal(err)};if _,err:=os.Stat(path+".n4-owned-wal");!errors.Is(err,os.ErrNotExist){t.Fatal("normal Stop residue",err)};t.Log("M0_REAL_V2_NORMAL_STOP_PASS");return}
 stopped:=false;defer func(){if !stopped{_ =child.Process.Kill();_ =child.Wait()}}()
 until:=time.Now().Add(40*time.Second)
 for{if _,err:=os.Stat(path+".ready");err==nil{break};if time.Now().After(until){t.Fatal("real child not ready")};time.Sleep(100*time.Millisecond)}
 j,err:=n4UnifiedRead(path+".n4-owned-wal");if err!=nil{t.Fatal(err)}
 if (scene=="full"||scene=="gone")&&(len(j.Records)!=4||j.Phase!="active"){t.Fatal("real four stages not active")}
 if scene=="partial"&&(len(j.Records)!=3||j.Records[2].State!="intent"){t.Fatal("real partial state missing")}
 if err=child.Process.Kill();err!=nil{t.Fatal(err)}
 if err=child.Wait();err==nil{t.Fatal("child did not crash")};stopped=true
 ctx,cancel:=context.WithTimeout(context.Background(),30*time.Second);defer cancel()
 if err=N4NativeRecoverState(ctx,path);err!=nil{t.Fatal("new process could not recover actual v2 WAL",err)}
 for _,s:=range []string{".n4-owned-wal",".n4-owned-wal.routes"}{if _,err=os.Stat(path+s);!errors.Is(err,os.ErrNotExist){t.Fatal("residual",s,err)}}
 if err=N4NativeRecoverState(ctx,path);err!=nil{t.Fatal("second recovery",err)}
 t.Log("M0_REAL_V2_WINTUN_CHILD_CRASH_NATIVE_RECOVERY_PASS scene="+scene)
}
