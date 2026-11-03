//go:build windows && wbd_v4_embedded_go
package main
import (
 "net/netip"
 "testing"
)
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

func TestM0PLAN028GameAllLanesSameServerPortDifferentSources(t *testing.T){
 for _,serverPort:=range []uint16{443,8443}{
  o:=m0NativeV4Options{ServerIP:netip.MustParseAddr("192.0.2.19"),ServerPort:serverPort,SourcePort:41031}
  seen:=map[uint16]bool{}
  for lane:=0;lane<4;lane++{
   flow,err:=m0WindowsGameOriginalClientFlow(o,[4]byte{192,0,2,31},lane)
   if err!=nil{t.Fatalf("lane %d: %v",lane,err)}
   if flow.PeerPort!=serverPort{t.Fatalf("Game lane %d sent to %d, only %d is served",lane,flow.PeerPort,serverPort)}
   if flow.LocalPort!=uint16(41031+lane)||seen[flow.LocalPort]{t.Fatalf("Game lane %d local source collision",lane)}
   if flow.PeerIP!=o.ServerIP.As4(){t.Fatal("changed server IPv4")}
   seen[flow.LocalPort]=true
  }
 }
}
func TestM0PLAN028GameRejectSourcePortOverflowBeforeAnySYN(t *testing.T){
 o:=m0NativeV4Options{ServerIP:netip.MustParseAddr("192.0.2.19"),ServerPort:443,SourcePort:65535}
 if _,err:=m0WindowsGameOriginalClientFlow(o,[4]byte{192,0,2,31},1);err==nil{
  t.Fatal("Game4 source port wrap must fail before emitting first SYN")
 }
 o.SourcePort=41031;o.ServerPort=0
 if _,err:=m0WindowsGameOriginalClientFlow(o,[4]byte{192,0,2,31},0);err==nil{
  t.Fatal("missing fixed service port")
 }
}
