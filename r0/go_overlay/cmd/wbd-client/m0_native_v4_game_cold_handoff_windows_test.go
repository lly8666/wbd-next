//go:build windows && wbd_v4_embedded_go
package main
import "testing"
// Cold buffer exhaustion is not a reason to kill a genuine TLS reader,
// or cause a permanent Game4-FEC startup loss before native Rust handoff.
func TestM0PLAN027GameColdBacklogDropsOnlyOptionalDetachedM3(t *testing.T){
 inbound:=make(chan m0GameInbound,2)
 if !offerGameColdInbound(inbound,m0GameInbound{lane:0})||!offerGameColdInbound(inbound,m0GameInbound{lane:1}){t.Fatal("early capacity")}
 if offerGameColdInbound(inbound,m0GameInbound{lane:1}){t.Fatal("full buffer must not grow")}
 if len(inbound)!=2{t.Fatal("earlier authentic ciphertext replaced")}
 if (<-inbound).lane!=0{t.Fatal("FIFO cold ciphertext reordering")}
 if !offerGameColdInbound(inbound,m0GameInbound{lane:0}){t.Fatal("reader must resume after overflow")}
 if (<-inbound).lane!=1||(<-inbound).lane!=0{t.Fatal("later authentic M3 no longer admitted")}
}
