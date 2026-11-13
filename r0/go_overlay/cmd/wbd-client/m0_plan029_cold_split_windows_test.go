//go:build windows && wbd_v4_embedded_go
package main
import ("net/netip";"os";"path/filepath";"strings";"testing")
func plan029Options(mode string)m0NativeV4Options{
 return m0NativeV4Options{
  RouteMode:mode,DirectDNS4:netip.MustParseAddr("223.5.5.5"),
  DNSServers4:[]netip.Addr{netip.MustParseAddr("1.1.1.1")},
  Bypass4:[]netip.Prefix{netip.MustParsePrefix("203.0.113.0/24")},
  Direct4:[]netip.Prefix{netip.MustParsePrefix("198.51.100.0/24")}}
}
func TestPlan029GoColdRustThreeModesDnsEqualAllowedNoBackup(t *testing.T){
 for _,mode:=range []string{"all","bypass-lan","bypass-lan-cn"}{
  o:=plan029Options(mode)
  c,e:=m0Plan029ColdSource(o,netip.MustParseAddr("10.1.0.7"),
   14,netip.MustParseAddr("10.234.12.34"),1280,[]byte("CN.EXAMPLE.\n"))
  if e!=nil||c.InnerMTU!=1280||c.DirectHard!=16384||len(c.Direct)!=1{
   t.Fatalf("cold %s %v",mode,e)
  }
  if mode=="bypass-lan-cn"{
   if len(c.CN)!=1||len(c.LAN)==0||string(c.Domains)!="cn.example\n"{t.Fatal("CN cold source",c)}
  }else if len(c.CN)!=0||len(c.Domains)!=0{
   t.Fatal("inactive CN allocations",mode)
  }
 }
 same:=plan029Options("bypass-lan-cn")
 same.DNSServers4=[]netip.Addr{same.DirectDNS4}
 if _,e:=m0Plan029ColdSource(same,netip.MustParseAddr("10.1.0.7"),
  14,netip.MustParseAddr("10.234.12.34"),1280,nil);e!=nil{t.Fatal(e)}
 same.DNSServers4=append(same.DNSServers4,netip.MustParseAddr("9.9.9.9"))
 if _,e:=m0Plan029ColdSource(same,netip.MustParseAddr("10.1.0.7"),
  14,netip.MustParseAddr("10.234.12.34"),1280,nil);e==nil{t.Fatal("backup DNS admitted")}
}
func TestPlan029GoColdDomainsIDNAAndRejectUnsupportedGeosite(t *testing.T){
 b,e:=m0Plan029CanonicalDomains([]byte("Example.CN.\n=例子.cn\n"))
 if e!=nil||!strings.Contains(string(b),"example.cn\n")||
  !strings.Contains(string(b),"=xn--fsqu00a.cn\n"){t.Fatalf("%q %v",b,e)}
 for _,s:=range []string{"include:cn","regexp:^.*\\.cn$",
   "keyword:cn","example.cn @cn","bad..cn","example.cn&ads"}{
  if _,e:=m0Plan029CanonicalDomains([]byte(s));e==nil{
   t.Fatalf("unsupported %q silently accepted",s)
  }
 }
}

func TestPlan029GoV3TrialOnlyOwnedCIAndExplicitValidatedDomains(t *testing.T){
 o:=plan029Options("bypass-lan-cn")
 o.StatePath=filepath.Join(t.TempDir(),"network-state")
 physical:=netip.MustParseAddr("10.1.0.7")
 lease:=netip.MustParseAddr("10.234.12.34")
 t.Setenv("GITHUB_ACTIONS","false")
 t.Setenv("WBD_PLAN029_NATIVE_V3_TRIAL","1")
 c,e:=m0Plan029TrialCold(o,physical,14,lease,1280)
 if e!=nil||c!=nil{t.Fatal("private V3 without CI admitted",e)}
 t.Setenv("GITHUB_ACTIONS","true")
 if _,e=m0Plan029TrialCold(o,physical,14,lease,1280);e==nil{
  t.Fatal("CN missing rules silently degraded")
 }
 p:=filepath.Join(t.TempDir(),"cn-rules.txt")
 if e=os.WriteFile(p,[]byte("cn.example\n=exact.cn\n"),0600);e!=nil{t.Fatal(e)}
 t.Setenv("WBD_PLAN029_CN_RULES_FILE",p)
 c,e=m0Plan029TrialCold(o,physical,14,lease,1280)
 if e!=nil||c==nil||string(c.Domains)!="cn.example\n=exact.cn\n"||
  len(c.FakeJournalPath)==0||c.DirectHard!=16384{
  t.Fatalf("cold trial missing durable CIDR/DNS/IDNA proof: %+v %v",c,e)
 }
 // Explicit route-mode all does NOT silently allocate CN-domain tracking.
 o.RouteMode="all"
 c,e=m0Plan029TrialCold(o,physical,14,lease,1280)
 if e!=nil||c==nil||len(c.Domains)!=0||len(c.FakeJournalPath)!=0{
  t.Fatal("all mode allocated CN trie/journal",e)
 }
}
