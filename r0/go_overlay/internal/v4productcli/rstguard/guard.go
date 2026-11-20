// Package rstguard owns exactly one Android root FakeTCP carrier RST rule.
// This is a cold-only iptables control, NEVER a packet sender or TLS fallback.
// The durable root-only journal is written before any kernel mutation.
package rstguard

import (
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

const marker = "wbd-next-root-rst-v1"
const maxJournal = 512
const maxRules = 256 << 10

var (
    ErrScope = errors.New("RST_GUARD_SCOPE")
    ErrLocked = errors.New("RST_GUARD_LOCKED")
    ErrJournal = errors.New("RST_GUARD_JOURNAL_UNSAFE")
    ErrBackend = errors.New("RST_GUARD_IPTABLES_UNAVAILABLE")
    ErrReadback = errors.New("RST_GUARD_READBACK_MISMATCH")
    ErrCleanup = errors.New("RST_GUARD_CLEANUP_UNVERIFIED")
)

func Class(err error) string {
    switch {
    case errors.Is(err, ErrScope): return "SCOPE_CONFLICT"
    case errors.Is(err, ErrLocked): return "OWNER_LOCKED"
    case errors.Is(err, ErrJournal): return "JOURNAL_UNSAFE"
    case errors.Is(err, ErrReadback): return "READBACK_MISMATCH"
    case errors.Is(err, ErrCleanup): return "CLEANUP_UNVERIFIED"
    default: return "IPTABLES_UNAVAILABLE"
    }
}

// Runner is cold-only. Production uses exec.CommandContext("iptables"), no shell.
type Runner func(...string) (string, error)

type Plan struct {
    Version int
    Interface string
    SourceIP string
    PeerIP string
    SourcePort int
    PeerPort int
}

func (p Plan) valid() bool {
    if p.Version != 1 || len(p.Interface) < 1 || len(p.Interface) > 15 ||
        p.SourcePort < 1 || p.SourcePort > 65535 ||
        p.PeerPort < 1 || p.PeerPort > 65535 { return false }
    for _, c := range p.Interface {
        if !(c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' ||
            c >= '0' && c <= '9' || c == '_' || c == '-' || c == '.') {
            return false
        }
    }
    source, e := netip.ParseAddr(p.SourceIP)
    if e != nil || !source.Is4() || source.IsUnspecified() || source.IsMulticast() || source.IsLoopback() {
        return false
    }
    peer, e := netip.ParseAddr(p.PeerIP)
    return e == nil && peer.Is4() && !peer.IsUnspecified() && !peer.IsMulticast() && !peer.IsLoopback()
}

func (p Plan) params() []string {
    return []string{
        "-o", p.Interface, "-s", p.SourceIP+"/32", "-d", p.PeerIP+"/32",
        "-p", "tcp", "-m", "tcp",
        "--sport", strconv.Itoa(p.SourcePort), "--dport", strconv.Itoa(p.PeerPort),
        "--tcp-flags", "RST", "RST",
        "-m", "comment", "--comment", marker, "-j", "DROP",
    }
}
func rule(action string, p Plan) []string {
    a := []string{"-w", "2", "-t", "filter", action, "OUTPUT"}
    return append(a, p.params()...)
}
func list() []string { return []string{"-w","2","-t","filter","-S","OUTPUT"} }
func counters() []string { return []string{"-w","2","-t","filter","-n","-v","-x","-L","OUTPUT"} }

type Guard struct {
    run Runner
    journal string
    lock *os.File
    plan Plan
    active bool
}

func checkPrivate(f *os.File, dir bool) error {
    st, e := f.Stat()
    if e != nil { return ErrJournal }
    owner, ok := st.Sys().(*syscall.Stat_t)
    if !ok || owner.Uid != uint32(os.Geteuid()) || owner.Nlink != 1 { return ErrJournal }
    if dir {
        if !st.IsDir() || st.Mode().Perm() != 0700 { return ErrJournal }
    } else if !st.Mode().IsRegular() || st.Mode().Perm() != 0600 {
        return ErrJournal
    }
    return nil
}
func safeFD(path string, flags int, perm uint32) (*os.File, error) {
    fd,e := syscall.Open(path, flags|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, perm)
    if e != nil { return nil, e }
    return os.NewFile(uintptr(fd), "wbd-owned-rst-guard"), nil
}
func syncDir(path string) error {
    d,e := os.Open(filepath.Dir(path))
    if e != nil { return ErrJournal }
    defer d.Close()
    if d.Sync() != nil { return ErrJournal }
    return nil
}
func read(path string) (Plan,bool,error) {
    f,e := safeFD(path,syscall.O_RDONLY,0)
    if errors.Is(e,syscall.ENOENT) { return Plan{},false,nil }
    if e != nil { return Plan{},false,ErrJournal }
    defer f.Close()
    if e = checkPrivate(f,false); e != nil { return Plan{},false,e }
    st,_ := f.Stat()
    if st.Size() < 2 || st.Size() > maxJournal { return Plan{},false,ErrJournal }
    b,e := io.ReadAll(io.LimitReader(f,maxJournal+1))
    if e != nil { return Plan{},false,ErrJournal }
    dec := json.NewDecoder(strings.NewReader(string(b)))
    dec.DisallowUnknownFields()
    var p Plan
    if dec.Decode(&p) != nil || !p.valid() || dec.Decode(&struct{}{}) != io.EOF {
        return Plan{},false,ErrJournal
    }
    return p,true,nil
}
func write(path string,p Plan) error {
    b,e := json.Marshal(p)
    if e != nil { return ErrJournal }
    b = append(b, '\n')
    if len(b) > maxJournal { return ErrJournal }
    f,e := safeFD(path,syscall.O_WRONLY|syscall.O_CREAT|syscall.O_EXCL,0600)
    if e != nil { return ErrJournal }
    if e = checkPrivate(f,false); e == nil {
        var n int
        n,e = f.Write(b)
        if e == nil && n != len(b) { e = io.ErrShortWrite }
    }
    if e == nil { e = f.Sync() }
    if closeErr := f.Close(); e == nil { e = closeErr }
    if e != nil { return ErrJournal }
    return syncDir(path)
}
func ownerLock(path string) (*os.File,error) {
    dir := filepath.Dir(path)
    if !filepath.IsAbs(path) || filepath.Clean(path) != path ||
        filepath.Base(path) != "rst-guard.json" { return nil,ErrJournal }
    st,e := os.Lstat(dir)
    if e != nil || !st.IsDir() || st.Mode().Perm() != 0700 ||
        st.Mode()&os.ModeSymlink != 0 { return nil,ErrJournal }
    owner,ok := st.Sys().(*syscall.Stat_t)
    if !ok || owner.Uid != uint32(os.Geteuid()) { return nil,ErrJournal }
    lock,e := safeFD(filepath.Join(dir,"rst-owner.lock"),syscall.O_RDWR|syscall.O_CREAT,0600)
    if e != nil { return nil,ErrJournal }
    if checkPrivate(lock,false) != nil { lock.Close(); return nil,ErrJournal }
    if syscall.Flock(int(lock.Fd()),syscall.LOCK_EX|syscall.LOCK_NB) != nil {
        lock.Close()
        return nil,ErrLocked
    }
    return lock,nil
}

// status checks this exact comment in OUTPUT, then -C checks the precise
// interface, 4-tuple and flags. Any duplicate/foreign comment fails closed.
func (g *Guard) status(p Plan) (bool,error) {
    output,e := g.run(list()...)
    if e != nil || len(output) > maxRules { return false,ErrBackend }
    count := 0
    for _,line := range strings.Split(output,"\n") {
        if !strings.Contains(line,marker) { continue }
        if !strings.HasPrefix(strings.TrimSpace(line),"-A OUTPUT ") ||
            !strings.Contains(line,"--comment") { return false,ErrScope }
        count++
    }
    if count > 1 { return false,ErrScope }
    if count == 0 { return false,nil }
    if _,e = g.run(rule("-C",p)...);e != nil { return false,ErrScope }
    return true,nil
}
func (g *Guard) remove(p Plan) error {
    present,e := g.status(p)
    if e != nil { return errors.Join(ErrCleanup,e) }
    if present {
        if _,e = g.run(rule("-D",p)...);e != nil { return ErrCleanup }
    }
    present,e = g.status(p)
    if e != nil || present { return ErrCleanup }
    if e = os.Remove(g.journal);e != nil { return ErrCleanup }
    if syncDir(g.journal) != nil { return ErrCleanup }
    return nil
}

// RecoverOwned is the recovery-only cold path. Exact journal + flock owns
// cleanup; without a journal, any foreign marker is a hard conflict, not
// permission to flush or delete a kernel firewall rule.
func RecoverOwned(run Runner,path string)(recovered bool,retErr error){
    if run==nil{return false,ErrBackend}
    lock,e:=ownerLock(path)
    if e!=nil{return false,e}
    defer func(){if lock.Close()!=nil{retErr=errors.Join(retErr,ErrCleanup)}}()
    g:=&Guard{run:run,journal:path,lock:lock}
    prior,exists,e:=read(path)
    if e!=nil{return false,e}
    if exists{
        if e=g.remove(prior);e!=nil{return false,e}
        recovered=true
    }
    present,e:=g.status(Plan{})
    if e!=nil||present{return recovered,errors.Join(ErrScope,e)}
    return recovered,nil
}

// New first recovers only a fully validated, stale, owned journal while
// holding flock. A foreign marker without a journal is NEVER deleted.
func New(run Runner,path string,p Plan) (_ *Guard,recovered bool,retErr error) {
    if run == nil || !p.valid() { return nil,false,ErrScope }
    lock,e := ownerLock(path)
    if e != nil { return nil,false,e }
    keep := false
    defer func(){ if !keep { lock.Close() } }()
    g := &Guard{run:run,journal:path,lock:lock,plan:p}
    prior,exists,e := read(path)
    if e != nil { return nil,false,e }
    if exists {
        if e = g.remove(prior);e != nil { return nil,false,e }
        recovered = true
    }
    occupied,e := g.status(p)
    if e != nil { return nil,recovered,e }
    if occupied { return nil,recovered,ErrScope }
    if e = write(path,p);e != nil { return nil,recovered,e }
    if _,e = g.run(rule("-I",p)...);e != nil {
        return nil,recovered,errors.Join(ErrBackend,g.remove(p))
    }
    verified,checkErr := g.status(p)
    if checkErr != nil || !verified {
        return nil,recovered,errors.Join(ErrReadback,checkErr,g.remove(p))
    }
    g.active = true
    keep = true
    return g,recovered,nil
}

// DropCounter is optional cold evidence; parse only a comment-tagged row.
// No packet, address, TLS transcript or unrelated firewall rule is exported.
func (g *Guard) DropCounter() (uint64,bool) {
    if g == nil || !g.active { return 0,false }
    out,e := g.run(counters()...)
    if e != nil || len(out) > maxRules { return 0,false }
    seen := false
    var result uint64
    for _,line := range strings.Split(out,"\n") {
        if !strings.Contains(line,marker) { continue }
        if seen { return 0,false }
        parts := strings.Fields(line)
        if len(parts) < 4 || parts[2] != "DROP" { return 0,false }
        n,e := strconv.ParseUint(parts[0],10,64)
        if e != nil { return 0,false }
        seen=true;result=n
    }
    return result,seen
}
func (g *Guard) Close() error {
    if g == nil { return nil }
    if !g.active { return ErrCleanup }
    g.active=false
    e:=g.remove(g.plan)
    if g.lock.Close()!=nil { e=errors.Join(e,ErrCleanup) }
    return e
}
func (p Plan) String() string { return fmt.Sprintf("rstguard-scope-version-%d",p.Version) }
