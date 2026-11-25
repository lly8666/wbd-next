package rootjournal

import (
 "fmt"
 "os"
 "path/filepath"
 "testing"
)
func TestB116HardwareOffloadSessionAndRestore(t *testing.T){
 for _,initial:=range []string{"0","null","1"}{
  t.Run(initial,func(t *testing.T){
   path:=filepath.Join(t.TempDir(),"owned",tetherOffloadJournal)
   value:=initial;writes:=0
   run:=func(a ...string)(string,error){
    if len(a)<3||a[1]!="global"||a[2]!=tetherOffloadKey{return "",fmt.Errorf("unexpected setting")}
    switch a[0]{
     case "get":return value+"\n",nil
     case "put":writes++;value=a[3];return "",nil
     case "delete":writes++;value="null";return "",nil
    };return "",fmt.Errorf("unexpected command")
   }
   owner,e:=NewTetherOffload(run,path,true);if e!=nil||value!="1"{t.Fatalf("start: %v value=%s",e,value)}
   if owner.Changed()!=(initial!="1"){t.Fatal("incorrect ownership")}
   if e=owner.Stop(true);e!=nil||value!=initial{t.Fatalf("stop: %v value=%s",e,value)}
   if initial=="1"&&writes!=0{t.Fatal("changed manually disabled setting")}
   if initial!="1"&&writes!=2{t.Fatal("missing exact disable/restore")}
   if _,e=os.Stat(path);!os.IsNotExist(e){t.Fatal("journal retained after clear")}
  })
 }
}
func TestB116HardwareOffloadActiveAndInterrupted(t *testing.T){
 path:=filepath.Join(t.TempDir(),"owned",tetherOffloadJournal)
 value:="0"
 run:=func(a ...string)(string,error){if a[0]=="get"{return value,nil};if a[0]=="put"{value=a[3];return "",nil};return "",fmt.Errorf("unexpected command")}
 if _,e:=NewTetherOffload(run,path,false);e==nil||value!="0"{t.Fatal("changed active/unknown HAL")}
 s,e:=NewTetherOffload(run,path,true);if e!=nil{t.Fatal(e)}
 if e=s.Stop(false);e==nil||value!="1"{t.Fatal("restore before forwarding cleanup")}
 if e=RecoverTetherOffload(run,path);e!=nil||value!="0"{t.Fatalf("owned recovery %v %s",e,value)}
}
func TestB116IndependentBpfAndHALReadback(t *testing.T){
 if TetherBPFState("  mIsBpfEnabled: true\n  Offload disabled\n")!="enabled"{t.Fatal("hardware switch confused with BPF")}
 if TetherBPFState("  mIsBpfEnabled: false\n")!="disabled"{t.Fatal("explicit BPF off")}
 if TetherBPFState("Offload disabled\n")!="unknown"{t.Fatal("missing BPF falsely passed")}
 if TetherHALInactive("Offload disabled\n"){t.Fatal("preference is not actual HAL stop")}
 if !TetherHALInactive("Hardware offload:\n  Offload HALs not started\n"){t.Fatal("inactive HAL readback")}
}
