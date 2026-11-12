//go:build windows

package faketcp

import (
 "encoding/binary"
 "net/netip"
 "testing"
 "golang.org/x/net/dns/dnsmessage"
)

func TestPlan029PhysicalDNSFrameDoesNotUseTunnelOrSystemResolver(t *testing.T){
 c:=PhysicalDNSConfig{
  Device:"\\Device\\NPF_{12345678-1234-1234-1234-123456789abc}",
  SourceMAC:[6]byte{1,2,3,4,5,6},NextHopMAC:[6]byte{7,8,9,10,11,12},
  Source4:netip.MustParseAddr("192.168.1.2"),Resolver4:netip.MustParseAddr("192.168.1.1"),
 }
 name,_:=dnsmessage.NewName("vpn.example.")
 q,e:=(&dnsmessage.Message{Header:dnsmessage.Header{ID:55,RecursionDesired:true},Questions:[]dnsmessage.Question{{Name:name,Type:dnsmessage.TypeA,Class:dnsmessage.ClassINET}}}).Pack()
 if e!=nil{t.Fatal(e)}
 wire,e:=physicalDNSFrame(c,52000,q,55);if e!=nil{t.Fatal(e)}
 if string(wire[:6])!=string(c.NextHopMAC[:])||string(wire[6:12])!=string(c.SourceMAC[:]){t.Fatal("wrong original physical Ethernet destination")}
 if got:=binary.BigEndian.Uint16(wire[12:14]);got!=0x800{t.Fatalf("ether type %x",got)}
 if len(wire)!=14+20+8+len(q){t.Fatal("packet length")}
 if physicalDNSChecksumFold(physicalDNSChecksumSum(wire[14:34]))!=0{t.Fatal("IPv4 checksum")}
 src,dst:=c.Source4.As4(),c.Resolver4.As4()
 if physicalDNSChecksumFold(physicalDNSPseudoSum(src[:],dst[:],wire[34:]))!=0{t.Fatal("UDP checksum")}
}

func TestPlan029PhysicalDNSRejectedOffPathAndWrongTransaction(t *testing.T){
 c:=PhysicalDNSConfig{Device:"\\Device\\NPF_{12345678-1234-1234-1234-123456789abc}",
 SourceMAC:[6]byte{1,2,3,4,5,6},NextHopMAC:[6]byte{7,8,9,10,11,12},
 Source4:netip.MustParseAddr("192.168.1.2"),Resolver4:netip.MustParseAddr("192.168.1.1")}
 name,_:=dnsmessage.NewName("vpn.example.")
 resp,e:=(&dnsmessage.Message{Header:dnsmessage.Header{ID:77,Response:true,RecursionAvailable:true},
 Questions:[]dnsmessage.Question{{Name:name,Type:dnsmessage.TypeA,Class:dnsmessage.ClassINET}},
 Answers:[]dnsmessage.Resource{{Header:dnsmessage.ResourceHeader{Name:name,Type:dnsmessage.TypeA,Class:dnsmessage.ClassINET,TTL:25},
 Body:&dnsmessage.AResource{A:[4]byte{203,0,113,7}}}}}).Pack()
 if e!=nil{t.Fatal(e)}
 reverse:=c;reverse.Source4,reverse.Resolver4=c.Resolver4,c.Source4
 reverse.SourceMAC,reverse.NextHopMAC=c.NextHopMAC,c.SourceMAC
 frame,e:=physicalDNSFrame(reverse,53,resp,77)
 if e==nil{t.Fatal("TX forbids privileged source port by design")}
 // A received DNS response needs the inverse UDP tuple; assemble it from
 // the validated source packet then update port and its UDP checksum.
 frame,e=physicalDNSFrame(reverse,52000,resp,77);if e!=nil{t.Fatal(e)}
 binary.BigEndian.PutUint16(frame[34:36],53);binary.BigEndian.PutUint16(frame[36:38],52000)
 binary.BigEndian.PutUint16(frame[40:42],0)
 src,dst:=reverse.Source4.As4(),reverse.Resolver4.As4()
 binary.BigEndian.PutUint16(frame[40:42],physicalDNSChecksumFold(physicalDNSPseudoSum(src[:],dst[:],frame[34:])))
 ips,ok:=physicalDNSReply(frame,c,52000,77,name)
 if !ok||len(ips)!=1||ips[0]!=netip.MustParseAddr("203.0.113.7"){t.Fatalf("valid physical reply %v %v",ips,ok)}
 if _,ok:=physicalDNSReply(frame,c,52000,78,name);ok{t.Fatal("mismatched transaction accepted")}
 frame[26]=1
 if _,ok:=physicalDNSReply(frame,c,52000,77,name);ok{t.Fatal("off-path source accepted")}
}
