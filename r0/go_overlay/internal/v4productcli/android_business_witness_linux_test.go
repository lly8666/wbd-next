//go:build linux && wbd_v4_embedded_go && wbd_v4_fec2_product

package v4productcli

import (
 "reflect"
 "testing"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
)
func TestA45OriginalAndroidReturnPathReceiptClasses(t *testing.T){
    // Native counters are read-only. Merely starting Rust M4 / Go READY
    // must emit ZERO receive-side or ICMP business markers.
    if got:=originalAndroidBusinessReceiptClasses(realityfront.V4PublicLoopPulse{});len(got)!=0{
        t.Fatalf("READY without real kernel packets must not fake receipt: %v",got)
    }
    p:=realityfront.V4PublicLoopPulse{RawPollReady:1}
    if got:=originalAndroidBusinessReceiptClasses(p);!reflect.DeepEqual(got,[]string{"RAW_SOCKET_READABLE"}){
        t.Fatalf("raw poll is not parsed/AEAD proof: %v",got)
    }
    p=realityfront.V4PublicLoopPulse{
        RawPollReady:1,RawParseFailed:1,RawParsed:1,
        RawAuthenticated:1,RawAuthRejected:1,ReverseTunWriteFailed:1,
        TunICMPSeen:1,TunTCPSeen:1,TunUDPSeen:1,
    }
    want:=[]string{
        "RAW_SOCKET_READABLE","RAW_PARSE_FAILED","RAW_PARSED",
        "RAW_AUTHENTICATED","RAW_AUTH_REJECTED",
        "REVERSE_TUN_WRITE_FAILED","TUN_ICMP_SEEN",
        "TUN_TCP_SEEN","TUN_UDP_SEEN",
    }
    if got:=originalAndroidBusinessReceiptClasses(p);!reflect.DeepEqual(got,want){
        t.Fatalf("actual original M4 counters classified %v want %v",got,want)
    }
}

func TestA44OriginalAndroidBusinessReceiptClasses(t *testing.T){
 if got:=originalAndroidBusinessReceiptClasses(realityfront.V4PublicLoopPulse{});len(got)!=0{
  t.Fatalf("zero Rust counters cannot claim app business %v",got)
 }
 p:=realityfront.V4PublicLoopPulse{
  TunIPv4Admitted:1,TunIPv4Rejected:2,BusinessRawCopied:3,
  BusinessReverseTun:4,DnsUDP53Seen:1,DnsTCP53Seen:1,
 }
 want:=[]string{"TUN_IPV4_SEEN","TUN_IPV4_REJECTED","APP_RAW_TX_COPIED",
  "APP_REVERSE_TUN_WRITTEN","DNS_UDP53_TUN_SEEN","DNS_TCP53_TUN_SEEN"}
 if got:=originalAndroidBusinessReceiptClasses(p);!reflect.DeepEqual(got,want){
  t.Fatalf("actual witness stages=%v wanted=%v",got,want)
 }
}
