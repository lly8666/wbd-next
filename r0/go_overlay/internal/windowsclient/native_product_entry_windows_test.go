//go:build windows

package windowsclient

import (
    "context"
    "errors"
    "os"
    "path/filepath"
    "testing"
    "net/netip"
    "slices"
    "strings"
)
func TestPLAN010OriginalNativeRecoveryNoShellOrLegacyFallback(t *testing.T) {
    dir:=t.TempDir()
    path:=filepath.Join(dir,"network-state.json")
    if err:=N4NativeRecoverState(context.Background(),path);err!=nil{
        t.Fatalf("absent native and old state should be a verified no-op: %v",err)
    }
    // Partial route receipt without a primary WAL is NOT "nothing to do".
    orphan:=path+".n4-owned-wal.routes"
    if err:=os.WriteFile(orphan,[]byte("owned-intent"),0600);err!=nil{t.Fatal(err)}
    if err:=N4NativeRecoverState(context.Background(),path);!errors.Is(err,ErrN4JournalConflict){
        t.Fatalf("orphaned route journal falsely cleared: %v",err)
    }
    if _,err:=os.Stat(orphan);err!=nil{t.Fatal("orphan sidecar removed",err)}
    if err:=os.Remove(orphan);err!=nil{t.Fatal(err)}
    old:=[]byte(`{"schema":1,"foreign_or_legacy":true}`)
    if err:=os.WriteFile(path,old,0600);err!=nil{t.Fatal(err)}
    err:=N4NativeRecoverState(context.Background(),path)
    if !errors.Is(err,ErrN4JournalConflict){t.Fatalf("old shell journal used as native: %v",err)}
    got,err:=os.ReadFile(path);if err!=nil||string(got)!=string(old){t.Fatal("legacy state lost",err)}
    if err:=os.Remove(path);err!=nil{t.Fatal(err)}
    native:=path+".n4-owned-wal"
    malformed:=[]byte(`{"schema":777,"identity":"pretend-owned"}`)
    if err:=os.WriteFile(native,malformed,0600);err!=nil{t.Fatal(err)}
    if err:=N4NativeRecoverState(context.Background(),path);err==nil{
        t.Fatal("unowned native WAL recovered or erased")
    }
    got,err=os.ReadFile(native);if err!=nil||string(got)!=string(malformed){t.Fatal("unowned WAL lost",err)}
    ctx,cancel:=context.WithCancel(context.Background());cancel()
    if err:=N4NativeRecoverState(ctx,path);!errors.Is(err,context.Canceled){t.Fatal(err)}
    if err:=N4NativeNetworkReady(ctx);!errors.Is(err,context.Canceled){t.Fatal(err)}
    if err:=N4NativeNetworkReady(context.Background());!errors.Is(err,ErrN4NativeGuard){
        t.Fatalf("unverified native WFP product unexpectedly enabled: %v",err)
    }
    if err:=N4NativeRecoverState(context.Background(),"relative.json");!errors.Is(err,ErrNetworkPlan){t.Fatal(err)}
}


func TestN4WindowsPersistedFullRouteReceiptsRejectMismatchWithoutOSWrites(t *testing.T){
 path,id:=n4PreRouteFixture(t,4,"owned")
 j,err:=n4UnifiedRead(path);if err!=nil{t.Fatal(err)}
 id.PnPInstanceSHA256=strings.Repeat("a",64)
 j.Identity=id
 plan,err:=BuildCompactNetworkPlan(Config{
  AdapterAlias:"WBD",TunnelMTU:1400,
  Lease4:netip.MustParsePrefix("10.234.12.34/32"),
  Server4:netip.MustParseAddr("198.51.100.10"),
  Physical:PhysicalPath{InterfaceIndex:12,NextHop4:netip.MustParseAddr("192.0.2.1")},
  DNSServers4:[]netip.Addr{netip.MustParseAddr("1.1.1.1"),netip.MustParseAddr("8.8.8.8")},
  StatePath:path,
 });if err!=nil{t.Fatal(err)}
 keys,err:=N4BuildCompactNativeRouteKeys(plan,id.WintunIndex);if err!=nil{t.Fatal(err)}
 j.Records=append(j.Records,n4UnifiedRecord{Name:"routes",State:"owned",
  Before:mustN4Raw(t,n4CompactRouteBaseline{Keys:keys})})
 j.Phase="active"
 side:=n4Journal{Schema:n4JournalSchema,Phase:"active",GuardArmed:true}
 for _,key:=range keys{side.Entries=append(side.Entries,n4Entry{Key:key,State:"owned"})}
 if got,err:=n4ValidatePersistedFullRouteReceipts(j,id,&side);err!=nil ||
  !slices.Equal(got,keys){t.Fatalf("exact parent-child WAL refused: %v",err)}
 mismatch:=side
 mismatch.Entries=append([]n4Entry(nil),side.Entries...)
 mismatch.Entries[1].Key.Interface++
 if _,err:=n4ValidatePersistedFullRouteReceipts(j,id,&mismatch);
  !errors.Is(err,ErrN4JournalConflict){t.Fatalf("foreign route sidecar authorized: %v",err)}
 unconfirmed:=side
 unconfirmed.Entries=append([]n4Entry(nil),side.Entries...)
 unconfirmed.Entries[len(unconfirmed.Entries)-1].State="intent"
 if _,err:=n4ValidatePersistedFullRouteReceipts(j,id,&unconfirmed);
  !errors.Is(err,ErrN4JournalConflict){t.Fatalf("unconfirmed route treated owned: %v",err)}
 wrong:=id;wrong.Generation[0]^=1
 if _,err:=n4ValidatePersistedFullRouteReceipts(j,wrong,&side);
  !errors.Is(err,ErrN4JournalConflict){t.Fatalf("foreign generation adopted: %v",err)}
 bad:=j
 bad.Records=append([]n4UnifiedRecord(nil),j.Records...)
 corrupted:=append([]NativeRouteKey(nil),keys...)
 corrupted[len(corrupted)-1].Prefix=netip.MustParsePrefix("203.0.113.9/32")
 bad.Records[4].Before=mustN4Raw(t,n4CompactRouteBaseline{Keys:corrupted})
 if _,err:=n4ValidatePersistedFullRouteReceipts(bad,id,&side);
  !errors.Is(err,ErrN4JournalConflict){t.Fatalf("unconfigured DNS/32 route authorized: %v",err)}
 // This fixture may not call N4WindowsRouteBackend, WFP Arm/Disarm or
 // any network OS setter. It only rejects malicious/stale WAL relationships.
}
