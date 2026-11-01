//go:build windows

package windowsclient

import (
 "errors"
 "net/netip"
 "slices"
 "strings"
 "testing"
)

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
