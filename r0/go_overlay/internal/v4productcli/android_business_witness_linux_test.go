//go:build linux && wbd_v4_embedded_go && wbd_v4_fec2_product

package v4productcli

import (
 "reflect"
 "strings"
 "testing"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
)
func TestA47OriginalNumericNativeM4Snapshots(t *testing.T){
 var p realityfront.V4PublicLoopPulse
 p.RawDebug[0]=8;p.RawDebug[1]=2;p.RawDebug[2]=4
 p.RawDebug[3]=1;p.RawDebug[14]=83;p.RawDebug[15]=52
 p.RawDebug[16]=24;p.RawDebug[17]=0xc633642f
 p.RawDebug[18]=0xc000022a;p.RawDebug[19]=443;p.RawDebug[20]=40238
 p.RawDebug[21]=11
 p.TunIPv4Admitted=7;p.BusinessRawCopied=6;p.RawParsed=2
 if got:=originalAndroidM4RxSnapshot(p);!strings.Contains(got,
      "kind=rx read=8 data=2 ack=4 tuple=1")||
      !strings.Contains(got,"lastlen=83 lastttl=52 lastflags=24")||
      !strings.Contains(got,"sport=443 dport=40238 errno=11"){
  t.Fatalf("original raw RX numeric forensic fields lost: %s",got)
 }
 if got:=originalAndroidM4OwnerSnapshot(p);!strings.Contains(got,
      "kind=m4 poll=0 parse_fail=0 parsed=2")||
      !strings.Contains(got,"tun=7 trej=0 rawtx=6"){
  t.Fatalf("original native M4 counter evidence lost: %s",got)
 }
}

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

func TestB3dOriginalAndroidTunnelDNSRealNativeClasses(t *testing.T){
  p:=realityfront.V4PublicLoopPulse{DnsUDP53Seen:1}
  got:=originalAndroidBusinessReceiptClasses(p)
  if !reflect.DeepEqual(got,[]string{"DNS_UDP53_TUN_SEEN"}) {
    t.Fatalf("TUN observation cannot claim original M4 copy or DNS reply: %v",got)
  }
  p.DnsTunnelRawCopied=1
  got=originalAndroidBusinessReceiptClasses(p)
  if !reflect.DeepEqual(got,[]string{"DNS_UDP53_TUN_SEEN","DNS_TUNNEL_RAW_COPIED"}) {
    t.Fatalf("RAW copied is not a reverse DNS TUN answer: %v",got)
  }
  p.DnsTunnelReplyTun=1
  got=originalAndroidBusinessReceiptClasses(p)
  if !reflect.DeepEqual(got,[]string{"DNS_UDP53_TUN_SEEN","DNS_TUNNEL_RAW_COPIED",
    "DNS_TUNNEL_REVERSE_TUN_WRITTEN"}) {
    t.Fatalf("original authenticated reverse DNS TUN stage absent: %v",got)
  }
  snapshot:=originalAndroidM4OwnerSnapshot(p)
  if !strings.Contains(snapshot,"dnsudp=1 dnstcp=0 dnsraw=1 dnsrtun=1") {
    t.Fatalf("real original M4 DNS numeric snapshot missing: %s",snapshot)
  }
}

func TestB4AndroidPhysicalDnsOriginalM4ReadbackClasses(t *testing.T){
 p:=realityfront.V4PublicLoopPulse{}
 if got:=originalAndroidBusinessReceiptClasses(p);len(got)!=0{
  t.Fatalf("physical cold grant cannot fabricate sent/received: %v",got)
 }
 p.DnsPhysicalTx=1
 want:=[]string{"DNS_PHYSICAL_UDP_COPIED"}
 if got:=originalAndroidBusinessReceiptClasses(p);!reflect.DeepEqual(got,want){
  t.Fatalf("actual physical UDP TX class missing %v",got)
 }
 p.DnsPhysicalRx=2
 p.DnsPhysicalError=3
 want=[]string{"DNS_PHYSICAL_UDP_COPIED","DNS_PHYSICAL_REVERSE_TUN_WRITTEN","DNS_PHYSICAL_ERROR"}
 if got:=originalAndroidBusinessReceiptClasses(p);!reflect.DeepEqual(got,want){
  t.Fatalf("physical RX/error receipt classes differ %v",got)
 }
 got:=originalAndroidM4OwnerSnapshot(p)
 if !strings.Contains(got,"dnsptx=1 dnsprx=2 dnsperr=3"){
  t.Fatalf("actual original M4 physical DNS counters missing %s",got)
 }
}

func TestB6AndroidDNSOriginalCopyReceiptClassesAndNumericSnapshot(t *testing.T){
 p:=realityfront.V4PublicLoopPulse{}
 if got:=originalAndroidBusinessReceiptClasses(p);len(got)!=0{
  t.Fatalf("B6 zero counters cannot imply DNS success: %v",got)
 }
 if got:=originalAndroidDNSB6Snapshot(p);!strings.Contains(got,
  "cnptx=0 noncnraw=0 tcpraw=0 ptctun=0"){
  t.Fatalf("zero B6 snapshot invalid: %s",got)
 }
 p.DnsCNPhysicalSent=2
 p.DnsNonCNTunnelRaw=3
 p.DnsTCP53OriginalRaw=4
 p.DnsPhysicalTCTun=1
 want:=[]string{"DNS_CN_PHYSICAL_SENT","DNS_NONCN_TUNNEL_RAW_COPIED",
  "DNS_TCP53_ORIGINAL_RAW_COPIED","DNS_PHYSICAL_TC_REPLY_TUN_WRITTEN"}
 if got:=originalAndroidBusinessReceiptClasses(p);!reflect.DeepEqual(got,want){
  t.Fatalf("B6 actual M4 raw/socket/TUN classes differ got=%v",got)
 }
 if got:=originalAndroidDNSB6Snapshot(p);!strings.Contains(got,
  "cnptx=2 noncnraw=3 tcpraw=4 ptctun=1"){
  t.Fatalf("B6 native numeric route snapshot missing: %s",got)
 }
 if got:=originalAndroidM4OwnerSnapshot(p);strings.Contains(got,"cnptx="){
  t.Fatalf("B6 altered legacy A47/B3d/B4 M4 wire: %s",got)
 }
}
