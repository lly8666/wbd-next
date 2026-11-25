package rootjournal

import(
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 "strings"
 "syscall"
)

const tetherBPFJournal="tether-bpf-journal.json"
const tetherBPFPinDir="/sys/fs/bpf/tethering/"

// Original tethering ingress attachments only. Never modify or unpin the
// program, its maps, CLAT, cgroup or netd BPF.
type TetherBPFHook struct{
 Interface string
 Index int
 Handle,Info,ProgramID,Flags uint32
 Name,Pin string
}
func tetherBPFName(name string)(pin string,upload bool,version int){
 n:=strings.TrimPrefix(strings.TrimSuffix(name,":[*fsobj]"),tetherBPFPinDir)
 for _,direction:=range []string{"upstream","downstream"}{
  for _,v:=range []int{4,6}{
   for _,link:=range []string{"ether","rawip"}{
    expected:=fmt.Sprintf("prog_offload_schedcls_tether_%s%d_%s",direction,v,link)
    if n==expected{return tetherBPFPinDir+expected,direction=="upstream",v}
   }
  }
 }
 return "",false,0
}
func(h TetherBPFHook)valid()bool{
 pin,_,version:=tetherBPFName(h.Name)
 proto:=uint32(8);if version==6{proto=0xdd86}
 return nameOK(h.Interface)&&h.Index>0&&h.Handle!=0&&h.Info>>16!=0&&h.Info&0xffff==proto&&
  h.ProgramID!=0&&pin!=""&&h.Pin==pin&&h.Flags&^uint32(1|16)==0
}
func(h TetherBPFHook)key()string{return fmt.Sprintf("%d/%d/%d",h.Index,h.Info,h.Handle)}
type TetherBPFIO struct{
 Read func()([]TetherBPFHook,error)
 PinID func(string)(uint32,error)
 Change func(TetherBPFHook,bool)error
 Current func(TetherBPFHook)bool
 BootID func()(string,error)
}
type tetherBPFRecord struct{Boot string;Hooks []TetherBPFHook}
func readTetherBPF(path string)(tetherBPFRecord,bool,error){
 var p tetherBPFRecord
 f,e:=openNoFollow(path,syscall.O_RDONLY,0)
 if errors.Is(e,syscall.ENOENT){return p,false,nil}
 if e!=nil{return p,false,e};defer f.Close()
 st,e:=f.Stat();if e!=nil{return p,false,e}
 uid,ok:=st.Sys().(*syscall.Stat_t)
 if !ok||uid.Uid!=uint32(os.Geteuid())||!st.Mode().IsRegular()||st.Mode().Perm()!=0600||st.Size()>maxRouteJournalBytes{return p,false,fmt.Errorf("invalid tether BPF journal")}
 d:=json.NewDecoder(io.LimitReader(f,maxRouteJournalBytes+1));d.DisallowUnknownFields()
 if d.Decode(&p)!=nil||d.Decode(&struct{}{})!=io.EOF||p.Boot==""||len(p.Hooks)==0{return p,false,fmt.Errorf("invalid tether BPF record")}
 seen:=map[string]bool{}
 for _,h:=range p.Hooks{if !h.valid()||seen[h.key()]{return p,false,fmt.Errorf("invalid tether BPF hook")};seen[h.key()]=true}
 return p,true,nil
}
func writeTetherBPF(path string,p tetherBPFRecord)error{
 b,e:=json.Marshal(p);if e!=nil{return e}
 f,e:=openNoFollow(path,syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL,0600)
 if e!=nil{return e}
 n,e:=f.Write(b);if e==nil&&n!=len(b){e=io.ErrShortWrite}
 if e==nil{e=f.Sync()}
 if e=errors.Join(e,f.Close());e!=nil{return e}
 return parentSync(path)
}
func validTetherBPFIO(k TetherBPFIO)bool{return k.Read!=nil&&k.PinID!=nil&&k.Change!=nil&&k.Current!=nil&&k.BootID!=nil}
func restoreTetherBPF(k TetherBPFIO,path string)error{
 p,found,e:=readTetherBPF(path);if e!=nil||!found{return e}
 boot,e:=k.BootID();if e!=nil{return e}
 if boot==p.Boot{
  current,e:=k.Read();if e!=nil{return e}
  byKey:=map[string]TetherBPFHook{};for _,h:=range current{byKey[h.key()]=h}
  for _,h:=range p.Hooks{
   if !k.Current(h){continue} // old interface gone; Android owns new one
   if got,ok:=byKey[h.key()];ok{
    if got!=h{return fmt.Errorf("tether BPF attachment replaced by Android")}
    continue
   }
   id,e:=k.PinID(h.Pin);if e!=nil||id!=h.ProgramID{return fmt.Errorf("original tether BPF pin changed")}
   if e=k.Change(h,true);e!=nil{return e}
  }
  current,e=k.Read();if e!=nil{return e}
  byKey=map[string]TetherBPFHook{};for _,h:=range current{byKey[h.key()]=h}
  for _,h:=range p.Hooks{if k.Current(h)&&byKey[h.key()]!=h{return fmt.Errorf("tether BPF restore readback incomplete")}}
 }
 if e=os.Remove(path);e!=nil{return e}
 return parentSync(path)
}
type TetherBPFOwner struct{k TetherBPFIO;path string;lock *os.File;count int}
func(s *TetherBPFOwner)Count()int{if s==nil{return 0};return s.count}
func NewTetherBPFPause(k TetherBPFIO,path,selected string)(*TetherBPFOwner,error){
 if !validTetherBPFIO(k)||!nameOK(selected){return nil,fmt.Errorf("invalid tether BPF scope")}
 l,e:=scopedOwnerLock(path,tetherBPFJournal,"tether-bpf-owner.lock");if e!=nil{return nil,e}
 fail:=func(e error)(*TetherBPFOwner,error){return nil,errors.Join(e,l.Close())}
 _,found,e:=readTetherBPF(path);if e!=nil{return fail(e)};if found{return fail(fmt.Errorf("previous tether BPF pause requires Restore"))}
 hooks,e:=k.Read();if e!=nil{return fail(e)}
 // Only the selected downstream ingress can divert new downstream packets
 // before the normal IP routing/NAT path. Return traffic from WBD enters
 // via TUN, not the physical upstream BPF hook.
 selectedHooks:=make([]TetherBPFHook,0,len(hooks))
 seen:=map[string]bool{}
 for _,h:=range hooks{
  _,upload,_:=tetherBPFName(h.Name)
  if h.Interface!=selected||!upload{continue}
  if !h.valid()||seen[h.key()]||!k.Current(h){return fail(fmt.Errorf("unrecognized tether BPF attachment"))}
  seen[h.key()]=true
  selectedHooks=append(selectedHooks,h)
  id,e:=k.PinID(h.Pin);if e!=nil||id!=h.ProgramID{return fail(fmt.Errorf("cannot reopen original tether BPF pin: %w",e))}
 }
 hooks=selectedHooks
 if len(hooks)==0{return nil,l.Close()}
 boot,e:=k.BootID();if e!=nil||boot==""{return fail(fmt.Errorf("kernel boot identity unavailable"))}
 if e=writeTetherBPF(path,tetherBPFRecord{Boot:boot,Hooks:hooks});e!=nil{return fail(e)}
 for _,h:=range hooks{
  if e=k.Change(h,false);e!=nil{return fail(errors.Join(e,restoreTetherBPF(k,path)))}
 }
 current,e:=k.Read()
 if e!=nil||hasSelectedTetherUpload(current,selected){return fail(errors.Join(e,fmt.Errorf("tether BPF detach readback incomplete"),restoreTetherBPF(k,path)))}
 return &TetherBPFOwner{k:k,path:path,lock:l,count:len(hooks)},nil
}
func hasSelectedTetherUpload(hooks []TetherBPFHook,selected string)bool{
 for _,h:=range hooks{_,upload,_:=tetherBPFName(h.Name);if h.Interface==selected&&upload{return true}}
 return false
}
func VerifyTetherBPFPause(k TetherBPFIO,path,selected string)error{
 p,found,e:=readTetherBPF(path);if e!=nil{return e}
 if found{
  boot,e:=k.BootID();if e!=nil||boot!=p.Boot{return fmt.Errorf("tether BPF owner changed")}
  same:=false
  for _,h:=range p.Hooks{if h.Interface==selected&&k.Current(h){same=true}}
  if !same{return fmt.Errorf("selected tether interface changed")}
 }
 hooks,e:=k.Read();if e!=nil{return e}
 if hasSelectedTetherUpload(hooks,selected){return fmt.Errorf("Android tether BPF attached again")}
 return nil
}
func(s *TetherBPFOwner)Stop(forwardingCleared bool)error{
 if s==nil||s.lock==nil{return nil}
 var e error
 if forwardingCleared{e=restoreTetherBPF(s.k,s.path)}else{e=fmt.Errorf("restore tether BPF after owned forwarding removal")}
 e=errors.Join(e,s.lock.Close());s.lock=nil;return e
}
func RecoverTetherBPF(k TetherBPFIO,path string)error{
 if !validTetherBPFIO(k){return fmt.Errorf("missing tether BPF IO")}
 l,e:=scopedOwnerLock(path,tetherBPFJournal,"tether-bpf-owner.lock");if e!=nil{return e};defer l.Close()
 return restoreTetherBPF(k,path)
}
