//go:build linux && wbd_v4_embedded_go && wbd_v4_fec2_product

package v4productcli

import (
 "reflect"
 "testing"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
)
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
