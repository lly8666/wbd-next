//go:build windows && wbd_v4_embedded_go
package main

// PLAN029: original Go cold CN/LAN/direct4/DNS snapshot for Rust V3 trial.
// Never per-DATA Go dispatch or Windows route-per-CIDR installation.
import (
 "crypto/sha256"
 "errors"
 "fmt"
 "net/netip"
 "os"
 "path/filepath"
 "strings"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
 "github.com/lly8666/wobuzhidao/internal/splitroute"
 "golang.org/x/net/idna"
)
var errM0Plan029Cold=errors.New("plan029: cold split source rejected")
const m0Plan029MaxPrefixRows=32768
func m0Plan029Rows(pp []netip.Prefix)([]realityfront.V4WindowsColdCIDR,error){
 if len(pp)>m0Plan029MaxPrefixRows{return nil,errM0Plan029Cold}
 out:=make([]realityfront.V4WindowsColdCIDR,0,len(pp))
 for _,p:=range pp{
  if !p.IsValid()||!p.Addr().Is4()||p.Bits()<0||p.Bits()>32{return nil,errM0Plan029Cold}
  out=append(out,realityfront.V4WindowsColdCIDR{
   Network:p.Masked().Addr().As4(),Bits:uint8(p.Bits())})
 }
 return out,nil
}
// Until the full pinned v2fly geolocation-cn include/attribute and RE2
// compiler exists, reject unsupported directives rather than silently
// turning keyword/regexp into suffix matches. No decrypted DoH/SNI.
func m0Plan029CanonicalDomains(input []byte)([]byte,error){
 if len(input)>1<<20{return nil,errM0Plan029Cold}
 var result strings.Builder
 for _,line:=range strings.Split(string(input),"\n"){
  s:=strings.TrimSpace(line)
  if s==""{continue}
  if strings.ContainsAny(s," \t\r")||strings.HasPrefix(s,"#")||
   strings.HasPrefix(s,"include:")||strings.HasPrefix(s,"keyword:")||
   strings.HasPrefix(s,"regexp:")||strings.ContainsAny(s,"@&"){
   return nil,fmt.Errorf("%w: unsupported geosite directive",errM0Plan029Cold)
  }
  exact:=strings.HasPrefix(s,"=");if exact{s=strings.TrimPrefix(s,"=")}
  s=strings.TrimSuffix(s,".")
  a,e:=idna.Lookup.ToASCII(s)
  if e!=nil{return nil,errM0Plan029Cold}
  a=strings.ToLower(a)
  if len(a)==0||len(a)>253{return nil,errM0Plan029Cold}
  for _,label:=range strings.Split(a,"."){
   if len(label)==0||len(label)>63||label[0]=='-'||label[len(label)-1]=='-'{return nil,errM0Plan029Cold}
   for _,r:=range label{
    if !(r>='a'&&r<='z')&&!(r>='0'&&r<='9')&&r!='-'{return nil,errM0Plan029Cold}
   }
  }
  if exact{result.WriteByte('=')}
  result.WriteString(a);result.WriteByte('\n')
  if result.Len()>1<<20{return nil,errM0Plan029Cold}
 }
 return []byte(result.String()),nil
}
func m0Plan029ColdSource(o m0NativeV4Options,physical netip.Addr,
 physicalIndex uint32,lease netip.Addr,innerMTU uint32,domainRules []byte,
)(realityfront.V4WindowsColdSplitConfig,error){
 var empty realityfront.V4WindowsColdSplitConfig
 if !physical.Is4()||physical.IsUnspecified()||physical.IsLoopback()||
  physicalIndex==0||!lease.Is4()||lease.IsUnspecified()||
  innerMTU<576||innerMTU>1500||len(o.DNSServers4)!=1||
  !o.DirectDNS4.Is4()||!o.DNSServers4[0].Is4()||
  o.DirectDNS4.IsMulticast()||o.DNSServers4[0].IsMulticast()||
  o.DirectDNS4.IsUnspecified()||o.DNSServers4[0].IsUnspecified()||
  o.DirectDNS4==netip.AddrFrom4([4]byte{255,255,255,255})||
  o.DNSServers4[0]==netip.AddrFrom4([4]byte{255,255,255,255}){
  return empty,errM0Plan029Cold
 }
 directHard:=o.DirectFlowHard
 if directHard==0{directHard=16384}
 if directHard>16384{return empty,errM0Plan029Cold}
 var mode uint32
 switch o.RouteMode{
 case "all":mode=0
 case "bypass-lan":mode=1
 case "bypass-lan-cn":mode=2
 default:return empty,errM0Plan029Cold
 }
 var lan,cn []netip.Prefix
 if mode!=0{
  p,e:=splitroute.Direct("bypass-lan","");if e!=nil{return empty,e}
  lan=p
  if mode==2{
   // H1946 signed P1 B1 proved compact OS Bypass4 has only 8 LAN
   // rows despite --china-ip-file's 4096 distinct /32 CN entries.
   // Rust's canonical cold CN snapshot must parse its own configured
   // source, not inherit the OS compact route/exclusion representation.
   // Single cold parse; an invalid custom source fails closed.
   cn,e=splitroute.Direct("bypass-lan-cn",o.ChinaIPFile)
   if e!=nil{return empty,e}
  }
 }
 cnRows,e:=m0Plan029Rows(cn);if e!=nil{return empty,e}
 lanRows,e:=m0Plan029Rows(lan);if e!=nil{return empty,e}
 var directRows []realityfront.V4WindowsColdCIDR
 if mode!=0 {
  directRows,e=m0Plan029Rows(o.Direct4);if e!=nil{return empty,e}
 } // All/split-off has no business Direct table, even the custom list.
 var domains []byte
 var journalPath []byte
 if mode==2&&o.CNDomainDirect&&o.StatePath!=""{
  if !filepath.IsAbs(o.StatePath){return empty,errM0Plan029Cold}
  journalPath=[]byte(o.StatePath+".n4-fakeip-journal")
  if len(journalPath)>4096{return empty,errM0Plan029Cold}
 }
 if mode==2{
  domains,e=m0Plan029CanonicalDomains(domainRules)
  if e!=nil{return empty,e}
 }
 var policyFlags uint32
 if mode==2&&o.CNDomainDirect{policyFlags=1}
 return realityfront.V4WindowsColdSplitConfig{
  RouteMode:mode,PolicyFlags:policyFlags,PhysicalIfIndex:physicalIndex,
  PhysicalSource:physical.As4(),Lease4:lease.As4(),
  DirectDNS:o.DirectDNS4.As4(),TunnelDNS:o.DNSServers4[0].As4(),
  FakeStart:[4]byte{198,18,0,1},FakeEnd:[4]byte{198,18,255,254},
  InnerMTU:innerMTU,DirectHard:directHard,
  StartupPaddingMode:o.StartupPaddingMode,
  CN:cnRows,LAN:lanRows,Direct:directRows,Domains:domains,
  FakeJournalPath:journalPath,
 },nil
}

// Cold-only per-original-generation synthetic /32, disjoint from
// selective FakeIP 198.18/16. No fixed test address.
func m0Plan029SyntheticForGeneration(install,epoch [16]byte)([4]byte,error){
 if install==[16]byte{}||epoch==[16]byte{}{
  return [4]byte{},errM0Plan029Cold
 }
 var input [32]byte
 copy(input[:16],install[:])
 copy(input[16:],epoch[:])
 h:=sha256.Sum256(input[:])
 return [4]byte{198,19,h[0],1+h[1]%254},nil
}

// 029B: original Rust V3 owns public DNS/IPv6/padding even with business
// split disabled. Only Direct/FakeIP resources are optional per generation.
// The old source-locked signed advanced-CN CI trial remains a separate
// explicit test input. No V2/Go packet-loop fallback is permitted.
func m0Plan029TrialCold(o m0NativeV4Options,physical netip.Addr,
 ifindex uint32,lease netip.Addr,innerMTU uint32,epoch [16]byte,
)(*realityfront.V4WindowsColdSplitConfig,error){
 trial:=os.Getenv("GITHUB_ACTIONS")=="true"&&
  os.Getenv("WBD_PLAN029_NATIVE_V3_TRIAL")=="1"
 effective:=o
 if !o.SplitEnable&&!trial{
  effective.RouteMode="all" // never even parse disabled CN/Direct rules
  effective.CNDomainDirect=false
 }
 if trial&&!o.SplitEnable{
  // The original source-locked 029 test is an explicit old-CN semantic
  // opt-in; new user profiles without a saved advanced key remain false.
  effective.CNDomainDirect=true
 }
 var domains []byte
 if effective.RouteMode=="bypass-lan-cn"{
  file:=effective.CNRulesFile
  if !o.SplitEnable{file=os.Getenv("WBD_PLAN029_CN_RULES_FILE")}
  if file==""||!filepath.IsAbs(file){return nil,errM0Plan029Cold}
  info,e:=os.Lstat(file)
  if e!=nil||info.Mode()&os.ModeSymlink!=0||
   !info.Mode().IsRegular()||info.Size()==0||info.Size()>1<<20{
   return nil,errM0Plan029Cold
  }
  domains,e=os.ReadFile(file);if e!=nil{return nil,e}
 }
 c,e:=m0Plan029ColdSource(effective,physical,ifindex,lease,innerMTU,domains)
 if e!=nil{return nil,e}
 if effective.RouteMode=="bypass-lan-cn"&&
  (len(c.Domains)==0||
   (effective.CNDomainDirect&&len(c.FakeJournalPath)==0)){
  return nil,errM0Plan029Cold
 }
 // All/off still needs ONE post-OS DNS-only TCP53 listener; the distinct
 // Rust business Direct TCP NAT table is NOT created in route-mode All.
 // This generation-owned synthetic /32 exists solely for its DNS TCP
 // return/Defender lease, with the original bounded Rust TX/Stop owner.
 synth,e:=m0Plan029SyntheticForGeneration(o.Installation,epoch)
 if e!=nil{return nil,e}
 c.TCPSynthetic4=synth
 return &c,nil
}
