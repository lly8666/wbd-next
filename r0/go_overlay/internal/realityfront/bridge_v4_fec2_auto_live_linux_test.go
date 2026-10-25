//go:build linux && cgo && wbd_v4_embedded_go

package realityfront

import "testing"

// Only native counters from genuine M4 first-copied DATA and authenticated
// reverse M2 can enter the decision. Missing or ambiguous stay unknown.
func TestV4FecAutoMatureDeltaNeverConvertsUnknownToNoLoss(t *testing.T) {
    var older,newer [30]uint64
    older[0],older[1],older[2],older[3],older[4]=100,80,10,7,3
    newer[0],newer[1],newer[2],newer[3],newer[4]=1100,950,70,67,13
    w,ok:=v4FecAutoWindow(newer,older,0)
    if !ok||w.FirstSent!=1000||w.Observed!=930||w.Missing!=60||
        w.Unknown!=70||w.Censored!=0||!w.sane(){
        t.Fatalf("unverified MatureFirstSend cohort was hidden %+v ok=%v",w,ok)
    }
    // Cumulative reset must be UNKNOWN, never a manufactured zero loss.
    reset:=newer
    reset[3]=1
    if _,ok:=v4FecAutoWindow(reset,older,0);ok{
        t.Fatal("native M2 counter reset accepted as an observation")
    }
    reset=newer
    reset[4]=1000
    if _,ok:=v4FecAutoWindow(reset,older,0);ok{
        t.Fatal("impossible mature numerator accepted")
    }
}

func TestV4Fec2OriginalPositiveConfirmationLagNoFakeRTT(t *testing.T) {
    var native [30]uint64
    // Without native unambiguous positive, no RTT or zero-lag sample
    // exists, even if genuine reverse control records exist elsewhere.
    native[10]=123
    lag,n,mean,known:=v4Fec2PositiveConfirmation(native)
    if lag!=0||n!=0||mean!=0||known {
        t.Fatalf("no authenticated DATA positive sample: %d/%d/%d known=%t",lag,n,mean,known)
    }
    // Native field indexes 12/13 are 8s mature positive lag ns
    // and unambiguous actual FIRST-send DATA sample count.
    native[12],native[13]=1_207_000_000,2
    lag,n,mean,known=v4Fec2PositiveConfirmation(native)
    if lag!=1_207_000_000||n!=2||mean!=603500||!known {
        t.Fatalf("original positive lag not preserved: %d/%d/%d known=%t",lag,n,mean,known)
    }
    // Saturating an absolute u64 sum must not overflow conversion or
    // divide-by-zero; even a true zero-latency positive stays KNOWN.
    native[12],native[13]=0,1
    _,n,mean,known=v4Fec2PositiveConfirmation(native)
    if n!=1||mean!=0||!known{t.Fatal("real zero positive mistaken as UNKNOWN")}
    native[12],native[13]=^uint64(0),1
    _,n,mean,known=v4Fec2PositiveConfirmation(native)
    if n!=1||mean!=^uint64(0)/1000||!known{t.Fatal("large native lag overflow")}
}
