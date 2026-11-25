//go:build android && (arm64 || amd64)

package rootjournal
import("net";"os";"os/exec";"path/filepath";"testing";"time")
func TestB117AndroidKernelTetherBPFPause(t *testing.T){
 if os.Getenv("WBD_B117_KERNEL")!="1"{t.Skip("guest-only")}
 if os.Geteuid()!=0{t.Fatal("root required")}
 run:=func(name string,args ...string){t.Helper();if b,e:=exec.Command(name,args...).CombinedOutput();e!=nil{t.Fatalf("%s %v: %v %s",name,args,e,b)}}
 a,b:="wbd117a","wbd117b"
 run("ip","link","add",a,"type","veth","peer","name",b)
 defer exec.Command("ip","link","del",a).Run()
 for _,i:=range []string{a,b}{run("ip","link","set",i,"up");run("tc","qdisc","add","dev",i,"clsact")}
 k:=androidTetherBPFIO(map[string]bool{a:true,b:true})
 makeHook:=func(name string,upload bool)TetherBPFHook{
  i,e:=net.InterfaceByName(name);if e!=nil{t.Fatal(e)}
  h:=b117Hook(name,i.Index,upload,1)
  h.ProgramID,e=k.PinID(h.Pin);if e!=nil{t.Fatalf("actual Android tethering pin unavailable: %v",e)}
  if e=k.Change(h,true);e!=nil{t.Fatalf("initial actual AOSP attach: %v",e)}
  return h
 }
 first,second:=makeHook(a,true),makeHook(b,false)
 path:=filepath.Join(t.TempDir(),"owned",tetherBPFJournal)
 owner,e:=NewTetherBPFPause(k,path,a);if e!=nil{t.Fatalf("live detach: %v",e)}
 defer owner.Stop(true)
 if owner.Count()!=1{t.Fatal("only selected downstream upload hook should be paused")}
 remaining,e:=k.Read();if e!=nil||len(remaining)!=1||remaining[0]!=second{t.Fatalf("unrelated hook changed: %v %v",e,remaining)}
 if e=VerifyTetherBPFPause(k,path,a);e!=nil{t.Fatal(e)}
 t.Log("B117_ANDROID_REAL_TETHER_PROGRAMS_DETACHED")
 changed:=make(chan struct{},1)
 watchStop,e:=WatchTetherBPFPause(k,path,a,func(){changed<-struct{}{}});if e!=nil{t.Fatal(e)}
 defer watchStop()
 if e=k.Change(first,true);e!=nil{t.Fatal(e)}
 select{case <-changed:case <-time.After(5*time.Second):t.Fatal("no actual tether reattach notification")}
 watchStop()
 t.Log("B117_ANDROID_REAL_TETHER_REATTACH_EVENT")
 if e=owner.Stop(true);e!=nil{t.Fatal(e)}
 got,e:=k.Read();if e!=nil||len(got)!=2{t.Fatalf("readback: %v %v",e,got)}
 seen:=map[TetherBPFHook]bool{};for _,h:=range got{seen[h]=true}
 if !seen[first]||!seen[second]{t.Fatal("original exact program IDs/attachments not restored")}
 t.Log("B117_ANDROID_REAL_TETHER_PROGRAMS_RESTORED")
}
