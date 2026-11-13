//go:build windows

package windowsclient

// PLAN029 generation-owned Defender listener lease, separate from the old
// WFP guard. A rule can ONLY be removed after a durable "owned" receipt
// from its original generation and an exact Windows Firewall COM readback.
// A missing/unconfirmed receipt with a present rule is AMBIGUOUS, not free
// authorization to delete it; preserve the sidecar for operator recovery.
import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "net/netip"
 "os"
 "path/filepath"
 "strconv"
)

const n4Plan029DefenderSchema="wbd-plan029-defender-lease/v1"
type n4Plan029DefenderKey struct{
 Name string `json:"name"`
 Description string `json:"description"`
 Lease4 netip.Addr `json:"lease4"`
 Remote4 netip.Addr `json:"remote4"`
 Port uint16 `json:"port"`
}
func(k n4Plan029DefenderKey)validate()error{
 if len(k.Name)<20||len(k.Name)>96||
  len(k.Description)<20||len(k.Description)>120||
  k.Port<1024||!k.Lease4.Is4()||!k.Remote4.Is4()||
  k.Lease4.IsUnspecified()||k.Remote4.IsUnspecified()||
  k.Lease4.IsLoopback()||k.Remote4.IsLoopback()||
  k.Remote4.As4()[0]!=198||k.Remote4.As4()[1]!=19||
  k.Remote4.As4()[3]==0||k.Remote4.As4()[3]==255||
  k.Lease4==k.Remote4{return ErrN4NativeGuard}
 return nil
}
func n4Plan029DefenderKeyFor(id N4UnifiedIdentity,
 lease,synthetic netip.Addr,port uint16)(n4Plan029DefenderKey,error){
 var k n4Plan029DefenderKey
 if !id.valid(){return k,ErrN4NativeGuard}
 // A random full epoch + installation + real PnP identity key uniquely
 // pins the EXACT rule name to a single authenticated original owner.
 digest:=sha256.Sum256([]byte(fmt.Sprintf(
  "%x/%x/%s/%d/%d/%s/%s/%d",
  id.Installation,id.Generation,id.PnPInstanceSHA256,
  id.WintunLUID,id.WintunIndex,lease,synthetic,port)))
 k=n4Plan029DefenderKey{
  Name:"WBD-PLAN029-TCP-"+hex.EncodeToString(digest[:16]),
  Description:"WBD-PLAN029-OWNED-"+hex.EncodeToString(digest[:]),
  Lease4:lease,Remote4:synthetic,Port:port,
 }
 if e:=k.validate();e!=nil{return n4Plan029DefenderKey{},e}
 return k,nil
}

type n4Plan029DefenderBackend interface{
 Lookup(context.Context,n4Plan029DefenderKey)(present,exact bool,err error)
 CreateIfAbsent(context.Context,n4Plan029DefenderKey)error
 RemoveOwned(context.Context,n4Plan029DefenderKey)error
}
type n4Plan029DefenderRecord struct{
 Schema string `json:"schema"`
 Identity N4UnifiedIdentity `json:"identity"`
 Key n4Plan029DefenderKey `json:"key"`
 Phase string `json:"phase"` // intent|owned|cleaning
}
type n4Plan029DefenderEnvelope struct{
 Data n4Plan029DefenderRecord `json:"data"`
 SHA256 string `json:"sha256"`
}
func n4Plan029DefenderValidateRecord(rec n4Plan029DefenderRecord,
 id N4UnifiedIdentity,k n4Plan029DefenderKey)error{
 if !id.valid()||rec.Schema!=n4Plan029DefenderSchema||
   rec.Identity!=id||rec.Key!=k||k.validate()!=nil||
   (rec.Phase!="intent"&&rec.Phase!="owned"&&rec.Phase!="cleaning"){
  return ErrN4JournalConflict
 }
 return nil
}
func n4Plan029WriteDefender(path string,
 rec n4Plan029DefenderRecord,initial bool)error{
 if path==""||rec.Schema!=n4Plan029DefenderSchema||
  !rec.Identity.valid()||rec.Key.validate()!=nil{
  return ErrN4JournalConflict
 }
 payload,e:=json.Marshal(rec);if e!=nil{return e}
 hash:=sha256.Sum256(payload)
 data,e:=json.Marshal(n4Plan029DefenderEnvelope{
  Data:rec,SHA256:hex.EncodeToString(hash[:])})
 if e!=nil{return e}
 if len(data)>n4MaxJournalBytes{return ErrN4JournalConflict}
 dir:=filepath.Dir(path)
 if e=os.MkdirAll(dir,0700);e!=nil{return e}
 if initial{
  f,err:=os.OpenFile(path,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
  if errors.Is(err,os.ErrExist){return ErrN4JournalConflict}
  if err!=nil{return err}
  _,err=f.Write(data);if err==nil{err=f.Sync()}
  return errors.Join(err,f.Close())
 }
 f,e:=os.CreateTemp(dir,".wbd-p029-defender-*")
 if e!=nil{return e}
 defer os.Remove(f.Name())
 if e=f.Chmod(0600);e!=nil{f.Close();return e}
 if _,e=f.Write(data);e!=nil{f.Close();return e}
 if e=f.Sync();e!=nil{f.Close();return e}
 if e=f.Close();e!=nil{return e}
 return os.Rename(f.Name(),path)
}
func n4Plan029ReadDefender(path string,id N4UnifiedIdentity,
 k n4Plan029DefenderKey)(n4Plan029DefenderRecord,error){
 var empty n4Plan029DefenderRecord
 f,e:=os.Open(path);if e!=nil{return empty,e}
 defer f.Close()
 data,e:=io.ReadAll(io.LimitReader(f,n4MaxJournalBytes+1))
 if e!=nil{return empty,e}
 if len(data)>n4MaxJournalBytes{return empty,ErrN4JournalConflict}
 var envelope n4Plan029DefenderEnvelope
 if e=json.Unmarshal(data,&envelope);e!=nil{return empty,ErrN4JournalConflict}
 body,e:=json.Marshal(envelope.Data)
 if e!=nil{return empty,ErrN4JournalConflict}
 digest:=sha256.Sum256(body)
 if hex.EncodeToString(digest[:])!=envelope.SHA256||
  n4Plan029DefenderValidateRecord(envelope.Data,id,k)!=nil{
  return empty,ErrN4JournalConflict
 }
 return envelope.Data,nil
}
func n4Plan029DefenderInstall(ctx context.Context,path string,
 id N4UnifiedIdentity,k n4Plan029DefenderKey,
 backend n4Plan029DefenderBackend)error{
 if ctx==nil||path==""||!id.valid()||k.validate()!=nil||backend==nil{
  return ErrN4NativeGuard
 }
 if e:=ctx.Err();e!=nil{return e}
 exists,_,e:=backend.Lookup(ctx,k);if e!=nil{return e}
 if exists{return ErrN4ForeignRoute}
 // Exact durable intent BEFORE OS mutation, never an implicit grant
 // to clean an unconfirmed or foreign rule if Create crashes midflight.
 rec:=n4Plan029DefenderRecord{Schema:n4Plan029DefenderSchema,
  Identity:id,Key:k,Phase:"intent"}
 if e=n4Plan029WriteDefender(path,rec,true);e!=nil{return e}
 if e=backend.CreateIfAbsent(ctx,k);e!=nil{return e}
 exists,exact,e:=backend.Lookup(ctx,k)
 if e!=nil{return e}
 if !exists||!exact{return ErrN4RouteAmbiguous}
 rec.Phase="owned"
 return n4Plan029WriteDefender(path,rec,false)
}
func n4Plan029DefenderRecover(ctx context.Context,path string,
 id N4UnifiedIdentity,k n4Plan029DefenderKey,
 backend n4Plan029DefenderBackend)error{
 if ctx==nil||path==""||!id.valid()||k.validate()!=nil||backend==nil{
  return ErrN4NativeGuard
 }
 rec,e:=n4Plan029ReadDefender(path,id,k)
 if errors.Is(e,os.ErrNotExist){
  // Absence of a sidecar alone cannot prove a firewall rule is absent.
  present,_,lookupErr:=backend.Lookup(ctx,k)
  if lookupErr!=nil{return lookupErr}
  if present{return ErrN4RouteAmbiguous}
  return nil
 }
 if e!=nil{return e}
 if e=ctx.Err();e!=nil{return e}
 present,exact,e:=backend.Lookup(ctx,k)
 if e!=nil{return e}
 if rec.Phase=="intent"&&present{
  // Crash after Add but before exact owned receipt, or foreign rule:
  // stop must preserve the rule + WAL and refuse false disconnection.
  return ErrN4RouteAmbiguous
 }
 if present&&!exact{return ErrN4ForeignRoute}
 if rec.Phase!="intent"{
  rec.Phase="cleaning"
  if e=n4Plan029WriteDefender(path,rec,false);e!=nil{return e}
  if present{
   if e=backend.RemoveOwned(ctx,k);e!=nil{return e}
   present,_,e=backend.Lookup(ctx,k)
   if e!=nil{return e}
   if present{return ErrN4RouteAmbiguous}
  }
 }
 // This unlink is safe only after a checked absence. Another generation's
 // same-looking but distinct rule name can never be removed by this path.
 return os.Remove(path)
}
func n4Plan029DefenderSidecarPath(statePath string)string{
 return statePath+".plan029-defender-tcp"
}
func n4Plan029DefenderPortText(k n4Plan029DefenderKey)string{
 return strconv.Itoa(int(k.Port))
}
