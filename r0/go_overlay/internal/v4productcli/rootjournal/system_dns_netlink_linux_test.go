//go:build linux

package rootjournal

import (
 "encoding/binary"
 "strings"
 "testing"
)
func TestB94ExactSystemDNSNetlinkRoundtrip(t *testing.T){
 for _,v6:=range []bool{false,true}{
  p:=SystemDNSPlan{DNSPlan:DNSPlan{Version:1,Tun:"wbdv40",Lease:"10.66.0.8/32",Port:43210,UIDs:[]int{11200}},NetID:105,IPv6:v6}
  family,table,e:=dnsNLFamily(p.family());if e!=nil{t.Fatal(e)}
  for _,r:=range p.rules("add"){
   data,e:=systemDNSNetlinkPayload(r);if e!=nil{t.Fatal(e)}
   // Match actual Linux/Android dump metadata: all ones means no suppressor.
   dump:=append(append([]byte(nil),data...),dnsNLAttr(dnsFRASuppressPrefixlen,dnsNL32(^uint32(0)))...)
   dump=append(dump,dnsNLAttr(dnsFRASuppressIfgroup,dnsNL32(^uint32(0)))...)
   line,e:=systemDNSNetlinkRow(dump,family,table);if e!=nil{t.Fatal(e)}
   for _,kind:=range []uint16{dnsFRASuppressPrefixlen,dnsFRASuppressIfgroup}{
    bad:=append(append([]byte(nil),data...),dnsNLAttr(kind,dnsNL32(0))...)
    if _,e=systemDNSNetlinkRow(bad,family,table);e==nil{t.Fatal("enabled suppressor accepted")}
   }
   got,e:=systemRuleKey(strings.Fields(line),p.table());if e!=nil{t.Fatal(e)}
   expected,e:=systemRuleKey(append([]string{r[4]+":","from","all"},r[5:]...),p.table())
   if e!=nil||got!=expected{t.Fatalf("kernel rule differs %s %s %v",got,expected,e)}
   // Readback must never lose an unknown or changed selector.
   if _,e=systemDNSNetlinkRow(append(append([]byte(nil),data...),dnsNLAttr(23,[]byte{1,0,1,0})...),family,table);e==nil{t.Fatal("foreign sport accepted")}
   bad:=append([]byte(nil),data...);binary.NativeEndian.PutUint32(bad[8:12],2)
   if _,e=systemDNSNetlinkRow(bad,family,table);e==nil{t.Fatal("inverted rule accepted")}
   r[14]="54";if _,e=systemDNSNetlinkPayload(r);e==nil{t.Fatal("different port accepted")}
  }
 }
}
