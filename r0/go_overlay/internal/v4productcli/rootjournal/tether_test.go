package rootjournal

import (
 "fmt"
 "path/filepath"
 "strings"
 "testing"
)
func TestB65TetherOwnedForwardingAndRestore(t *testing.T){
 p:=TetherPlan{Version:1,Tun:"wbd0",Downstream:"ap0",Subnet:"192.168.43.0/24",Lease:"10.9.0.2/32"}
 cmds:=p.commands();present:=make([]bool,len(cmds))
 ip:=func(a ...string)(string,error){
  if a[2]=="show"{
   var lines []string
   for i,c:=range cmds{if !present[i]||c.kind!=a[1]{continue}
    if c.kind=="route"{lines=append(lines,strings.Join(c.args," ")+" scope link")}else{
     row:=append([]string{c.args[1]+":"},c.args[2:]...)
     if i==5{row=append([]string{c.args[1]+":","from","all"},c.args[2:]...)}
     lines=append(lines,strings.Join(row," "))
    }
   };return strings.Join(lines,"\n"),nil
  }
  for i,c:=range cmds{if c.kind==a[1]&&strings.Join(c.args," ")==strings.Join(a[3:]," "){present[i]=a[2]=="add";return "",nil}}
  return "",fmt.Errorf("unexpected ip %v",a)
 }
 fw:=func(a ...string)(string,error){
  if a[4]=="-S"{var lines []string;for i,c:=range cmds{if present[i]&&c.kind==a[3]&&c.args[0]==a[5]{lines=append(lines,"-A "+strings.Join(c.args," "))}};return strings.Join(lines,"\n"),nil}
  row:=a[5:];if a[4]=="-I"{row=append([]string{a[5]},a[7:]...)}
  for i,c:=range cmds{if c.kind==a[3]&&strings.Join(c.args," ")==strings.Join(row," "){present[i]=a[4]=="-I";return "",nil}}
  return "",fmt.Errorf("unexpected firewall %v",a)
 }
 path:=filepath.Join(t.TempDir(),"tether-journal.json")
 owner,e:=NewTether(ip,fw,path,p);if e!=nil{t.Fatal(e)}
 for i,v:=range present{if !v{t.Fatalf("missing command %d",i)}}
 if e=owner.Stop();e!=nil{t.Fatal(e)}
 for _,v:=range present{if v{t.Fatal("Stop retained state")}}
 owner,e=NewTether(ip,fw,path,p);if e!=nil{t.Fatal(e)}
 if e=owner.lock.Close();e!=nil{t.Fatal(e)};owner.lock=nil
 if e=RecoverTether(ip,fw,path);e!=nil{t.Fatal(e)}
 for _,v:=range present{if v{t.Fatal("Restore retained state")}}
}
