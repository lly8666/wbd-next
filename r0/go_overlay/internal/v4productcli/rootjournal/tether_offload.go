package rootjournal

import (
 "errors"
 "fmt"
 "io"
 "os"
 "strings"
 "syscall"
)

const tetherOffloadJournal="tether-offload-journal"
const tetherOffloadKey="tether_offload_disabled"

// Only the Android hardware offload preference, never a BPF map, program,
// netd, or other global setting. The caller proves the HAL is not running
// before changing an enabled/default preference. A settings write alone
// is NOT a live HAL Stop receipt.
func ReadTetherOffload(run Runner)(string,error){
 s,e:=run("get","global",tetherOffloadKey)
 if e!=nil{return "",e}
 s=strings.TrimSpace(s)
 if s!="0"&&s!="1"&&s!="null"{return "",fmt.Errorf("unknown hardware offload preference")}
 return s,nil
}
func readOffloadJournal(path string)(string,bool,error){
 f,e:=openNoFollow(path,syscall.O_RDONLY,0)
 if errors.Is(e,syscall.ENOENT){return "",false,nil}
 if e!=nil{return "",false,e};defer f.Close()
 st,e:=f.Stat();if e!=nil{return "",false,e}
 owner,ok:=st.Sys().(*syscall.Stat_t)
 if !ok||owner.Uid!=uint32(os.Geteuid())||!st.Mode().IsRegular()||st.Mode().Perm()!=0600||st.Size()>4{return "",false,fmt.Errorf("invalid offload journal")}
 b,e:=io.ReadAll(io.LimitReader(f,5));if e!=nil{return "",false,e}
 old:=string(b)
 if old!="0"&&old!="null"{return "",false,fmt.Errorf("invalid original offload preference")}
 return old,true,nil
}
func restoreOffload(run Runner,path string)error{
 old,found,e:=readOffloadJournal(path)
 if e!=nil||!found{return e}
 current,e:=ReadTetherOffload(run);if e!=nil{return e}
 // A user change to an enabled/default state while WBD is running is
 // not ours to undo. Only restore the disabled value we installed.
 if current=="1"{
  if old=="null"{_,e=run("delete","global",tetherOffloadKey)}else{_,e=run("put","global",tetherOffloadKey,old)}
  if e!=nil{return e}
  current,e=ReadTetherOffload(run);if e!=nil{return e}
  if current!=old{return fmt.Errorf("hardware offload restore readback mismatch")}
 }
 if e=os.Remove(path);e!=nil{return e}
 return parentSync(path)
}
type TetherOffloadOwner struct{run Runner;path string;lock *os.File;changed bool}
func (s *TetherOffloadOwner) Changed()bool{return s!=nil&&s.changed}
func NewTetherOffload(run Runner,path string,halInactive bool)(*TetherOffloadOwner,error){
 if run==nil{return nil,fmt.Errorf("missing offload settings runner")}
 l,e:=scopedOwnerLock(path,tetherOffloadJournal,"tether-offload-owner.lock");if e!=nil{return nil,e}
 fail:=func(e error)(*TetherOffloadOwner,error){return nil,errors.Join(e,l.Close())}
 _,found,e:=readOffloadJournal(path)
 if e!=nil{return fail(e)}
 if found{return fail(fmt.Errorf("previous hardware offload journal requires owned Restore"))}
 old,e:=ReadTetherOffload(run);if e!=nil{return fail(e)}
 s:=&TetherOffloadOwner{run:run,path:path,lock:l}
 if old=="1"{return s,nil} // already disabled by user; no write, no restore
 if !halInactive{return fail(fmt.Errorf("hardware offload running or unknown; stop existing sharing first"))}
 f,e:=openNoFollow(path,syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL,0600)
 if e!=nil{return fail(e)}
 n,e:=f.WriteString(old);if e==nil&&n!=len(old){e=io.ErrShortWrite}
 if e==nil{e=f.Sync()}
 if e=errors.Join(e,f.Close());e!=nil{return fail(e)}
 if e=parentSync(path);e!=nil{return fail(e)}
 _,e=run("put","global",tetherOffloadKey,"1")
 if e==nil{
  var v string
  v,e=ReadTetherOffload(run)
  if e==nil&&v!="1"{e=fmt.Errorf("hardware offload disable readback mismatch")}
 }
 if e!=nil{return fail(errors.Join(e,restoreOffload(run,path)))}
 s.changed=true
 return s,nil
}
// Restore only after our forwarding state was withdrawn. If cleanup was
// uncertain, retain the journal for the existing explicit Root Restore.
func(s *TetherOffloadOwner) Stop(forwardingCleared bool)error{
 if s==nil||s.lock==nil{return nil}
 var e error
 if s.changed{
  if forwardingCleared{e=restoreOffload(s.run,s.path)}else{e=fmt.Errorf("hardware offload restore deferred until owned forwarding cleanup")}
 }
 e=errors.Join(e,s.lock.Close());s.lock=nil
 return e
}
func RecoverTetherOffload(run Runner,path string)error{
 l,e:=scopedOwnerLock(path,tetherOffloadJournal,"tether-offload-owner.lock");if e!=nil{return e};defer l.Close()
 return restoreOffload(run,path)
}

// BPF coordinator config is independent from hardware preference. Do not
// infer false from missing/changed OEM dump text, or infer active from a
// dump error. Exact known lines only; conflicting lines are unknown.
func TetherBPFState(dump string)string{
 yes,no:=false,false
 for _,line:=range strings.Split(dump,"\n"){
  switch strings.TrimSpace(line){case "mIsBpfEnabled: true":yes=true;case "mIsBpfEnabled: false":no=true}
 }
 if yes&&!no{return "enabled"}
 if no&&!yes{return "disabled"}
 return "unknown"
}
func TetherHALInactive(dump string)bool{
 inactive,active:=false,false
 for _,line:=range strings.Split(dump,"\n"){
  switch strings.TrimSpace(line){case "Offload HALs not started":inactive=true;case "Offload HALs started":active=true}
 }
 return inactive&&!active
}
