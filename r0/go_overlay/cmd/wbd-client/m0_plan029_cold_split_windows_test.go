//go:build windows && wbd_v4_embedded_go
package main
import ("net/netip";"os";"path/filepath";"strings";"testing")
func plan029Options(mode string)m0NativeV4Options{
 return m0NativeV4Options{
  Installation:[16]byte{1},
  RouteMode:mode,DirectDNS4:netip.MustParseAddr("223.5.5.5"),
  DNSServers4:[]netip.Addr{netip.MustParseAddr("1.1.1.1")},
  Bypass4:[]netip.Prefix{netip.MustParsePrefix("203.0.113.0/24")},
  Direct4:[]netip.Prefix{netip.MustParsePrefix("198.51.100.0/24")}}
}
func TestPLAN029StartupPaddingCanonicalLegacyAndConflicts(t *testing.T){
 cases:=[]struct{value string;old bool;want string;bad bool}{
  {"",false,"off",false},{"",true,"tls",false},
  {"off",false,"off",false},{"tls",false,"tls",false},
  {"flows",false,"flows",false},{"tls",true,"tls",false},
  {"off",true,"",true},{"flows",true,"",true},{"all",false,"",true},
 }
 for _,c:=range cases{
  got,err:=m0CanonicalWindowsStartupPadding(c.value,c.old)
  if (err!=nil)!=c.bad||(!c.bad&&got!=c.want){
   t.Fatalf("mode=%q old=%t got=%q err=%v",c.value,c.old,got,err)
  }
 }
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
 c,e:=m0Plan029TrialCold(o,physical,14,lease,1280,[16]byte{2})
 if e!=nil||c!=nil{t.Fatal("private V3 without CI admitted",e)}
 t.Setenv("GITHUB_ACTIONS","true")
 if _,e=m0Plan029TrialCold(o,physical,14,lease,1280,[16]byte{2});e==nil{
  t.Fatal("CN missing rules silently degraded")
 }
 p:=filepath.Join(t.TempDir(),"cn-rules.txt")
 if e=os.WriteFile(p,[]byte("cn.example\n=exact.cn\n"),0600);e!=nil{t.Fatal(e)}
 t.Setenv("WBD_PLAN029_CN_RULES_FILE",p)
 c,e=m0Plan029TrialCold(o,physical,14,lease,1280,[16]byte{2})
 if e!=nil||c==nil||c.TCPSynthetic4==[4]byte{}||string(c.Domains)!="cn.example\n=exact.cn\n"||
  len(c.FakeJournalPath)==0||c.DirectHard!=16384{
  t.Fatalf("cold trial missing durable CIDR/DNS/IDNA proof: %+v %v",c,e)
 }
 // Explicit route-mode all does NOT silently allocate CN-domain tracking.
 o.RouteMode="all"
 c,e=m0Plan029TrialCold(o,physical,14,lease,1280,[16]byte{2})
 if e!=nil||c==nil||c.TCPSynthetic4!=[4]byte{}||len(c.Domains)!=0||len(c.FakeJournalPath)!=0{
  t.Fatal("all mode allocated CN trie/journal",e)
 }
}

func TestPlan029GenerationSyntheticOnlyOneOwnedHost(t *testing.T){
 install:=[16]byte{1};e1:=[16]byte{2};e2:=[16]byte{3}
 a,err:=m0Plan029SyntheticForGeneration(install,e1)
 if err!=nil||a[0]!=198||a[1]!=19||a[3]==0||a[3]==255{t.Fatalf("invalid synthetic %v %v",a,err)}
 b,err:=m0Plan029SyntheticForGeneration(install,e1)
 if err!=nil||a!=b{t.Fatal("synthetic unstable",err)}
 b,err=m0Plan029SyntheticForGeneration(install,e2)
 if err!=nil||a==b{t.Fatal("epoch not isolated",err)}
 if _,err=m0Plan029SyntheticForGeneration(install,[16]byte{});err==nil{t.Fatal("zero generation admitted")}
}

// A generation may select a small Direct-only hard cap for bounded pressure
// testing without forcing the machine to allocate 16k physical sockets.
// Tunnel pins/traffic are independent of this limit in Rust PacketIngress.
func TestPlan029ColdDirectHardConfiguredBoundedAndDefault(t *testing.T){
 for _,tc:=range []struct{requested,want uint32;accept bool}{
  {0,16384,true},{1,1,true},{4096,4096,true},{16384,16384,true},
  {16385,0,false},
 }{
  o:=plan029Options("bypass-lan-cn")
  o.DirectFlowHard=tc.requested
  c,e:=m0Plan029ColdSource(o,netip.MustParseAddr("10.1.0.7"),
   14,netip.MustParseAddr("10.234.12.34"),1280,[]byte("cn.example\n"))
  if tc.accept{
   if e!=nil||c.DirectHard!=tc.want{
    t.Fatalf("direct hard %d, got %d err=%v",tc.requested,c.DirectHard,e)
   }
  }else if e==nil{t.Fatalf("oversized direct hard %d accepted",tc.requested)}
 }
}
