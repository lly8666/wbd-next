//go:build windows && wbd_v4_embedded_go
package main
import "testing"
func TestM0PLAN026GameColdHandoffQueueNeverBlocksRustJoin(t *testing.T){
 inbound:=make(chan m0GameInbound,2);failed:=make(chan error,2)
 for lane:=0;lane<2;lane++{
  if !offerGameColdInbound(inbound,failed,m0GameInbound{lane:lane}){t.Fatal("lost lane")}
 }
 if offerGameColdInbound(inbound,failed,m0GameInbound{lane:1}){t.Fatal("overflow accepted")}
 if len(inbound)!=2{t.Fatal("earlier ciphertext dropped")}
 select{case err:=<-failed:if err==nil{t.Fatal("nil overflow")};default:t.Fatal("no overflow error")}
 if (<-inbound).lane!=0||(<-inbound).lane!=1{t.Fatal("original lane order changed")}
}
