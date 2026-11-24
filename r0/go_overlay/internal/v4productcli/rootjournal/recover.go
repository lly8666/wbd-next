package rootjournal

// RecoverOwned withdraws ONLY the kernel route/rule described by a fully
// validated, root-only durable journal. It is the Android UI Restore seam.
// It never flushes the global firewall, main table, netd or other VPN rules.
import (
 "fmt"
 "strconv"
 "strings"
)

// RecoverOwned must be called by the real rooted original Go client only
// AFTER the exact native process has stopped/joined. The cross-process flock
// rejects a concurrent real owner even if the app supervisor died.
func RecoverOwned(run Runner,path string,batches ...DirectBatch)(recovered bool,retErr error){
 if run==nil{return false,fmt.Errorf("missing root route runner")}
 if err:=ownedDirectory(path);err!=nil{return false,err}
 lock,err:=openOwnerLock(path)
 if err!=nil{return false,err}
 defer func(){if e:=lock.Close();e!=nil{retErr=fmt.Errorf("route owner unlock incomplete: %w",e)}}()
 v,exists,err:=readOwnedJournalVersion(path)
 if err!=nil{return false,err}
 if exists{
  switch v {
  case version:
   p,ok,e:=journalRead(path)
   if e!=nil||!ok{return false,fmt.Errorf("invalid single-route recovery journal: %w",e)}
   if e=(&Session{run:run,journal:path,plan:p,directBatch:optionalDirectBatch(batches)}).removeExact(p);e!=nil{return false,e}
  case groupVersion:
   p,ok,e:=groupRead(path)
   if e!=nil||!ok{return false,fmt.Errorf("invalid group-route recovery journal: %w",e)}
   if e=(&GroupSession{run:run,journal:path,plan:p,directBatch:optionalDirectBatch(batches)}).removeExact(p);e!=nil{return false,e}
  case legacyAllAppsVersion,allAppsVersion:
   p,ok,e:=readAllAppJournal(path)
   if e!=nil||!ok{return false,fmt.Errorf("invalid all-app-route recovery journal: %w",e)}
   if e=(&AllAppSession{run:run,journal:path,plan:p,directBatch:optionalDirectBatch(batches)}).removeExact(p);e!=nil{return false,e}
  default:return false,fmt.Errorf("foreign route journal version")
  }
  recovered=true
 }
 // A clean empty private table AND absence of any reserved WBD priority
 // are required before publishing Restore success. Never mutate foreign
 // table/rules if the immutable ownership journal was missing.
 table,e:=run(routeShow()...)
 if e!=nil||strings.TrimSpace(table)!="" {return recovered,fmt.Errorf("private root table not empty or unavailable")}
 rules,e:=run(ruleShow()...)
 if e!=nil{return recovered,fmt.Errorf("root policy rules unavailable")}
 for _,line:=range strings.Split(rules,"\n"){
  words:=strings.Fields(line)
  if len(words)==0{continue}
  n,e:=strconv.Atoi(strings.TrimSuffix(words[0],":"))
  if e!=nil{return recovered,fmt.Errorf("malformed root policy rule")}
  if n>=Priority&&n<Priority+AllMaxRules{
   return recovered,fmt.Errorf("reserved root policy priority remains")}
  for i:=0;i+1<len(words);i++{
   if (words[i]=="lookup"||words[i]=="table")&&words[i+1]==strconv.Itoa(Table){
    return recovered,fmt.Errorf("owned root policy table still referenced")}
  }
 }
 return recovered,nil
}
