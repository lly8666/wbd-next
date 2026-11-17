package dnsnative

// CN rules are DNS-QNAME classification only. They never alter the real A
// address, do not implement FakeIP or match per-IP data-plane packets.
// Build provenance: v2fly/domain-list-community geolocation-cn, pinned by
// the legacy deterministic importer and the exact output SHA below.
import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "errors"
 "fmt"
 "io"
 "os"
 "syscall"
 "regexp"
 "strings"
)

const (
 PinnedCNSourceCommit = "41504eae2a11f305fe88cfc605cf6c105a80bf5a"
 PinnedCNSHA256 = "45496d28e7a90472274fdf6c23afd43a0e478f9127dea241b628ca730863b1d6"
 PinnedCNRuleCount = 8503
 MaxCNSnapshotBytes = 6000000
)

type CNRules struct {
 suffix map[string]struct{}
 exact map[string]struct{}
 keywords []string
 regex []*regexp.Regexp
 total int
 digest string
}
type CNStats struct{
 Total int
 Domain int
 Full int
 Keyword int
 Regex int
 SHA256 string
}
func validDNSName(s string)bool{
 if s==""||len(s)>253||strings.HasSuffix(s,"."){return false}
 for _,label:=range strings.Split(s,"."){
  if label==""||len(label)>63||label[0]=='-'||label[len(label)-1]=='-'{return false}
  for _,b:=range []byte(label){
   if !((b>='a'&&b<='z')||(b>='0'&&b<='9')||b=='-'){return false}
  }
 }
 return true
}
func validKeyword(s string)bool{
 if s==""||len(s)>512{return false}
 for _,b:=range []byte(s){
  if !((b>='a'&&b<='z')||(b>='0'&&b<='9')||b=='-'||b=='.'){return false}
 }
 return true
}
// LoadPinnedCN explicitly requires the authentic importer-produced bytes.
// Every include/@attribute/affiliation has already been resolved by the
// source-pinned Python importer. Regex rules are compiled, not downgraded
// into suffixes or silently ignored. This function never downloads data.
func LoadPinnedCN(raw []byte)(*CNRules,error){
 if len(raw)<=10000||len(raw)>=MaxCNSnapshotBytes{return nil,fmt.Errorf("CN rules size invalid")}
 expected,_:=hex.DecodeString(PinnedCNSHA256)
 sum:=sha256.Sum256(raw)
 if !bytes.Equal(sum[:],expected){return nil,fmt.Errorf("CN geosite SHA256 mismatch: fail closed")}
 if raw[len(raw)-1]!='\n'{return nil,fmt.Errorf("CN rules missing final newline")}
 r:=&CNRules{suffix:make(map[string]struct{}),exact:make(map[string]struct{}),digest:PinnedCNSHA256}
 var previous string
 for _,line:=range strings.Split(string(raw[:len(raw)-1]),"\n"){
  if line==""||len(line)>530||line<=previous{return nil,fmt.Errorf("CN rules empty, unordered or duplicated")}
  previous=line
  colon:=strings.IndexByte(line,':')
  if colon<1||colon>=len(line)-1{return nil,fmt.Errorf("CN rule missing type/value")}
  kind,value:=line[:colon],line[colon+1:]
  if len(value)>512{return nil,fmt.Errorf("CN rule too long")}
  r.total++
  if r.total>150000{return nil,fmt.Errorf("CN rule count exceeds cap")}
  switch kind{
  case "domain","full":
   if !validDNSName(value){return nil,fmt.Errorf("invalid CN domain rule")}
   if kind=="domain"{r.suffix[value]=struct{}{}}else{r.exact[value]=struct{}{}}
  case "keyword":
   if !validKeyword(value){return nil,fmt.Errorf("invalid CN keyword")}
   r.keywords=append(r.keywords,value)
  case "regexp":
   if len(r.regex)>=2048{return nil,fmt.Errorf("too many regex rules")}
   re,err:=regexp.Compile("(?i)"+value)
   if err!=nil{return nil,fmt.Errorf("unsupported geosite regexp: %w",err)}
   r.regex=append(r.regex,re)
  default:return nil,fmt.Errorf("unknown CN rule type %q",kind)
  }
 }
 if r.total!=PinnedCNRuleCount||len(r.suffix)!=8431||
  len(r.exact)!=69||len(r.regex)!=3||len(r.keywords)!=0{
  return nil,fmt.Errorf("CN geosite type/count differs from pinned source")
 }
 return r,nil
}
func (r *CNRules) Stats() CNStats{
 if r==nil{return CNStats{}}
 return CNStats{Total:r.total,Domain:len(r.suffix),Full:len(r.exact),
  Keyword:len(r.keywords),Regex:len(r.regex),SHA256:r.digest}
}
// Match accepts normalized ASCII DNS names only. Labels are exact for
// 'domain' suffixes: mynotbaidu.com cannot match baidu.com. CNAME targets
// never retroactively change the original query's path.
func (r *CNRules) Match(name string) bool {
 if r==nil{return false}
 name=strings.ToLower(strings.TrimSuffix(name,"."))
 if !validDNSName(name){return false}
 if _,yes:=r.exact[name];yes{return true}
 for suffix:=name;suffix!="";{
  if _,yes:=r.suffix[suffix];yes{return true}
  dot:=strings.IndexByte(suffix,'.')
  if dot<0{break}
  suffix=suffix[dot+1:]
 }
 for _,word:=range r.keywords{if strings.Contains(name,word){return true}}
 for _,re:=range r.regex{if re.MatchString(name){return true}}
 return false
}
// NewPinnedCNResolver makes split mode refuse startup when the *actual*
// pinned rules cannot be read and verified, instead of secretly routing
// every CN query to tunnel or to an arbitrary fallback DNS endpoint.
func NewPinnedCNResolver(dial DialFunc, raw []byte, split bool)(*Resolver,*CNRules,error){
 rules,err:=LoadPinnedCN(raw)
 if err!=nil{return nil,nil,err}
 resolver,err:=New(dial,rules.Match,split)
 if err!=nil{return nil,nil,err}
 return resolver,rules,nil
}
// ReadPinnedCN is bounded even when the caller supplies a pipe or procfs
// pseudo-file with unknown length; the caller controls the exact path.
func ReadPinnedCN(reader io.Reader)(*CNRules,error){
 if reader==nil{return nil,errors.New("missing CN geosite source")}
 raw,err:=io.ReadAll(io.LimitReader(reader,MaxCNSnapshotBytes+1))
 if err!=nil{return nil,err}
 return LoadPinnedCN(raw)
}

// ReadPinnedCNFile loads one Android App-private, owner-only file from
// the same O_NOFOLLOW fd whose actual bytes receive the upstream hash
// check. No global resolver, path traversal or silent substitute source.
// Files are copied from the signed APK by the ordinary Android App,
// then opened by the original native Root Go cold-control process.
func ReadPinnedCNFile(path string)(*CNRules,error){
 if path==""{return nil,errors.New("missing pinned CN rule path")}
 fd,err:=syscall.Open(path,syscall.O_RDONLY|syscall.O_CLOEXEC|
  syscall.O_NOFOLLOW|syscall.O_NONBLOCK,0)
 if err!=nil{return nil,err}
 f:=os.NewFile(uintptr(fd),"pinned-cn-geosite")
 defer f.Close()
 st,err:=f.Stat()
 if err!=nil{return nil,err}
 if !st.Mode().IsRegular()||st.Mode().Perm()!=0600||
  st.Size()<=10000||st.Size()>=MaxCNSnapshotBytes{
  return nil,errors.New("pinned CN source must be a bounded private 0600 regular file")
 }
 return ReadPinnedCN(f)
}
