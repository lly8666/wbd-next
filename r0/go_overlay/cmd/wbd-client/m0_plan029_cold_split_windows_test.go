//go:build windows && wbd_v4_embedded_go
package main
import ("fmt";"net/netip";"os";"path/filepath";"strings";"testing")
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
  if e!=nil||c.InnerMTU!=1280||c.DirectHard!=16384||
   (mode=="all"&&len(c.Direct)!=0)||(mode!="all"&&len(c.Direct)!=1){
   t.Fatalf("cold %s %v",mode,e)
  }
  if mode=="bypass-lan-cn"{
   if len(c.CN)<4096||len(c.LAN)==0||string(c.Domains)!="cn.example\n"{t.Fatal("CN cold source",len(c.CN),c)}
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
// H1960: two configured DNS settings are each ONE unicast IPv4 endpoint.
// No invalid 0/broadcast sentinel may silently become a system resolver,
// second endpoint or cross-direction fallback at cold Apply.
func TestPlan029H1963ColdDnsTwoSingleEndpointsRejectZeroAndBroadcast(t *testing.T){
 physical:=netip.MustParseAddr("10.1.0.7")
 lease:=netip.MustParseAddr("10.234.12.34")
 for _,mode:=range []string{"all","bypass-lan","bypass-lan-cn"}{
  for _,bad:=range []string{"0.0.0.0","255.255.255.255"}{
   for _,which:=range []string{"direct","tunnel"}{
    o:=plan029Options(mode)
    addr:=netip.MustParseAddr(bad)
    if which=="direct"{o.DirectDNS4=addr}else{o.DNSServers4=[]netip.Addr{addr}}
    if c,err:=m0Plan029ColdSource(o,physical,14,lease,1280,[]byte("cn.example\n"));
       err==nil{t.Fatalf("invalid %s DNS %s accepted in mode=%s: %+v",which,bad,mode,c)}
   }
  }
  // User may deliberately set both directions to the SAME valid IPv4;
  // this remains two independent purposes, not multiple/fallback DNS.
  same:=plan029Options(mode)
  same.DNSServers4=[]netip.Addr{same.DirectDNS4}
  if _,err:=m0Plan029ColdSource(same,physical,14,lease,1280,[]byte("cn.example\n"));
     err!=nil{t.Fatalf("equal valid DNS lost in mode=%s: %v",mode,err)}
 }
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
 if e!=nil||c==nil||c.RouteMode!=0||c.PolicyFlags!=0||
  len(c.Direct)!=0||len(c.Domains)!=0||len(c.FakeJournalPath)!=0{
  t.Fatal("business-off still requires original Rust V3 DNS/padding, never old V2",e)
 }
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
 if e!=nil||c==nil||c.TCPSynthetic4==[4]byte{}||len(c.Domains)!=0||len(c.FakeJournalPath)!=0{
  t.Fatal("all mode allocated CN trie/journal",e)
 }
}

func TestPlan029ExplicitProductSplitOutsideCIUsesOnlyConfiguredRules(t *testing.T){
 o:=plan029Options("bypass-lan-cn")
 o.SplitEnable=true
 o.CNDomainDirect=true // earlier original FakeIP behavior is explicit
 o.StatePath=filepath.Join(t.TempDir(),"network-state")
 path:=filepath.Join(t.TempDir(),"cn-rule-source.txt")
 if err:=os.WriteFile(path,[]byte("cn.example\n=exact.cn\n"),0600);err!=nil{t.Fatal(err)}
 o.CNRulesFile=path
 t.Setenv("GITHUB_ACTIONS","false")
 t.Setenv("WBD_PLAN029_NATIVE_V3_TRIAL","")
 t.Setenv("WBD_PLAN029_CN_RULES_FILE",filepath.Join(t.TempDir(),"foreign-ci-rules"))
 c,err:=m0Plan029TrialCold(o,netip.MustParseAddr("10.1.0.7"),
  14,netip.MustParseAddr("10.234.12.34"),1280,[16]byte{2})
 if err!=nil||c==nil||string(c.Domains)!="cn.example\n=exact.cn\n"||
  c.TCPSynthetic4==[4]byte{}||len(c.FakeJournalPath)==0{
  t.Fatalf("real configured split was still CI-gated: %+v %v",c,err)
 }
 o.CNRulesFile="relative-cn.txt"
 if _,err=m0Plan029TrialCold(o,netip.MustParseAddr("10.1.0.7"),
  14,netip.MustParseAddr("10.234.12.34"),1280,[16]byte{2});err==nil{
  t.Fatal("product admitted nonabsolute unowned CN rules path")
 }
 o.CNRulesFile=path
 o.SplitEnable=false
 if cold,err:=m0Plan029TrialCold(o,netip.MustParseAddr("10.1.0.7"),
  14,netip.MustParseAddr("10.234.12.34"),1280,[16]byte{2});
  err!=nil||cold==nil||cold.RouteMode!=0||cold.PolicyFlags!=0||
  len(cold.CN)!=0||len(cold.Direct)!=0||len(cold.Domains)!=0||
  len(cold.FakeJournalPath)!=0||cold.TCPSynthetic4==[4]byte{}{
  t.Fatal("disabled business still needs DNS/padding V3, not Direct or FakeIP",err)
 }
}

// H2102: all/off does not read inactive CN rules or enforce a saved
// business Direct hard cap; the two public DNS endpoints remain required.
func TestPlan029BAllOffIgnoresInactiveBusinessCapacity(t *testing.T){
 physical:=netip.MustParseAddr("10.1.0.7")
 lease:=netip.MustParseAddr("10.234.12.34")
 t.Setenv("GITHUB_ACTIONS","false")
 t.Setenv("WBD_PLAN029_NATIVE_V3_TRIAL","")
 for _,tc:=range []struct{mode string;split bool}{
  {"bypass-lan-cn",false},{"all",true},{"all",false},
 }{
  o:=plan029Options(tc.mode)
  o.SplitEnable=tc.split
  o.DirectFlowHard=^uint32(0)
  o.ChinaIPFile=filepath.Join(t.TempDir(),"missing-cn-ips")
  o.CNRulesFile=filepath.Join(t.TempDir(),"missing-cn-domains")
  cold,err:=m0Plan029TrialCold(o,physical,14,lease,1389,[16]byte{2})
  if err!=nil||cold==nil||cold.RouteMode!=0||cold.DirectHard!=16384||
   cold.TCPSynthetic4==[4]byte{}||len(cold.CN)!=0||
   len(cold.Direct)!=0||len(cold.Domains)!=0||
   len(cold.FakeJournalPath)!=0{
   t.Fatalf("inactive Direct cap/rules blocked public Rust DNS: mode=%s split=%t cfg=%+v err=%v",tc.mode,tc.split,cold,err)
  }
  o.DirectDNS4=netip.IPv4Unspecified()
  if _,err=m0Plan029TrialCold(o,physical,14,lease,1389,[16]byte{2});err==nil{
   t.Fatal("inactive split suppressed mandatory bootstrap DNS validation")
  }
 }
 active:=plan029Options("bypass-lan")
 active.SplitEnable=true
 active.DirectFlowHard=^uint32(0)
 if _,err:=m0Plan029TrialCold(active,physical,14,lease,1389,[16]byte{2});err==nil{
  t.Fatal("active Direct cap exceeded 16384 but was accepted")
 }
}

// B4: three genuine cold-configuration generations must not resurrect a
// retired FakeIP writer or force disabled Direct resources to be present.
func TestPlan029BThreeGenerationsAdvancedOrdinaryAllNoStaleWriter(t *testing.T){
 t.Setenv("GITHUB_ACTIONS","false")
 t.Setenv("WBD_PLAN029_NATIVE_V3_TRIAL","")
 physical:=netip.MustParseAddr("10.1.0.7")
 lease:=netip.MustParseAddr("10.234.12.34")
 root:=t.TempDir()
 rules:=filepath.Join(root,"cn-domains.txt")
 if err:=os.WriteFile(rules,[]byte("cn.example\n"),0600);err!=nil{t.Fatal(err)}
 o:=plan029Options("bypass-lan-cn")
 o.SplitEnable=true
 o.CNDomainDirect=true
 o.StatePath=filepath.Join(root,"network-state")
 o.CNRulesFile=rules
 first,err:=m0Plan029TrialCold(o,physical,14,lease,1389,[16]byte{2})
 if err!=nil||first==nil||first.RouteMode!=2||first.PolicyFlags!=1||
  len(first.Domains)==0||len(first.FakeJournalPath)==0{
  t.Fatalf("advanced generation must own selective FakeIP: %+v %v",first,err)
 }
 // The cold constructor must never read, unlink, truncate or re-open the
 // prior generation's file in ordinary/all mode. A real network WAL Stop
 // remains a separate signed B4 test, not this pure admission assertion.
 previousJournal:=string(first.FakeJournalPath)
 sentinel:=[]byte("TEST_ONLY_PREVIOUS_GENERATION_DO_NOT_REBIND")
 if err:=os.WriteFile(previousJournal,sentinel,0600);err!=nil{t.Fatal(err)}
 o.CNDomainDirect=false
 second,err:=m0Plan029TrialCold(o,physical,14,lease,1389,[16]byte{3})
 if err!=nil||second==nil||second.RouteMode!=2||second.PolicyFlags!=0||
  len(second.Domains)==0||len(second.FakeJournalPath)!=0||
  first.TCPSynthetic4==second.TCPSynthetic4{
  t.Fatalf("ordinary generation must keep CN DNS but no old FakeIP writer: %+v %v",second,err)
 }
 o.SplitEnable=false
 o.RouteMode="all"
 o.CNRulesFile=filepath.Join(root,"old-rules-absent")
 o.ChinaIPFile=filepath.Join(root,"old-ips-absent")
 o.DirectFlowHard=^uint32(0)
 third,err:=m0Plan029TrialCold(o,physical,14,lease,1389,[16]byte{4})
 if err!=nil||third==nil||third.RouteMode!=0||third.PolicyFlags!=0||
  len(third.Domains)!=0||len(third.Direct)!=0||len(third.CN)!=0||
  len(third.FakeJournalPath)!=0||third.DirectHard!=16384||
  second.TCPSynthetic4==third.TCPSynthetic4||
  third.DirectDNS!=first.DirectDNS||third.TunnelDNS!=first.TunnelDNS{
  t.Fatalf("split-off must keep DNS/epoch while abandoning business Direct: %+v %v",third,err)
 }
 got,err:=os.ReadFile(previousJournal)
 if err!=nil||string(got)!=string(sentinel){
  t.Fatalf("old FakeIP writer was touched across cold generations: %v",err)
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

func TestPlan029H1946Cold4096CNIndependentOfOSBypass(t *testing.T){
 path:=filepath.Join(t.TempDir(),"china-4096.txt")
 var lines strings.Builder
 for i:=0;i<4096;i++{
  fmt.Fprintf(&lines,"11.42.%d.%d/32\n",i/128,(i%128)*2)
 }
 if e:=os.WriteFile(path,[]byte(lines.String()),0600);e!=nil{t.Fatal(e)}
 o:=plan029Options("bypass-lan-cn")
 o.Bypass4=[]netip.Prefix{netip.MustParsePrefix("10.0.0.0/8")}
 o.ChinaIPFile=path
 cold,e:=m0Plan029ColdSource(o,netip.MustParseAddr("10.1.0.7"),
  14,netip.MustParseAddr("10.234.12.34"),1280,[]byte("cn.example\n"))
 if e!=nil{t.Fatal(e)}
 count:=0;first:=false;last:=false
 for _,p:=range cold.CN{
  if p.Bits!=32||p.Network[0]!=11||p.Network[1]!=42{continue}
  count++
  if p.Network==([4]byte{11,42,0,0}){first=true}
  if p.Network==([4]byte{11,42,31,254}){last=true}
 }
 if count!=4096||!first||!last{
  t.Fatalf("Rust cold CN truncated/merged: raw32=%d first=%t last=%t",count,first,last)
 }
 o.ChinaIPFile=path+".missing"
 if _,e:=m0Plan029ColdSource(o,netip.MustParseAddr("10.1.0.7"),
  14,netip.MustParseAddr("10.234.12.34"),1280,nil);e==nil{
  t.Fatal("explicit missing CN source silently fell back")
 }
}

func TestPlan029BOrdinaryCNKeepsDnsTrieWithoutFakeIpJournal(t *testing.T){
 o:=plan029Options("bypass-lan-cn")
 o.SplitEnable=true
 o.CNDomainDirect=false // fresh config ordinary, no FakeIP publication
 o.StatePath=filepath.Join(t.TempDir(),"network-state")
 path:=filepath.Join(t.TempDir(),"cn-rules.txt")
 if e:=os.WriteFile(path,[]byte("www.cn.example\n"),0600);e!=nil{t.Fatal(e)}
 o.CNRulesFile=path
 t.Setenv("GITHUB_ACTIONS","false")
 t.Setenv("WBD_PLAN029_NATIVE_V3_TRIAL","")
 c,e:=m0Plan029TrialCold(o,netip.MustParseAddr("10.1.0.7"),
  14,netip.MustParseAddr("10.234.12.34"),1389,[16]byte{2})
 if e!=nil||c==nil||c.RouteMode!=2||c.PolicyFlags!=0||
  string(c.Domains)!="www.cn.example\n"||len(c.FakeJournalPath)!=0||
  c.TCPSynthetic4==[4]byte{}||len(c.CN)==0{
  t.Fatalf("ordinary CN must retain direct DNS and CN IP, never FakeIP: %+v %v",c,e)
 }
 o.CNDomainDirect=true
 c,e=m0Plan029TrialCold(o,netip.MustParseAddr("10.1.0.7"),
  14,netip.MustParseAddr("10.234.12.34"),1389,[16]byte{2})
 if e!=nil||c==nil||c.PolicyFlags!=1||len(c.FakeJournalPath)==0{
  t.Fatalf("advanced CN does not own journal: %+v %v",c,e)
 }
}
