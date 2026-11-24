//go:build linux && cgo && wbd_v4_embedded_go
package v4productcli
import(
 "context"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
 "time"

 "github.com/lly8666/wobuzhidao/internal/realityfront"
)
func TestPLAN030ConfigReusesServerParser(t *testing.T){
 dir:=t.TempDir()
 c:=defaultManagedConfig()
 c.ServerName="wbd.example.test"
 c.RouteKeyFile=filepath.Join(dir,"route.hex")
 c.TLSCert=filepath.Join(dir,"cert.pem")
 c.TLSKey=filepath.Join(dir,"key.pem")
 c.RawInterface="lo"
 c.Users=[]managedUser{{"one","password"}}
 if e:=managedMaterial(c);e!=nil{t.Fatal(e)}
 path:=filepath.Join(dir,"server.json")
 if e:=saveManagedConfig(path,c);e!=nil{t.Fatal(e)}
 before,e:=os.ReadFile(c.RouteKeyFile);if e!=nil{t.Fatal(e)}
 if e=saveManagedConfig(path,c);e!=nil{t.Fatal(e)}
 after,e:=os.ReadFile(c.RouteKeyFile);if e!=nil||string(before)!=string(after){t.Fatal("route key reset",e)}
 args,clean,e:=managedArgs(c);if e!=nil{t.Fatal(e)};defer clean()
 if strings.Contains(strings.Join(args," "),"password"){t.Fatal("password in argv")}
 cfg,e:=parse("server",args);if e!=nil{t.Fatal(e)}
 if !cfg.mixedModes||cfg.outerMTU!=1460||cfg.users["one"]!="password"||!cfg.leasePool.IsValid(){t.Fatal("original parser semantics lost")}
 c.Listen="0.0.0.0:99999";if e=saveManagedConfig(path,c);e==nil{t.Fatal("invalid port accepted")}
 stored,_,e:=loadManagedConfig(path);if e!=nil||stored.Listen!="0.0.0.0:443"{t.Fatal("invalid config replaced valid file",e)}
}
func TestPLAN030OnDemandSnapshotSocket(t *testing.T){
 ctx,cancel:=context.WithCancel(context.Background())
 m:=&serverManagement{path:filepath.Join(t.TempDir(),"clients.sock"),revision:"revision"}
 if e:=m.listen(ctx);e!=nil{t.Fatal(e)}
 defer func(){cancel();m.close()}()
 select{case <-m.requests:t.Fatal("snapshot without reader");case <-time.After(20*time.Millisecond):}
 result:=make(chan managementSnapshot,1)
 go func(){s,e:=readManagedSnapshot(m.path);if e!=nil{result<-managementSnapshot{State:e.Error()};return};result<-s}()
 select{
 case reply:=<-m.requests:reply<-managementSnapshot{State:"ready",ConfigRevision:"revision",Clients:[]managedClient{}}
 case <-time.After(time.Second):t.Fatal("request missing")
 }
 select{
 case s:=<-result:
  if s.State!="ready"||s.ConfigRevision!="revision"{t.Fatal(s)}
  b,_:=json.Marshal(s);if !strings.Contains(string(b),"\"clients\":[]"){t.Fatal(string(b))}
 case <-time.After(time.Second):t.Fatal("response missing")
 }
}

func TestPLAN030WatchCountersAndNegotiatedBudget(t *testing.T){
 a,b:=uint64(20),uint64(30)
 if v:=managedCounterRate(&a,&b,2);v==nil||*v!=5{t.Fatal(v)}
 if managedCounterRate(&b,&a,2)!=nil||managedCounterRate(nil,&a,2)!=nil{t.Fatal("counter reset not unknown")}
 r:=managedClient{Lanes:4,FEC:"fixed",ClientRecordLimit:1360,ServerRecordLimit:1420}
 r.applyNegotiatedBudget()
 if r.NegotiatedInnerCap==nil||*r.NegotiatedInnerCap!=1298{t.Fatalf("expected canonical Game FEC budget: %+v",r)}
 if r.ClientOuterSetting!=nil||r.ClientOSInnerMTU!=nil{t.Fatal("guessed remote MTU")}
 normal:=managedClient{Lanes:1}
 normal.applyIdentity(realityfront.ManagementSessionIdentity{NormalFECOff:true,ClientRecordLimit:1420,ServerRecordLimit:1420})
 normal.applyNegotiatedBudget()
 if normal.FEC!="off"||normal.NegotiatedInnerCap==nil||*normal.NegotiatedInnerCap!=1389{t.Fatalf("authenticated Normal/off budget missing: %+v",normal)}
 if normal.ClientOSInnerMTU!=nil{t.Fatal("guessed remote OS MTU")}
}

func TestPLAN030ManualAccountLeaseUsesOriginalParser(t *testing.T){
 dir:=t.TempDir();c:=defaultManagedConfig()
 c.ServerName="wbd.example.test";c.RawInterface="lo"
 c.TunIPv4="10.66.0.1/24";c.LeasePool="10.66.0.128/25"
 c.RouteKeyFile=filepath.Join(dir,"route.hex");c.TLSCert=filepath.Join(dir,"cert.pem");c.TLSKey=filepath.Join(dir,"key.pem")
 c.Users=[]managedUser{{"one","password"}}
 c.ManualClientLeases=map[string]string{"one":"10.66.0.2/32"}
 c.PeerPersona="windows11"
 if e:=managedMaterial(c);e!=nil{t.Fatal(e)}
 args,clean,e:=managedArgs(c);if e!=nil{t.Fatal(e)};defer clean()
 cfg,e:=parse("server",args);if e!=nil{t.Fatal(e)}
 if cfg.manualClientLeases4["one"]!="10.66.0.2/32"||!cfg.mixedModes{t.Fatal("manual account not routed through original parser")}
}
