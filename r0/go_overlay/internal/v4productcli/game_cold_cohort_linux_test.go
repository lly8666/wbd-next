//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_product

package v4productcli

import (
    "testing"
    "github.com/lly8666/wobuzhidao/internal/realityfront"
)

// The original H1540 loss case must still separate attempts sharing a
// logical epoch, while NAT-rewritten source tuples cannot split a group.
func TestPLAN028Game2ColdRetryCannotMixStaleProtectedEpochLanes(t *testing.T){
    cohort:=realityfront.V4LinuxGameCohortID{
        Principal:"account-carol-test",TunnelID:[16]byte{1},Epoch:[16]byte{2},Lanes:2,
    }
    stale:=originalGameColdAttemptKey{cohort:cohort,attempt:[16]byte{3}}
    fresh1:=originalGameColdAttemptKey{cohort:cohort,attempt:[16]byte{4}}
    fresh2:=originalGameColdAttemptKey{cohort:cohort,attempt:[16]byte{4}}
    if stale==fresh1||fresh1!=fresh2{t.Fatal("cold group attempt identity")}
}
func TestPLAN028OriginalGame4ColdPortCohortAndForeignScope(t *testing.T){
    cohort:=realityfront.V4LinuxGameCohortID{
        Principal:"account-dave-test",TunnelID:[16]byte{9},Epoch:[16]byte{4},Lanes:4,
    }
    group:=originalGameColdAttemptKey{cohort:cohort,attempt:[16]byte{5}}
    for _,port:=range []uint16{49120,31001,65535,5103}{
        // Even arbitrary NAT ports do not enter the authenticated group key.
        if port==0||group!=(originalGameColdAttemptKey{cohort:cohort,attempt:[16]byte{5}}){
            t.Fatal("NAT port split the protected Game4 group")
        }
    }
    other:=group;other.cohort.TunnelID[0]++
    if other==group{t.Fatal("different logical tunnel joined")}
    other=group;other.attempt[0]++
    if other==group{t.Fatal("different cold attempt joined")}
}
