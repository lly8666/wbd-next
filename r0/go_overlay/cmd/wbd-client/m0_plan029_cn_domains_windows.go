//go:build windows

package main

import (
 "bytes"
 "crypto/sha256"
 _ "embed"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net/http"
 "os"
 "path/filepath"
 "regexp"
 "strings"
 "time"
 "unicode/utf8"

 "golang.org/x/net/idna"
)

// The source-locked assembler embeds only the official geolocation-cn
// GeoSite protobuf entry, not the whole geosite database. Offline at runtime.
//go:embed cn_domains_builtin.dat
var m0CNBuiltin []byte

const m0CNMaxRuleBytes=4<<20
const m0CNMaxRules=100000
const m0CNMaxDownload=16<<20
const m0CNLatest="https://api.github.com/repos/v2fly/domain-list-community/releases/latest"
const m0CNReleaseBase="https://github.com/v2fly/domain-list-community/releases/download/"
var errM0CNRules=errors.New("invalid China domain snapshot")

// Native DNS queries use the Rust trie (suffix/exact), keyword and compiled
// regex; this cold normalizer never converts a non-suffix rule into a suffix.
func m0Plan029CanonicalDomains(input []byte)([]byte,error){
 if len(input)>m0CNMaxRuleBytes||!utf8.Valid(input){return nil,errM0CNRules}
 var result strings.Builder
 seen:=make(map[string]struct{})
 for _,line:=range strings.Split(string(input),"\n"){
  s:=strings.TrimSpace(line)
  if s==""{continue}
  if strings.HasPrefix(s,"#")||strings.HasPrefix(s,"include:")||strings.ContainsAny(s,"\r\n\t "){return nil,errM0CNRules}
  var canonical string
  switch {
  case strings.HasPrefix(s,"regexp:"):
   pattern:=strings.TrimPrefix(s,"regexp:")
   if pattern==""{return nil,errM0CNRules}
   if _,err:=regexp.Compile(pattern);err!=nil{return nil,err}
   canonical="regexp:"+pattern
  case strings.HasPrefix(s,"keyword:"):
   keyword:=strings.TrimPrefix(s,"keyword:")
   if keyword==""||strings.ContainsAny(keyword,"@&"){return nil,errM0CNRules}
   for _,r:=range keyword{if r>127{return nil,errM0CNRules}}
   canonical="keyword:"+strings.ToLower(keyword)
  default:
   if strings.ContainsAny(s,"@&:"){return nil,errM0CNRules}
   exact:=strings.HasPrefix(s,"=");if exact{s=strings.TrimPrefix(s,"=")}
   s=strings.TrimSuffix(s,".")
   a,e:=idna.Lookup.ToASCII(s);if e!=nil{return nil,e}
   a=strings.ToLower(a)
   if len(a)==0||len(a)>253{return nil,errM0CNRules}
   for _,label:=range strings.Split(a,"."){
    if len(label)==0||len(label)>63||label[0]=='-'||label[len(label)-1]=='-'{return nil,errM0CNRules}
    for _,r:=range label{if !(r>='a'&&r<='z')&&!(r>='0'&&r<='9')&&r!='-'{return nil,errM0CNRules}}
   }
   canonical=a;if exact{canonical="="+a}
  }
  if _,ok:=seen[canonical];ok{continue}
  seen[canonical]=struct{}{}
  result.WriteString(canonical);result.WriteByte('\n')
  if result.Len()>m0CNMaxRuleBytes||len(seen)>m0CNMaxRules{return nil,errM0CNRules}
 }
 return []byte(result.String()),nil
}

// routercommon.GeoSiteList/GeoSite/Domain protobuf, no new Go dependency.
// Official entries use varint and length-delimited fields; skip attributes
// as geolocation-cn is the unfiltered, already-expanded upstream group.
type m0CNField struct{number uint64; wire uint64; value uint64; data []byte}
func m0CNFields(data []byte, visit func(m0CNField) error) error {
 for len(data)>0{
  tag,n:=binary.Uvarint(data);if n<=0||tag>>3==0{return errM0CNRules};data=data[n:]
  f:=m0CNField{number:tag>>3,wire:tag&7}
  switch f.wire{
  case 0:
   v,k:=binary.Uvarint(data);if k<=0{return errM0CNRules};f.value=v;data=data[k:]
  case 2:
   size,k:=binary.Uvarint(data);if k<=0{return errM0CNRules};data=data[k:]
   if size>uint64(len(data)){return errM0CNRules};f.data=data[:int(size)];data=data[int(size):]
  default:return errM0CNRules
  }
  if err:=visit(f);err!=nil{return err}
 }
 return nil
}
func m0CNExtract(data []byte)([]byte,error){
 var selected []byte
 err:=m0CNFields(data,func(f m0CNField)error{
  if f.number!=1||f.wire!=2{return nil}
  var name string
  if e:=m0CNFields(f.data,func(v m0CNField)error{if v.number==1&&v.wire==2{name=string(v.data)};return nil});e!=nil{return e}
  if strings.EqualFold(name,"geolocation-cn"){
   if selected!=nil{return errM0CNRules};selected=f.data
  }
  return nil
 })
 if err!=nil||selected==nil{return nil,errM0CNRules}
 var raw strings.Builder
 err=m0CNFields(selected,func(f m0CNField)error{
  if f.number!=2||f.wire!=2{return nil}
  var kind uint64
  var value string
  if e:=m0CNFields(f.data,func(v m0CNField)error{
   if v.number==1&&v.wire==0{kind=v.value}
   if v.number==2&&v.wire==2{value=string(v.data)}
   return nil
  });e!=nil{return e}
  if value==""||strings.ContainsAny(value,"\r\n"){return errM0CNRules}
  switch kind{
  case 0:raw.WriteString("keyword:")
  case 1:raw.WriteString("regexp:")
  case 2:
  case 3:raw.WriteByte('=')
  default:return errM0CNRules
  }
  raw.WriteString(value);raw.WriteByte('\n')
  if raw.Len()>m0CNMaxRuleBytes{return errM0CNRules}
  return nil
 })
 if err!=nil{return nil,err}
 result,err:=m0Plan029CanonicalDomains([]byte(raw.String()))
 if err!=nil{return nil,err}
 if len(result)==0{return nil,errM0CNRules}
 return result,nil
}
func m0Plan029BuiltinDomains()([]byte,error){
 rules,err:=m0CNExtract(m0CNBuiltin)
 if err!=nil{return nil,err}
 if bytes.Count(rules,[]byte{'\n'})<1000{return nil,errM0CNRules}
 return rules,nil
}
func m0CNGet(c *http.Client,url string,limit int64)([]byte,error){
 req,e:=http.NewRequest(http.MethodGet,url,nil);if e!=nil{return nil,e}
 req.Header.Set("User-Agent","WBD-CN-domain-update")
 resp,e:=c.Do(req);if e!=nil{return nil,e};defer resp.Body.Close()
 if resp.StatusCode!=http.StatusOK{return nil,fmt.Errorf("HTTP %d",resp.StatusCode)}
 data,e:=io.ReadAll(io.LimitReader(resp.Body,limit+1));if e!=nil{return nil,e}
 if int64(len(data))>limit{return nil,errM0CNRules}
 return data,nil
}
func m0CNDownload(c *http.Client,latest,base string)([]byte,string,error){
 meta,e:=m0CNGet(c,latest,1<<20);if e!=nil{return nil,"",e}
 var release struct{Tag string `json:"tag_name"`}
 if e=json.Unmarshal(meta,&release);e!=nil{return nil,"",e}
 if len(release.Tag)!=14||strings.IndexFunc(release.Tag,func(r rune)bool{return r<'0'||r>'9'})>=0{return nil,"",errM0CNRules}
 prefix:=base+release.Tag+"/"
 dat,e:=m0CNGet(c,prefix+"dlc.dat",m0CNMaxDownload);if e!=nil{return nil,"",e}
 sum,e:=m0CNGet(c,prefix+"dlc.dat.sha256sum",4096);if e!=nil{return nil,"",e}
 fields:=strings.Fields(string(sum));hash:=sha256.Sum256(dat)
 if len(fields)==0||!strings.EqualFold(fields[0],hex.EncodeToString(hash[:])){return nil,"",errors.New("China domain upstream checksum mismatch")}
 rules,e:=m0CNExtract(dat);if e!=nil{return nil,"",e}
 if bytes.Count(rules,[]byte{'\n'})<1000{return nil,"",errM0CNRules}
 return rules,release.Tag,nil
}
func m0CNWriteAtomic(target string,rules []byte)error{
 if !filepath.IsAbs(target){return errM0CNRules}
 if e:=os.MkdirAll(filepath.Dir(target),0700);e!=nil{return e}
 f,e:=os.CreateTemp(filepath.Dir(target),".cn-domains-*.tmp");if e!=nil{return e}
 name:=f.Name();defer os.Remove(name)
 _,e=f.Write(rules)
 if e==nil{e=f.Sync()}
 if closeErr:=f.Close();e==nil{e=closeErr}
 if e!=nil{return e}
 return os.Rename(name,target)
}
func m0Plan029DomainCommand(args []string)bool{
 if len(args)==0||args[0]!="--update-cn-domains"{return false}
 if len(args)!=2{fmt.Fprintln(os.Stderr,"--update-cn-domains requires an absolute output path");os.Exit(2)}
 rules,tag,e:=m0CNDownload(&http.Client{Timeout:40*time.Second},m0CNLatest,m0CNReleaseBase)
 if e==nil{e=m0CNWriteAtomic(args[1],rules)}
 if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
 fmt.Printf("CN_DOMAIN_UPDATE upstream=%s rules=%d sha256=%x reconnect_required=1\n",tag,bytes.Count(rules,[]byte{'\n'}),sha256.Sum256(rules))
 return true
}
