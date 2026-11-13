//go:build windows
package windowsclient

// PLAN029 H1697: one real signed Wintun no-old-WFP four-stage OS Apply/Stop
// capability scene. Nothing here proves Rust ingress, physical Direct or
// product Ready. This file is copied into the pinned original Go on one Action.
import (
 "context"
 "crypto/rand"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "net/netip"
 "os"
 "path/filepath"
 "testing"
 "time"
)

func TestPlan029SignedNoWFPFourWin32StagesRealApplyAndStop(t *testing.T){
 if os.Getenv("WBD_PLAN029_REAL_OS_V2_GATE")!="1" ||
  os.Getenv("GITHUB_ACTIONS")!="true"{
  t.Skip("requires isolated Windows2025 signed Wintun and actual owned Win32 OS")
 }
 receipt:=map[string]any{
  "schema_version":1,"source_sha":os.Getenv("GITHUB_SHA"),
  "result":"FAIL_UNFINISHED","scope":"REAL_SIGNED_NO_OLD_WFP_FOUR_OS_STAGES_ONLY",
  "old_wfp_guard":"NOT_CREATED","routed_split":"NOT_RUN",
  "rust_direct_tcp":"NOT_RUN","rust_direct_udp":"NOT_RUN",
  "real_dns53_dispatcher":"NOT_RUN","gui_product_ready":"NOT_RUN",
 }
 defer func(){
  path:=os.Getenv("WBD_PLAN029_REAL_OS_V2_RECEIPT")
  if path==""{t.Error("missing receipt path");return}
  if e:=os.MkdirAll(filepath.Dir(path),0700);e!=nil{t.Error(e);return}
  data,e:=json.MarshalIndent(receipt,"","  ")
  if e!=nil{t.Error(e);return}
  if e=os.WriteFile(path,append(data,'\n'),0600);e!=nil{t.Error(e)}
 }()
 if receipt["source_sha"]==""{t.Fatal("missing exact source")}
 ctx,cancel:=context.WithTimeout(context.Background(),48*time.Second)
 defer cancel()
 var nonce [8]byte
 if _,e:=rand.Read(nonce[:]);e!=nil{t.Fatal(e)}
 tun,e:=OpenTUN("WBD-P029-OS-"+hex.EncodeToString(nonce[:]))
 if e!=nil{receipt["result"]="FAIL_REAL_SIGNED_WINTUN_OPEN";t.Fatal(e)}
 t.Cleanup(func(){if e:=tun.Close();e!=nil{t.Errorf("Wintun owned Close: %v",e)}})
 native,e:=tun.NativeIdentity(ctx)
 if e!=nil||!native.CreatedByProcess||native.Index==0||native.LUID==0{
  receipt["result"]="FAIL_CURRENT_SIGNED_TUN_IDENTITY"
  t.Fatalf("not original created signed Wintun: %+v %v",native,e)
 }
 receipt["wintun_ifindex"]=native.Index
 var installation,generation [16]byte
 if _,e=rand.Read(installation[:]);e!=nil{t.Fatal(e)}
 if _,e=rand.Read(generation[:]);e!=nil{t.Fatal(e)}
 id,e:=N4OriginalCurrentPinnedWintunIdentity(ctx,tun,installation,generation)
 if e!=nil{receipt["result"]="FAIL_ORIGINAL_PINNED_PNP";t.Fatal(e)}
 // Discover the actual selected physical route WITHOUT querying Npcap,
 // external DNS or an internet host. This runs before any /1 mutation,
 // excludes the Wintun and never relies on a fixed test ifindex/gateway.
 peer:=netip.MustParseAddr("203.0.113.250")
 adapters,e:=nativeIPv4Adapters()
 if e!=nil{receipt["result"]="FAIL_PHYSICAL_ADAPTER_SNAPSHOT";t.Fatal(e)}
 candidates,e:=nativeIPv4Routes(adapters,peer,native.Index)
 if e!=nil{receipt["result"]="FAIL_PHYSICAL_ROUTE_SNAPSHOT";t.Fatal(e)}
 selected,e:=selectPhysicalRoute(candidates)
 if e!=nil{receipt["result"]="FAIL_SELECTED_PHYSICAL_ROUTE";t.Fatal(e)}
 nextHop:=selected.nextHop
 if !nextHop.IsValid()||nextHop.IsUnspecified(){nextHop=peer}
 if selected.interfaceIndex==0||selected.interfaceIndex==native.Index ||
  !selected.source4.Is4()||!nextHop.Is4(){
  receipt["result"]="FAIL_FOREIGN_PHYSICAL_SELECTION"
  t.Fatal("no separate bounded physical IPv4 route")
 }
 receipt["selected_physical_index"]=selected.interfaceIndex
 receipt["selected_physical_source"]=selected.source4.String()
 receipt["selected_physical_next_hop"]=nextHop.String()
 statePath:=filepath.Join(t.TempDir(),"owned-state.json")
 plan,e:=BuildCompactNetworkPlan(Config{
  AdapterAlias:tun.Name(),
  Lease4:netip.MustParsePrefix("198.18.99.77/32"),
  Server4:peer,
  Physical:PhysicalPath{InterfaceIndex:selected.interfaceIndex,NextHop4:nextHop},
  DNSServers4:[]netip.Addr{netip.MustParseAddr("1.1.1.1")},
  StatePath:statePath,TunnelMTU:1280,
 })
 if e!=nil{receipt["result"]="FAIL_COMPACT_NETWORK_PLAN";t.Fatal(e)}
 keys,e:=N4BuildCompactNativeRouteKeys(plan,native.Index)
 if e!=nil||len(keys)<3||len(keys)>9{
  receipt["result"]="FAIL_BOUNDED_ROUTE_INTENT"
  t.Fatalf("invalid route batch n=%d e=%v",len(keys),e)
 }
 receipt["owned_compact_route_keys"]=len(keys)
 txn,e:=n4AssembleWindowsNoWFPNativeTxn(ctx,tun,plan,id)
 if e!=nil{receipt["result"]="FAIL_FOUR_STAGE_ASSEMBLY";t.Fatal(e)}
 if !txn.noLegacyWFP||len(txn.stages())!=4||txn.Stages[4]!=nil{
  receipt["result"]="FAIL_OLD_WFP_GUARD_IN_V2"
  t.Fatal("v2 stage set included retired WFP guard")
 }
 // This local test deliberately exercises four real concrete Win32 writers.
 // Public N4PrepareRealWindowsProduct continues to decline product Ready
 // unless authenticated Rust+true DNS/Direct and OS receipts are complete.
 if !txn.assemblyOnly{t.Fatal("test unexpectedly inherited product qualification")}
 txn.assemblyOnly=false
 // Register finally before Apply. Source-locked generation+machine gate
 // remains held by transaction throughout every stage/rollback operation.
 // The parent and the child sidecar must be retired before closing Wintun.
 defer func(){
  cleanCtx,done:=context.WithTimeout(context.Background(),35*time.Second)
  defer done()
  err:=txn.Recover(cleanCtx)
  if err!=nil{
   receipt["cleanup"]="FAIL_RETAIN_OWNED_WAL"
   receipt["cleanup_error"]=err.Error()
   t.Errorf("exact no-WFP owned WAL cleanup failed: %v",err)
   return
  }
  if err:=txn.VerifyLiveOSDisconnected(cleanCtx);err!=nil{
   receipt["cleanup"]="FAIL_OS_DISCONNECTED_READBACK"
   receipt["cleanup_error"]=err.Error()
   t.Errorf("no-WFP OS absent readback failed: %v",err)
   return
  }
  receipt["cleanup"]="PASS_EXACT_OWNED_FOUR_STAGE_STOP_NO_OLD_WFP"
 }()
 receipt["result"]="FAIL_AT_LIVE_OS_APPLY"
 if err:=txn.Apply(ctx);err!=nil{
  receipt["apply_error"]=err.Error()
  t.Fatalf("four real Win32 stage Apply first error: %v",err)
 }
 receipt["apply"]="RETURNED_OK"
 status,e:=txn.VerifyLiveOSApplied(ctx)
 if e!=nil||!status.AllNativeOSApplied||status.GuardOwned||
  !status.LeaseOwned||!status.MTUOwned||!status.DNSOwned||
  !status.RoutesOwned||status.Schema!=N4NativeLiveOSSchemaNoWFP {
  receipt["result"]="FAIL_LIVE_V2_OS_APPLIED_READBACK"
  t.Fatalf("real Win32 live four-stage readback %+v error=%v",status,e)
 }
 receipt["applied"]="PASS_INDEPENDENT_LIVE_V2_FOUR_STAGE_READBACK"
 // H1716: THIS is the exact API called before public Windows READY and
 // at its existing low-frequency health timer. Old v1 hard-coded five
 // stages, so the real v2 OS rows could be fully Applied while this probe
 // returned inspected=0/ErrN4NativeGuard. Read via the same live owner,
 // original machine exclusion and actual no-old-WFP Win32 MTU CAS.
 actualMTU,mtuErr:=txn.LiveConfiguredMTU(ctx)
 if mtuErr!=nil||actualMTU!=plan.TunnelMTU{
  receipt["result"]="FAIL_V2_RUNTIME_MTU_LIVE_CAS"
  receipt["mtu_runtime_error"]=fmt.Sprint(mtuErr)
  t.Fatalf("PLAN029 v2 live native MTU readback expected=%d actual=%d error=%v",
   plan.TunnelMTU,actualMTU,mtuErr)
 }
 receipt["runtime_mtu"]="PASS_CURRENT_GENERATION_V2_LIVE_MTU_CAS"
 receipt["runtime_mtu_value"]=actualMTU
 t.Logf("PLAN029_H1716_RUNTIME_V2_MTU_TRUE_OS_READBACK_PASS source=%s mtu=%d no_old_wfp=true",
  os.Getenv("GITHUB_SHA"),actualMTU)
 // Recover once now rather than letting test cleanup be the only Stop.
 receipt["result"]="FAIL_AT_LIVE_OS_RECOVER"
 if err:=txn.Recover(ctx);err!=nil{
  receipt["stop_error"]=err.Error()
  t.Fatalf("four real Win32 exact-owned Stop failed: %v",err)
 }
 if err:=txn.VerifyLiveOSDisconnected(ctx);err!=nil{
  receipt["result"]="FAIL_OS_STOP_ABSENCE_READBACK"
  t.Fatalf("four-stage OS no-WFP Stop readback: %v",err)
 }
 if _,e:=os.Lstat(txn.Path);!errors.Is(e,os.ErrNotExist){
  receipt["result"]="FAIL_PARENT_WAL_AFTER_STOP"
  t.Fatalf("no-WFP parent WAL survived: %v",e)
 }
 if _,e:=os.Lstat(txn.Path+".routes");!errors.Is(e,os.ErrNotExist){
  receipt["result"]="FAIL_CHILD_ROUTE_RECEIPT_AFTER_STOP"
  t.Fatalf("no-WFP route child WAL survived: %v",e)
 }
 receipt["result"]="PASS_SCOPED_SIGNED_WINTUN_REAL_FOUR_NO_WFP_WIN32_APPLY_READBACK_STOP"
 receipt["cleanup"]="PASS_EXACT_OWNED_FOUR_STAGE_STOP_NO_OLD_WFP"
 t.Logf("PLAN029_H1697_REAL_WIN32_FOUR_STAGE_OS_APPLIED_STOP_PASS source=%s route_keys=%d guard=false",os.Getenv("GITHUB_SHA"),len(keys))
}
