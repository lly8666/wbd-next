//go:build windows

package windowsclient

import "encoding/json"

// n4ValidatePersistedFullRouteReceipts checks the only parent/child WAL
// relationship that could authorize recovery of original GameFEC's final
// route stage. READ-ONLY: it does not recover, adopt an alias, delete a
// route, clear WFP, or promote PreRoute WAL into full-product qualification.
// The checksum-valid parent generation and child per-entry intents must
// agree before any future OS-level recovered-route CAS is attempted.
func n4ValidatePersistedFullRouteReceipts(
 j n4UnifiedJournal,id N4UnifiedIdentity,child *n4Journal,
)([]NativeRouteKey,error){
 if !n4ValidPinnedPnPHash(id.PnPInstanceSHA256) ||
  j.Identity!=id || len(j.Records)!=5 ||
  (j.Phase!="active" && j.Phase!="applying" && j.Phase!="cleaning") ||
  j.Records[4].Name!="routes" ||
  (j.Records[4].State!="intent" && j.Records[4].State!="owned"){
  return nil,ErrN4JournalConflict
 }
 // The first four receipts must already be definitively owned before
 // any route stage can exist. Reuse the original strict real baseline
 // validation for guard, address, MTU and DNS; do not weaken it.
 for _,rec:=range j.Records[:4]{
  if rec.State!="owned"{return nil,ErrN4JournalConflict}
 }
 prefix:=j
 prefix.Records=j.Records[:4]
 prefix.Phase="applying"
 if err:=n4ValidatePersistedPreRouteJournal(prefix,id);err!=nil{
  return nil,err
 }
 var receipt n4CompactRouteBaseline
 if err:=json.Unmarshal(j.Records[4].Before,&receipt);err!=nil{
  return nil,ErrN4JournalConflict
 }
 keys:=receipt.Keys
 if err:=n4ValidateRouteBatch(keys);err!=nil{
  return nil,ErrN4JournalConflict
 }
 var dns n4DNSStageBaseline
 if err:=json.Unmarshal(j.Records[3].Before,&dns);err!=nil{
  return nil,ErrN4JournalConflict
 }
 for i,key:=range keys{
  if (i==0 && key.Interface==id.WintunIndex) ||
   (i>0 && key.Interface!=id.WintunIndex){
   return nil,ErrN4JournalConflict
  }
  if i>2{
   // No arbitrary /32 host capture may be acquired from a recoverable
   // WAL: every one must already belong to the original DNS baseline.
   found:=false
   for _,server:=range dns.Servers{
    if key.Prefix.Addr()==server && key.Prefix.Bits()==32{
     found=true;break
    }
   }
   if !found{return nil,ErrN4JournalConflict}
  }
 }
 if child!=nil{
  if child.Schema!=n4JournalSchema ||
   n4ValidateJournal(*child)!=nil ||
   len(child.Entries)>len(keys){
   return nil,ErrN4JournalConflict
  }
  if child.Phase=="active" && len(child.Entries)!=len(keys){
   return nil,ErrN4JournalConflict
  }
  for i,entry:=range child.Entries{
   if entry.Key!=keys[i] ||
    (entry.State=="intent" && i!=len(child.Entries)-1){
    return nil,ErrN4JournalConflict
   }
   // Parent can mark routes owned only after the entire child journal
   // reached active. An unconfirmed child intent cannot be promoted.
   if j.Records[4].State=="owned" && entry.State!="owned"{
    return nil,ErrN4JournalConflict
   }
  }
  if j.Records[4].State=="owned" && (!child.GuardArmed || child.Phase=="applying"){
   return nil,ErrN4JournalConflict
  }
 }
 return keys,nil
}
