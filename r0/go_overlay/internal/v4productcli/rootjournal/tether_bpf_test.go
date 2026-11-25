package rootjournal
import("fmt";"os";"path/filepath";"testing")
func b117Hook(iface string,index int,upload bool,id uint32)TetherBPFHook{
 dir:="downstream";if upload{dir="upstream"}
 name:="prog_offload_schedcls_tether_"+dir+"4_ether:[*fsobj]"
 pin,_,_:=tetherBPFName(name)
 return TetherBPFHook{Interface:iface,Index:index,Handle:1,Info:3<<16|8,ProgramID:id,Name:name,Pin:pin}
}
func TestB117PauseRestore(t *testing.T){
 a,b:=b117Hook("ap0",5,true,55),b117Hook("rmnet0",6,false,66)
 live:=[]TetherBPFHook{a,b}
 k:=TetherBPFIO{Read:func()([]TetherBPFHook,error){return append([]TetherBPFHook(nil),live...),nil},
 PinID:func(p string)(uint32,error){if p==a.Pin{return 55,nil};if p==b.Pin{return 66,nil};return 0,fmt.Errorf("pin")},
 Current:func(TetherBPFHook)bool{return true},BootID:func()(string,error){return "boot",nil},
 Change:func(h TetherBPFHook,add bool)error{if add{live=append(live,h);return nil};for i,v:=range live{if v==h{live=append(live[:i],live[i+1:]...);return nil}};return fmt.Errorf("missing")}}
 path:=filepath.Join(t.TempDir(),"owned",tetherBPFJournal)
 s,e:=NewTetherBPFPause(k,path,"ap0");if e!=nil||s.Count()!=1||len(live)!=1||live[0]!=b{t.Fatalf("pause: %v",e)}
 if e=VerifyTetherBPFPause(k,path,"ap0");e!=nil{t.Fatal(e)}
 if e=s.Stop(true);e!=nil||len(live)!=2||live[0]!=b||live[1]!=a{t.Fatalf("restore: %v %v",e,live)}
 if _,e=os.Stat(path);!os.IsNotExist(e){t.Fatal("journal not cleared")}
 s,e=NewTetherBPFPause(k,path,"ap0");if e!=nil{t.Fatal(e)}
 if e=s.Stop(false);e==nil||len(live)!=1||live[0]!=b{t.Fatal("restored too early")}
 if e=RecoverTetherBPF(k,path);e!=nil||len(live)!=2{t.Fatalf("restore: %v",e)}
}
