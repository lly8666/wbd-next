package dnsnative

import (
 "bytes"
 "context"
 "errors"
 "net"
 "os"
 "path/filepath"
 "regexp"
 "testing"
)

func TestCNMatcherPreservesFullDomainKeywordRegexpAndDNSLabelBoundaries(t *testing.T){
 r:=&CNRules{
  suffix:map[string]struct{}{"baidu.com":{}},
  exact:map[string]struct{}{"only.example":{}},
  keywords:[]string{"wallet"},
  regex:[]*regexp.Regexp{regexp.MustCompile("(?i)^ads[0-9]+[.]cn$")},
 }
 for _,q:=range []string{"www.baidu.com","baidu.com","ONLY.EXAMPLE","mywallet.net","ads12.cn"}{
  if !r.Match(q){t.Fatalf("missing expected independent CN rule type: %s",q)}
 }
 for _,q:=range []string{"notbaidu.com","notonly.example","only.example.org",
    "ads.cn","badwallet.example..net"," baidu.com","baidu.com.evil.net",""}{
  if r.Match(q){t.Fatalf("unsafe overmatching or malformed DNS: %s",q)}
 }
 if !r.Match("www.baidu.com."){t.Fatal("absolute FQDN normalization lost")}
}
func TestSplitModeRefusesMissingMatcherAndUnboundSockets(t *testing.T){
 dial:=func(context.Context,Path,string,string)(net.Conn,error){
  return nil,errors.New("fixture fail")
 }
 if _,err:=New(dial,nil,true);!errors.Is(err,ErrUnbound){
  t.Fatal("silent fallback to tunnel on missing CN matcher",err)
 }
 if _,err:=New(nil,func(string)bool{return true},true);!errors.Is(err,ErrUnbound){
  t.Fatal("missing path-aware dial accepted",err)
 }
 // Split off may be created without a geosite matcher: all intercepted
 // ordinary DNS then deliberately follows the tunnel DNS endpoint.
 if _,err:=New(dial,nil,false);err!=nil{t.Fatal(err)}
}
func pinnedRules(t *testing.T)[]byte{
 t.Helper()
 path:=os.Getenv("WBD_PINNED_CN_GEOSITE")
 if path==""{t.Skip("real pinned upstream only in B2 dedicated source-locked job")}
 data,err:=os.ReadFile(path)
 if err!=nil{t.Fatal(err)}
 return data
}
func TestPinnedCNGeosite8503FullTypedSnapshotAndNoSilentFallback(t *testing.T){
 raw:=pinnedRules(t)
 r,err:=LoadPinnedCN(raw)
 if err!=nil{t.Fatal("pinned upstream not fully loaded",err)}
 st:=r.Stats()
 if st.Total!=8503||st.Domain!=8431||st.Full!=69||
  st.Regex!=3||st.Keyword!=0||st.SHA256!=PinnedCNSHA256{
  t.Fatalf("geosite silently dropped typed rules: %+v",st)
 }
 // Real pinned geolocation-cn does NOT imply an automatic "*.cn" rule.
 // The older KSU synthetic domain examples are not an upstream geosite oracle.
 for _,name:=range []string{"www.baidu.com","www.qq.com","baidu.com"}{
  if !r.Match(name){t.Fatalf("missing authentic CN rule for %s",name)}
 }
 for _,name:=range []string{"www.example.net","foo.example.cn","baidu.com.evil.example",
  "invalid..domain","-illegal.cn"}{
  if r.Match(name){t.Fatalf("CN rules overmatch non-CN or invalid name %q",name)}
 }
 viaReader,err:=ReadPinnedCN(bytes.NewReader(raw))
 if err!=nil||viaReader.Stats()!=st{t.Fatal("bounded reader differs from direct verifier",err)}
 corrupt:=bytes.Clone(raw)
 corrupt[len(corrupt)/2]^=1
 if _,err=LoadPinnedCN(corrupt);err==nil{t.Fatal("pinned SHA tampering accepted")}
 if _,err=LoadPinnedCN(raw[:len(raw)-1]);err==nil{t.Fatal("truncated CN rules accepted")}
 if _,err=ReadPinnedCN(bytes.NewReader(bytes.Repeat([]byte("x"),MaxCNSnapshotBytes+1)));err==nil{
  t.Fatal("overlarge source reader accepted")
 }
}
func TestPinnedCNGeositeOnRealUDPAndTCPDNSLoopback(t *testing.T){
 raw:=pinnedRules(t)
 cn:=serveDNS(t,[4]byte{203,0,113,91})
 tunnel:=serveDNS(t,[4]byte{198,51,100,92})
 cn.truncate=true
 r,rules,err:=NewPinnedCNResolver(scopedDial(cn,tunnel),raw,true)
 if err!=nil||rules==nil{t.Fatal("verified CN resolver startup failed",err)}
 // Inject local DNS socket endpoints only for real host fixture, without
 // changing the production fixed ChinaDNS/TunnelDNS defaults.
 r.direct=cn.addr
 r.tunnel=tunnel.addr
 answer,err:=r.Resolve(context.Background(),makeQuery("www.baidu.com",0x1919),false)
 if err!=nil||lastIP(t,answer)!=cn.ip{t.Fatal("authentic baidu geosite not sent via CN",err)}
 if cn.udpCalls.Load()!=1||cn.tcpCalls.Load()!=1||
  tunnel.udpCalls.Load()!=0||tunnel.tcpCalls.Load()!=0{
  t.Fatal("CN DNS escaped same-path TCP fallback scope")
 }
 other,err:=r.Resolve(context.Background(),makeQuery("www.example.net",0x2020),false)
 if err!=nil||lastIP(t,other)!=tunnel.ip{t.Fatal("overseas QNAME not sent via tunnel",err)}
 bootstrap,err:=r.Resolve(context.Background(),makeQuery("wbd-bootstrap.example.net",0x3030),true)
 if err!=nil||lastIP(t,bootstrap)!=cn.ip{t.Fatal("original Go bootstrap must use physical",err)}
 if tunnel.udpCalls.Load()!=1||cn.udpCalls.Load()!=2||cn.tcpCalls.Load()!=2{
  t.Fatal("unexpected cross-upstream retry or bootstrap leakage")
 }
}

func TestB2bSignedAPKRuleColdFileRequires0600NoSymlinkAndPinnedHash(t *testing.T){
 raw:=pinnedRules(t)
 dir:=t.TempDir()
 name:=filepath.Join(dir,"wbd-cn-geosite.txt")
 if err:=os.WriteFile(name,raw,0600);err!=nil{t.Fatal(err)}
 verified,err:=ReadPinnedCNFile(name)
 if err!=nil||verified.Stats().Total!=PinnedCNRuleCount{
  t.Fatal("cannot load exact signed-style private copy",err)
 }
 if err:=os.Chmod(name,0644);err!=nil{t.Fatal(err)}
 if _,err=ReadPinnedCNFile(name);err==nil{
  t.Fatal("world-readable CN asset unexpectedly admitted")
 }
 if err:=os.Chmod(name,0600);err!=nil{t.Fatal(err)}
 link:=filepath.Join(dir,"symlink")
 if err:=os.Symlink(name,link);err!=nil{t.Fatal(err)}
 if _,err=ReadPinnedCNFile(link);err==nil{
  t.Fatal("signed CN asset symlink followed by root cold parser")
 }
 corrupt:=append([]byte(nil),raw...)
 corrupt[len(corrupt)/2]^=1
 if err:=os.WriteFile(name,corrupt,0600);err!=nil{t.Fatal(err)}
 if _,err=ReadPinnedCNFile(name);err==nil{
  t.Fatal("modified signed-style CN content accepted")
 }
 if _,err=ReadPinnedCNFile(dir);err==nil{
  t.Fatal("directory accepted instead of private CN asset")
 }
}
