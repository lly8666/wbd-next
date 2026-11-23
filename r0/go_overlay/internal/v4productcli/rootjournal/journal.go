// Package rootjournal owns one reversible Android ARM64 per-UID IPv4 route.
// It never creates a default/main-table route, changes global DNS, marks
// process-wide sockets, performs TLS, or touches a Go/Rust packet hot path.
//
// An fsync'd O_EXCL root-owned journal precedes kernel mutation; after a
// process crash the next authorized invocation can delete ONLY that exact
// rule and its dedicated table route, after exact kernel readback.
package rootjournal

import (
    "crypto/rand"
    "encoding/hex"
    "encoding/json"
    "errors"
    "fmt"
    "io"
    "net/netip"
    "os"
    "path/filepath"
    "strconv"
    "strings"
    "syscall"
)

const (
    Table = 19842
    Priority = 9600
    version = 1
    maxJournalBytes = 2048
)

// Runner executes ip(8) without shell interpolation; every call is cold-only.
type Runner func(...string)(string,error)

type Plan struct {
    Version int `json:"version"`
    UID int `json:"uid"`
    Tun string `json:"tun"`
    Lease string `json:"lease"`
    ServerIP string `json:"server_ip,omitempty"`
    DirectCIDRs []string `json:"direct_cidrs,omitempty"`
    Underlay string `json:"underlay"`
    NetworkHandle uint64 `json:"network_handle"`
    IfIndex int `json:"ifindex"`
    Nonce string `json:"nonce"`
}

type Session struct {
    run Runner
    journal string
    plan Plan
    active bool
    // O_NOFOLLOW owner.lock flock survives across all route mutations.
    // A second process MUST NOT recover a still-running first generation.
    lock *os.File
}

func nameOK(s string)bool{
    if len(s)==0||len(s)>15{return false}
    for _,r:=range s{
        if !(r>='a'&&r<='z'||r>='A'&&r<='Z'||
             r>='0'&&r<='9'||r=='_'||r=='-'){return false}
    }
    return true
}

func (p Plan) valid()bool{
    addr,err:=netip.ParsePrefix(p.Lease)
    return err==nil&&addr.IsValid()&&addr.Addr().Is4()&&
        addr.Bits()==32&&!addr.Addr().IsUnspecified()&&
        !addr.Addr().IsMulticast()&&p.UID>=10000&&p.UID<=1999999&&
        nameOK(p.Tun)&&nameOK(p.Underlay)&&p.Tun!=p.Underlay&&
        (p.ServerIP==""||(validServerPeerIPv4(p.ServerIP)&&
        p.ServerIP!=addr.Addr().String()))&&
        validDirectCIDRs(p.DirectCIDRs,p.ServerIP)&&
        p.NetworkHandle!=0&&p.IfIndex>0&&
        p.Version==version&&len(p.Nonce)==32
}

// Deliberately no environment-dependent table or priority: old root
// process recovery MUST use the same namespace and dedicated fixed keys.
func routeShow()[]string{
    return []string{"-4","route","show","table",strconv.Itoa(Table)}
}
func ruleShow()[]string{return []string{"-4","rule","show"}}
func routeAdd(tun string)[]string{
    return []string{"-4","route","add","default","dev",tun,"table",strconv.Itoa(Table)}
}
func routeDel(tun string)[]string{
    return []string{"-4","route","del","default","dev",tun,"table",strconv.Itoa(Table)}
}
func ruleAdd(uid int)[]string{
    v:=strconv.Itoa(uid)
    return []string{"-4","rule","add","pref",strconv.Itoa(Priority),
        "uidrange",v+"-"+v,"lookup",strconv.Itoa(Table)}
}
func ruleDel(uid int)[]string{
    v:=strconv.Itoa(uid)
    return []string{"-4","rule","del","pref",strconv.Itoa(Priority),
        "uidrange",v+"-"+v,"lookup",strconv.Itoa(Table)}
}

// Parse complete ip output, not guessed success from exit code. Reject
// foreign route attrs/table occupants before deletion.
func routeState(out,tun string)(present bool,err error){
    out=strings.TrimSpace(out)
    if out==""{return false,nil}
    lines:=strings.Split(out,"\n")
    if len(lines)!=1{return false,fmt.Errorf("foreign route occupies WBD table")}
    fields:=strings.Fields(lines[0])
    if len(fields)<3||fields[0]!="default"||
        fields[1]!="dev"||fields[2]!=tun{
        return false,fmt.Errorf("WBD route differs from owned TUN")
    }
    // The exact route was created without metrics, gateway, source, mtu
    // overrides or other selectors. Never delete a modified/foreign route
    // merely because its destination and device still match.
    seenScope,seenProto:=false,false
    for i:=3;i<len(fields);i+=2{
        if i+1>=len(fields){return false,fmt.Errorf("incomplete owned WBD route attribute")}
        switch {
        case fields[i]=="scope"&&fields[i+1]=="link"&&!seenScope:
            seenScope=true
        case fields[i]=="proto"&&fields[i+1]=="boot"&&!seenProto:
            seenProto=true
        default:
            return false,fmt.Errorf("foreign WBD route attributes")
        }
    }
    return true,nil
}
// Strictly match the ordinary uidrange-only rule emitted by our own ip rule
// add. Extra selectors (fwmark, iif, oif, not, ipproto, etc.) narrow the
// kernel match and make this a different rule, which Stop must not delete.
// Both the legacy single and multi-UID journal use this ONE parser.
func strictOwnedUIDRule(fields []string,priority,uid int)bool{
    if len(fields)<7||fields[0]!=strconv.Itoa(priority)+":"{return false}
    i:=1
    if fields[i]!="from"||fields[i+1]!="all"{return false}
    i+=2
    if i<len(fields)&&fields[i]=="to"{
        if i+1>=len(fields)||fields[i+1]!="all"{return false}
        i+=2
    }
    if i+3>=len(fields)||fields[i]!="uidrange"||
       fields[i+1]!=strconv.Itoa(uid)+"-"+strconv.Itoa(uid){return false}
    i+=2
    if (fields[i]!="lookup"&&fields[i]!="table")||
        fields[i+1]!=strconv.Itoa(Table){return false}
    return i+2==len(fields)
}
func ruleState(out string,uid int)(present bool,err error){
    u:=strconv.Itoa(uid)+"-"+strconv.Itoa(uid)
    pref:=strconv.Itoa(Priority)+":"
    table:=strconv.Itoa(Table)
    for _,line:=range strings.Split(out,"\n"){
        fields:=strings.Fields(line)
        if len(fields)==0{continue}
        hasTable:=false
        hasUID:=false
        for i:=0;i+1<len(fields);i++{
            if (fields[i]=="lookup"||fields[i]=="table")&&fields[i+1]==table{
                hasTable=true
            }
            if fields[i]=="uidrange"&&fields[i+1]==u{hasUID=true}
        }
        if fields[0]!=pref && !hasTable{continue}
        if fields[0]!=pref||!hasTable||!hasUID||present||
           !strictOwnedUIDRule(fields,Priority,uid){
            return false,fmt.Errorf("foreign uidrange rule intersects dedicated WBD rule/table")
        }
        present=true
    }
    return present,nil
}

func ownedDirectory(path string)error{
    dir:=filepath.Dir(path)
    if !filepath.IsAbs(path)||filepath.Clean(path)!=path||
        filepath.Base(path)!="route-journal.json"{
        return fmt.Errorf("root route journal path invalid")
    }
    if err:=os.Mkdir(dir,0700);err!=nil&&!errors.Is(err,os.ErrExist){
        return err
    }
    st,err:=os.Lstat(dir)
    if err!=nil{return err}
    stat,ok:=st.Sys().(*syscall.Stat_t)
    if !ok||!st.IsDir()||st.Mode().Perm()!=0700||
        stat.Uid!=uint32(os.Geteuid()){
        return fmt.Errorf("root journal directory must be owner-only, not symlink")
    }
    return nil
}
func parentSync(path string)error{
    d,err:=os.Open(filepath.Dir(path))
    if err!=nil{return err}
    defer d.Close()
    return d.Sync()
}
func openNoFollow(path string,flags int,mode uint32)(*os.File,error){
    fd,err:=syscall.Open(path,flags|syscall.O_CLOEXEC|syscall.O_NOFOLLOW,mode)
    if err!=nil{return nil,err}
    return os.NewFile(uintptr(fd),"wbd-owned-root-journal"),nil
}
func journalRead(path string)(Plan,bool,error){
    f,err:=openNoFollow(path,syscall.O_RDONLY,0)
    if errors.Is(err,syscall.ENOENT){return Plan{},false,nil}
    if err!=nil{return Plan{},false,err}
    defer f.Close()
    st,err:=f.Stat()
    if err!=nil{return Plan{},false,err}
    owner,ok:=st.Sys().(*syscall.Stat_t)
    if !ok||!st.Mode().IsRegular()||st.Mode().Perm()!=0600||
        owner.Uid!=uint32(os.Geteuid())||st.Size()<2||
        st.Size()>maxJournalBytes{
        return Plan{},false,fmt.Errorf("foreign/invalid root journal")
    }
    raw,err:=io.ReadAll(io.LimitReader(f,maxJournalBytes+1))
    if err!=nil{return Plan{},false,err}
    var p Plan
    decoder:=json.NewDecoder(strings.NewReader(string(raw)))
    decoder.DisallowUnknownFields()
    if err=decoder.Decode(&p);err!=nil||!p.valid(){
        return Plan{},false,fmt.Errorf("invalid durable root routing journal")
    }
    if decoder.Decode(&struct{}{})!=io.EOF{
        return Plan{},false,fmt.Errorf("root journal trailing records")
    }
    return p,true,nil
}
func journalCreate(path string,p Plan)error{
    raw,err:=json.Marshal(p)
    if err!=nil{return err}
    raw=append(raw,'\n')
    if len(raw)>maxJournalBytes{return fmt.Errorf("journal over capacity")}
    f,err:=openNoFollow(path,syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL,0600)
    if err!=nil{return err}
    n,writeErr:=f.Write(raw)
    if writeErr==nil&&n!=len(raw){writeErr=io.ErrShortWrite}
    if writeErr==nil{writeErr=f.Sync()}
    closeErr:=f.Close()
    if writeErr!=nil{return writeErr}
    if closeErr!=nil{return closeErr}
    return parentSync(path)
}

func openOwnerLock(path string)(*os.File,error){
    lockPath:=filepath.Join(filepath.Dir(path),"owner.lock")
    f,err:=openNoFollow(lockPath,
        syscall.O_RDWR|syscall.O_CREAT,0600)
    if err!=nil{return nil,err}
    st,err:=f.Stat()
    if err!=nil{_ = f.Close();return nil,err}
    owner,ok:=st.Sys().(*syscall.Stat_t)
    if !ok||!st.Mode().IsRegular()||st.Mode().Perm()!=0600||
        owner.Uid!=uint32(os.Geteuid()){
        _=f.Close()
        return nil,fmt.Errorf("foreign root owner lock")
    }
    if err=syscall.Flock(int(f.Fd()),syscall.LOCK_EX|syscall.LOCK_NB);err!=nil{
        _=f.Close()
        return nil,fmt.Errorf("another original root route owner is still live: %w",err)
    }
    return f,nil
}
func New(run Runner,path string,original Plan)(session *Session,retErr error){
    if run==nil{return nil,fmt.Errorf("missing kernel route runner")}
    if err:=ownedDirectory(path);err!=nil{return nil,err}
    lock,err:=openOwnerLock(path)
    if err!=nil{return nil,err}
    defer func(){
        if retErr!=nil{_ = lock.Close()}
    }()
    original.Version=version
    var nonce [16]byte
    if _,err:=rand.Read(nonce[:]);err!=nil{return nil,err}
    original.Nonce=hex.EncodeToString(nonce[:])
    if !original.valid(){return nil,fmt.Errorf("invalid verified root UID /32 / Network scope")}
    s:=&Session{run:run,journal:path,plan:original,lock:lock}
    kind,exists,err:=readOwnedJournalVersion(path)
    if err!=nil{return nil,err}
    if exists{
        if kind==groupVersion{
            group,ok,e:=groupRead(path)
            if e!=nil||!ok{return nil,fmt.Errorf("invalid prior group journal: %w",e)}
            if group.Tun!=original.Tun||group.Underlay!=original.Underlay||
               !hasUID(group.UIDs,original.UID){
                return nil,fmt.Errorf("foreign previous group generation: manual recovery required")
            }
            gs:=&GroupSession{run:run,journal:path,plan:group,lock:lock}
            if err=gs.removeExact(group);err!=nil{return nil,err}
        }else{
            old,ok,e:=journalRead(path)
            if e!=nil||!ok{return nil,fmt.Errorf("invalid prior single journal: %w",e)}
            if old.UID!=original.UID||old.Tun!=original.Tun||
               old.Underlay!=original.Underlay{
                return nil,fmt.Errorf("foreign previous root generation: manual recovery required")
            }
            // A previous process may have died between durable journal,
            // route/rule add and Stop. Recover exactly its owned state.
            if err=s.removeExact(old);err!=nil{return nil,err}
        }
    }
    if err=s.requireEmpty();err!=nil{return nil,err}
    if err=journalCreate(path,original);err!=nil{return nil,err}
    // Durable receipt before ANY change. Failures retain the file until
    // exact route/rule cleanup proves the private table empty.
    if _,err=s.run(routeAdd(original.Tun)...);err!=nil{
        return nil,errors.Join(err,s.removeExact(original))
    }
    if err=s.requireRouteOnly(original);err!=nil{
        return nil,errors.Join(err,s.removeExact(original))
    }
    if original.ServerIP!=""{
        if _,err=s.run(peerThrowArgs("add",original.ServerIP)...);err!=nil{
            return nil,errors.Join(err,s.removeExact(original))
        }
        if err=s.requirePeerRouteOnly(original);err!=nil{
            return nil,errors.Join(err,s.removeExact(original))
        }
    }
    // B58: batch ordinary LAN/direct prefixes, then confirm the entire
    // private FIB once before the one selected App UID is installed.
    for _,cidr:=range original.DirectCIDRs{
        if _,err=s.run(directArgs("add",cidr)...);err!=nil{
            return nil,errors.Join(err,s.removeExact(original))
        }
    }
    if len(original.DirectCIDRs)>0{
        route,peer,direct,rule,readErr:=s.query(original)
        if readErr!=nil||!route||(original.ServerIP!=""&&!peer)||
            !allDirectPresent(direct)||rule{
            return nil,errors.Join(fmt.Errorf("single-app direct FIB not ready before UID: %w",readErr),
                s.removeExact(original))
        }
    }
    if _,err=s.run(ruleAdd(original.UID)...);err!=nil{
        return nil,errors.Join(err,s.removeExact(original))
    }
    if err=s.requireReady(original);err!=nil{
        return nil,errors.Join(err,s.removeExact(original))
    }
    s.active=true
    return s,nil
}
func (s *Session) query(p Plan)(bool,bool,[]bool,bool,error){
    out,err:=s.run(routeShow()...)
    if err!=nil{return false,false,nil,false,err}
    route,peer,direct,err:=routeWithDirect(out,p.Tun,p.ServerIP,p.DirectCIDRs)
    if err!=nil{return false,false,nil,false,err}
    lines,err:=s.run(ruleShow()...)
    if err!=nil{return false,false,nil,false,err}
    rule,err:=ruleState(lines,p.UID)
    return route,peer,direct,rule,err
}
func (s *Session) requireEmpty()error{
    route,peer,direct,rule,err:=s.query(s.plan)
    if err!=nil{return err}
    if route||peer||anyDirectPresent(direct)||rule{
        return fmt.Errorf("WBD routing table/rule occupied")
    }
    return nil
}
func (s *Session) requireRouteOnly(p Plan)error{
    route,peer,direct,rule,err:=s.query(p)
    if err!=nil{return err}
    if !route||peer||anyDirectPresent(direct)||rule{
        return fmt.Errorf("WBD route-only readback mismatch")
    }
    return nil
}
func (s *Session) requirePeerRouteOnly(p Plan)error{
    route,peer,direct,rule,err:=s.query(p)
    if err!=nil{return err}
    if !route||!peer||anyDirectPresent(direct)||rule{
        return fmt.Errorf("WBD peer-only route readback mismatch")
    }
    return nil
}
func (s *Session) requireReady(p Plan)error{
    route,peer,direct,rule,err:=s.query(p)
    if err!=nil{return err}
    if !route||(p.ServerIP!=""&&!peer)||
        !allDirectPresent(direct)||!rule{
        return fmt.Errorf("WBD authenticated UID/direct/peer readback mismatch")
    }
    return nil
}
func (s *Session) removeExact(p Plan)error{
    route,peer,direct,rule,err:=s.query(p)
    if err!=nil{return err}
    if rule{
        if _,err=s.run(ruleDel(p.UID)...);err!=nil{return err}
    }
    for i:=len(direct)-1;i>=0;i--{
        if direct[i]{
            if _,err=s.run(directArgs("del",p.DirectCIDRs[i])...);err!=nil{return err}
        }
    }
    if peer{
        if _,err=s.run(peerThrowArgs("del",p.ServerIP)...);err!=nil{return err}
    }
    if route{
        if _,err=s.run(routeDel(p.Tun)...);err!=nil{return err}
    }
    if err=s.requireEmpty();err!=nil{return err}
    if err=os.Remove(s.journal);err!=nil{return err}
    return parentSync(s.journal)
}
// Stop is idempotent, never deletes a foreign route, and gives a positive
// completion ONLY once OS readback proves the policy gone and fsync unlinks
// the journal. Called BEFORE original Rust M4 Stop/join.
func (s *Session) Stop()error{
    if s==nil{return nil}
    if !s.active{return nil}
    if err:=s.removeExact(s.plan);err!=nil{return err}
    s.active=false
    // The actual kernel rule, route and durable journal are now absent.
    // Only then release the cross-process ownership barrier.
    if s.lock!=nil{
        err:=s.lock.Close()
        s.lock=nil
        return err
    }
    return nil
}
