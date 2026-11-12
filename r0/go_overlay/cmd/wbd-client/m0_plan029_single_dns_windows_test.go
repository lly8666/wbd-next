//go:build windows
package main
import ("net/netip";"testing")
func TestPlan029SingleDNSNoBackup(t *testing.T){
 cases:=[]struct{d,u,old string;explicit bool;wD,wU string;retired int;bad bool}{
  {"223.5.5.5","1.1.1.1","",false,"223.5.5.5","1.1.1.1",0,false},
  {"223.5.5.5","1.1.1.1","9.9.9.9,8.8.8.8",false,"223.5.5.5","9.9.9.9",1,false},
  {"223.5.5.5","9.9.9.9","9.9.9.9,8.8.8.8",true,"223.5.5.5","9.9.9.9",1,false},
  {"223.5.5.5","1.1.1.1","9.9.9.9",true,"","",0,true},
  {"223.5.5.5,1.1.1.1","1.1.1.1","",false,"","",0,true},
  {"223.5.5.5","8.8.8.8,1.1.1.1","",false,"","",0,true},
  {"127.0.0.1","1.1.1.1","",false,"","",0,true},
 }
 for _,c:=range cases{
  a,b,n,e:=m0Plan029DNSSettings(c.d,c.u,c.old,c.explicit)
  if (e!=nil)!=c.bad{t.Fatalf("%+v error=%v",c,e)}
  if c.bad{continue}
  if a!=netip.MustParseAddr(c.wD)||b!=netip.MustParseAddr(c.wU)||n!=c.retired{
   t.Fatalf("%+v got %v %v %d",c,a,b,n)
  }
 }
}
