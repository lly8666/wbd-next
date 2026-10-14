package fec

import (
    "bytes"
    _ "embed"
    "encoding/hex"
    "strings"
    "testing"
    "time"
)

//go:embed r0_link_fec_wire_v1.txt
var r0PinnedFecWire string

func r0FecFixture(t *testing.T,name string) []byte {
    t.Helper()
    for _,line:=range strings.Split(r0PinnedFecWire,"\n"){
        if line=="" || strings.HasPrefix(line,"#"){continue}
        parts:=strings.Split(line,"|")
        if len(parts)!=2 {t.Fatalf("invalid fixture row %q",line)}
        if parts[0]!=name {continue}
        raw,err:=hex.DecodeString(parts[1])
        if err!=nil{t.Fatal(err)}
        return raw
    }
    t.Fatalf("missing fixture %s",name)
    return nil
}

func TestR0FecPinnedActualStreamingSourceAndFinalParityHeaders(t *testing.T){
    // Real original Go 20:4 systematic codec, NOT a fake/synthetic Rust GF codec.
    codec:=NewReedSolomon20x20()
    encoder,err:=NewFastBlockEncoderWithParity(codec,64,time.Second,0x01020304,4)
    if err!=nil{t.Fatal(err)}
    emitted,err:=encoder.Add([]byte{0xaa,0xbb,0xcc},time.Unix(1,0))
    if err!=nil||len(emitted)!=1 {t.Fatalf("source not emitted instantly: %v %d",err,len(emitted))}
    source:=append([]byte(nil),emitted[0]...)
    if !bytes.Equal(source,r0FecFixture(t,"fec-source")) {
        t.Fatalf("actual old Go source wire=%x vs pinned fixture=%x",source,r0FecFixture(t,"fec-source"))
    }
    if len(source)!=59 {t.Fatal("source 56B header plus 3B payload")}
    parity,err:=encoder.Flush()
    if err!=nil || len(parity)!=1 {t.Fatalf("real Go k=1 parity count wrong: %v %d",err,len(parity))}
    if len(parity[0])!=59 {t.Fatalf("real Go parity len=%d not 59",len(parity[0]))}
    wantHeader:=r0FecFixture(t,"fec-final-parity-header-only")
    if !bytes.Equal(parity[0][:HeaderSize],wantHeader) {
        t.Fatalf("old Go final parity header=%x want=%x",parity[0][:HeaderSize],wantHeader)
    }
    if parity[0][10]!=4 || parity[0][11]!=1 || parity[0][8]!=20 {
        t.Fatal("real Go header failed to preserve configured parity and shortened k")
    }
    if _,err:=ParseBlockHeader(parity[0][:HeaderSize]);err!=nil {
        t.Fatalf("old Go final FEC header did not parse: %v",err)
    }
}

func TestR0FecPinnedRealGoProfilesWireBounds(t *testing.T){
    for _,p:=range SupportedParityShards(){
        encoder,err:=NewFastBlockEncoderWithParity(NewReedSolomon20x20(),64,time.Second,2,p)
        if err!=nil{t.Fatal(err)}
        source,err:=encoder.Add([]byte{0x11},time.Unix(1,0))
        if err!=nil || len(source)!=1 || len(source[0])!=HeaderSize+1 {
            t.Fatalf("real systematic profile 20:%d early delivery %v",p,err)
        }
        if source[0][10]!=byte(p) || source[0][14]!=0 || source[0][15]!=1 {
            t.Fatalf("profile/streaming metadata wrong: %x",source[0][:16])
        }
        repairs,err:=encoder.Flush()
        if err!=nil || len(repairs)!=1 || len(repairs[0])!=HeaderSize+1 {
            t.Fatalf("real Go shortened parity profile 20:%d wrong %v",p,err)
        }
        if repairs[0][10]!=byte(p) || repairs[0][11]!=1 || repairs[0][8]!=20 {
            t.Fatalf("final header lied about configured geometry: %x",repairs[0][:16])
        }
    }
}
