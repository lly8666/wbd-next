//go:build windows && wbd_v4_embedded_go

package main
import("bytes";"crypto/sha256";"fmt";"net/http";"net/http/httptest";"net/netip";"os";"path/filepath";"testing")
func TestH2378EmbeddedGeolocationCNAndColdDefault(t *testing.T){
 rules,e:=m0Plan029BuiltinDomains();if e!=nil{t.Fatal(e)}
 for _,name:=range []string{"baidu.com","qq.com","taobao.com","jd.com"}{
  if !bytes.Contains(rules,[]byte("\n"+name+"\n"))&&!bytes.HasPrefix(rules,[]byte(name+"\n")){t.Fatal("missing actual upstream domain",name)}
 }
 canon,e:=m0Plan029CanonicalDomains([]byte("CN.Example.\n=Exact.Example\nkeyword:EXAMPLE\nregexp:^a[0-9]+\\.example$\n"))
 if e!=nil||string(canon)!="cn.example\n=exact.example\nkeyword:example\nregexp:^a[0-9]+\\.example$\n"{t.Fatal(string(canon),e)}
 o:=plan029Options("bypass-lan-cn");o.SplitEnable=true
 c,e:=m0Plan029TrialCold(o,netip.MustParseAddr("10.1.0.7"),14,netip.MustParseAddr("10.234.12.34"),1280,[16]byte{2})
 if e!=nil||c==nil||!bytes.Equal(c.Domains,rules)||c.PolicyFlags!=0{t.Fatal("offline default CN snapshot did not reach cold Rust input",e)}
 if path:=os.Getenv("WBD_H2378_CN_TEST_EXPORT");path!=""{if e=os.WriteFile(path,rules,0600);e!=nil{t.Fatal(e)}}
 t.Logf("H2378_EMBEDDED_CN_RULES count=%d bytes=%d sha256=%x",bytes.Count(rules,[]byte{'\n'}),len(rules),sha256.Sum256(rules))
}
func TestH2378ManualUpdateActualSnapshotAndFailurePreservesOld(t *testing.T){
 corrupt:=false
 server:=httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
  switch r.URL.Path{
  case "/latest":fmt.Fprint(w,`{"tag_name":"20261123144211"}`)
  case "/download/20261123144211/dlc.dat":w.Write(m0CNBuiltin)
  case "/download/20261123144211/dlc.dat.sha256sum":
   if corrupt{fmt.Fprint(w,"wrong")}else{fmt.Fprintf(w,"%x  dlc.dat",sha256.Sum256(m0CNBuiltin))}
  default:http.NotFound(w,r)
  }
 }))
 defer server.Close()
 path:=filepath.Join(t.TempDir(),"updated.txt")
 if e:=os.WriteFile(path,[]byte("old.example\n"),0600);e!=nil{t.Fatal(e)}
 rules,tag,e:=m0CNDownload(server.Client(),server.URL+"/latest",server.URL+"/download/")
 if e!=nil||tag!="20261123144211"{t.Fatal(tag,e)}
 if e=m0CNWriteAtomic(path,rules);e!=nil{t.Fatal(e)}
 old,e:=os.ReadFile(path);if e!=nil||!bytes.Equal(old,rules){t.Fatal("update did not replace",e)}
 corrupt=true
 if _,_,e=m0CNDownload(server.Client(),server.URL+"/latest",server.URL+"/download/");e==nil{t.Fatal("checksum mismatch accepted")}
 after,e:=os.ReadFile(path);if e!=nil||!bytes.Equal(after,old){t.Fatal("failed update replaced existing",e)}
}
