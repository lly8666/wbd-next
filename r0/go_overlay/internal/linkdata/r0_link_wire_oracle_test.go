package linkdata

import (
    "bytes"
    _ "embed"
    "encoding/hex"
    "strings"
    "testing"
    "time"
)

//go:embed r0_link_fec_wire_v1.txt
var r0PinnedLinkWire string

func r0LinkFixture(t *testing.T, name string) []byte {
    t.Helper()
    for _, line := range strings.Split(r0PinnedLinkWire, "\n") {
        if line == "" || strings.HasPrefix(line, "#") { continue }
        parts := strings.Split(line, "|")
        if len(parts) != 2 { t.Fatalf("invalid fixed fixture row %q", line) }
        if parts[0] != name { continue }
        raw, err := hex.DecodeString(parts[1])
        if err != nil { t.Fatal(err) }
        return raw
    }
    t.Fatalf("missing fixture %s", name)
    return nil
}

func TestR0LinkPinnedRealGoMtu63_64_65Wire(t *testing.T) {
    f,err := NewFragmenter(64)
    if err != nil { t.Fatal(err) }
    packet := bytes.Repeat([]byte{0x5a}, 65)
    for _, n := range []int{63, 64} {
        frames, err := f.Fragment(packet[:n])
        if err != nil || len(frames)!=1 || !bytes.Equal(frames[0],packet[:n]) {
            t.Fatalf("n=%d unexpected real Go ordinary wire %v", n, err)
        }
    }
    frames,err:=f.Fragment(packet)
    if err!=nil || len(frames)!=2 { t.Fatalf("real Go MTU+1: %v, %d",err,len(frames)) }
    for i,want := range [][]byte{r0LinkFixture(t,"link64-first"),r0LinkFixture(t,"link64-last")} {
        if !bytes.Equal(frames[i],want) {
            t.Fatalf("fragment %d actual old Go=%x want locked=%x",i,frames[i],want)
        }
        if len(frames[i])>64 { t.Fatal("wire greater than LINK budget") }
    }
    reasm,err:=NewReassembler(64)
    if err!=nil { t.Fatal(err) }
    now:=time.Unix(1,0)
    if got,done,err:=reasm.Push(frames[1],now);err!=nil || done || got!=nil {
        t.Fatalf("tail first prematurely completed: %x %v %v",got,done,err)
    }
    got,done,err:=reasm.Push(frames[0],now)
    if err!=nil || !done || !bytes.Equal(got,packet) {
        t.Fatalf("real Go actual reassembly wrong: %v %v len=%d",err,done,len(got))
    }
}

func TestR0LinkPinnedRealGoMagicWFandInvalidLength(t *testing.T) {
    f,err:=NewFragmenter(64)
    if err!=nil {t.Fatal(err)}
    magic:=[]byte("WBDLFRG1")
    a,err:=f.Fragment(magic)
    if err!=nil || len(a)!=1 || !bytes.Equal(a[0],r0LinkFixture(t,"link-magic-escaped")) {
        t.Fatalf("reserved magic was not escaped: %x %v",a,err)
    }
    adaptive,err:=NewFragmenter(64)
    if err!=nil {t.Fatal(err)}
    wf:=[]byte("WF!")
    b,err:=adaptive.FragmentAvoidFEC(wf)
    if err!=nil || len(b)!=1 || !bytes.Equal(b[0],r0LinkFixture(t,"link-wf-escaped")) {
        t.Fatalf("adaptive WF escape diverged from old Go: %x %v",b,err)
    }
    fixed,err:=NewFragmenter(64)
    if err!=nil {t.Fatal(err)}
    raw,err:=fixed.Fragment(wf)
    if err!=nil || len(raw)!=1 || !bytes.Equal(raw[0],wf) {
        t.Fatalf("fixed/off wrongly escaped WF: %x %v",raw,err)
    }
    rx,err:=NewReassembler(64)
    if err!=nil {t.Fatal(err)}
    corrupted:=append([]byte(nil),r0LinkFixture(t,"link64-first")...)
    corrupted[13]=0 // zero count
    got,done,err:=rx.Push(corrupted,time.Unix(1,0))
    if err==nil || done || got!=nil {t.Fatalf("invalid LINK count accepted: %x %v %v",got,done,err)}
}
