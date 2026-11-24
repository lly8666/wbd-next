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
