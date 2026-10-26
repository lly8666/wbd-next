package faketcp

import (
    "fmt"
    "sync/atomic"
)

// Public V4 cold start fixes the local SYN/SYN-ACK advertised TCP payload
// ceiling from the actual interface + configured outer IPv4 MTU. This is
// scoped to the public product's one-time startup; legacy Go defaults and
// unrelated callers continue to use DefaultMSS=1360.
var publicV4MSS atomic.Uint32

func SetPublicV4AdvertisedMSS(mss uint16) error {
    if mss < 536 || mss > 8960 {
        return fmt.Errorf("public v4 mss %d outside supported IPv4 envelope", mss)
    }
    for {
        existing := publicV4MSS.Load()
        if existing != 0 {
            if existing == uint32(mss) { return nil }
            return fmt.Errorf("public v4 mss immutable after admission: %d != %d", existing, mss)
        }
        if publicV4MSS.CompareAndSwap(0, uint32(mss)) { return nil }
    }
}
func PublicV4AdvertisedMSS() uint16 {
    if v := publicV4MSS.Load(); v != 0 { return uint16(v) }
    return DefaultMSS
}
