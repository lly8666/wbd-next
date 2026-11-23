package rootjournal

import (
 "reflect"
 "testing"
 "fmt"
 "strings"
)

func TestB33DirectIPv4CIDRColdCanonicalModes(t *testing.T){
 list,e:=ParseDirectCIDRs("192.168.7.0/24, 10.8.0.0/16,198.51.100.9/32")
 if e!=nil||!reflect.DeepEqual(list,[]string{"10.8.0.0/16","192.168.7.0/24","198.51.100.9/32"}){
  t.Fatalf("canonical direct CIDRs %v %v",list,e)
 }
 if !validDirectCIDRs(list,"203.0.113.10"){t.Fatal("valid direct CIDRs refused")}
 for _,bad:=range []string{
  "0.0.0.0/0","192.168.1.3/24","224.0.0.0/4","127.0.0.0/8",
  "10.0.0.0/8,10.0.0.0/8","10.0.0.0/8,,192.168.0.0/16",
 }{
  if x,e:=ParseDirectCIDRs(bad);e==nil{t.Fatalf("accepted direct %q: %v",bad,x)}
 }
 var prefixes []string
 for i:=0;i<16;i++{prefixes=append(prefixes,fmt.Sprintf("10.%d.0.0/16",i))}
 all,e:=ParseDirectCIDRs(strings.Join(prefixes,","))
 if e!=nil||len(all)!=16{t.Fatalf("16 direct IPv4 prefixes not parsed: %v %v",all,e)}
 if !validDirectCIDRs(all,"203.0.113.10"){t.Fatal("16 direct prefixes not accepted")}
 if _,e=ParseDirectCIDRs(strings.Join(prefixes,",")+",10.16.0.0/16");e==nil{
  t.Fatal("17 direct IPv4 prefixes should require explicit larger contract")
 }
 if validDirectCIDRs([]string{"203.0.113.10/32"},"203.0.113.10"){t.Fatal("duplicate protected peer route")}
 if validDirectCIDRs([]string{"192.168.0.0/16","10.0.0.0/8"},""){t.Fatal("noncanonical route order")}
}

func TestB33ExistingOriginalPeerAndAdditionalDirectKernelFIB(t *testing.T){
 routes:="default dev wbdv40 scope link\nthrow 203.0.113.9\nthrow 192.168.0.0/16\nthrow 10.10.10.7\n"
 direct:=[]string{"10.10.10.7/32","192.168.0.0/16"}
 route,peer,present,e:=routeWithDirect(routes,"wbdv40","203.0.113.9",direct)
 if e!=nil||!route||!peer||!allDirectPresent(present){t.Fatalf("kernel readback %t %t %v %v",route,peer,present,e)}
 missing,other,flags,e:=routeWithDirect("default dev wbdv40\nthrow 203.0.113.9\n","wbdv40","203.0.113.9",direct)
 if e!=nil||!missing||!other||anyDirectPresent(flags){t.Fatalf("missing direct must remain missing: %v %v",flags,e)}
 for _,foreign:=range []string{
  "throw 192.168.0.0/16 via 10.0.0.1",
  "throw 172.16.0.0/12",
  "throw 192.168.0.0/16\nthrow 192.168.0.0/16",
 }{
  if _,_,_,e:=routeWithDirect("default dev wbdv40\nthrow 203.0.113.9\n"+foreign,"wbdv40","203.0.113.9",direct);e==nil{
   t.Fatalf("accepted foreign/direct duplicate %q",foreign)
  }
 }
}
