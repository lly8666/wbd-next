package realityfront

import (
    "bytes"
    "context"
    "crypto/tls"
    "encoding/binary"
    "errors"
    "io"
    "testing"
    "time"
)

// Every V2 request AND reply is still one TLS-protected application message,
// with a self-delimited random suffix. The decoder must consume precisely it:
// leftover TLS bytes can otherwise be mistaken for a native Rust record.
func TestH2200EncryptedAdmissionTwoWaysHaveBoundedVariableLengths(t *testing.T){
    policy:=v4TestPolicy(1,CipherChaCha)
    req:=AdmissionRequest{
        RecordVersion:V4RecordVersion,Policy:policy,DesiredLanes:1,LaneID:1,
        TunnelID:[]byte("0123456789abcdef"),ClientLimit:1400,
        Username:"alice",Password:"secret",
    }
    result:=AdmissionResult{
        RecordVersion:V4RecordVersion,Policy:policy,DesiredLanes:1,LaneID:1,
        TunnelID:[]byte("0123456789abcdef"),ClientLimit:1400,ServerLimit:1400,
        IncarnationNonce:[16]byte{1},
    }
    reqLengths:=map[int]bool{}
    replyLengths:=map[int]bool{}
    for _,mode:=range []uint8{0,1,2}{
        ext:=V4Extension{Features:v4RequiredFeatures,Epoch:[16]byte{4},
            StartupPadding:mode,ControlPadded:true}
        for trial:=0;trial<8;trial++{
            request,err:=v4RequestWire(req,ext)
            if err!=nil{t.Fatal(err)}
            r:=bytes.NewReader(append(append([]byte{},request...),0xee))
            got,dec,err:=v4ReadRequest(r)
            if err!=nil||dec!=ext||got.Username!=req.Username||
                got.RecordVersion!=V4RecordVersion||r.Len()!=1{
                t.Fatalf("V2 request decode/mode/tail role=%d len=%d remaining=%d err=%v",mode,len(request),r.Len(),err)
            }
            reqLengths[len(request)]=true
            reply,err:=v4ReplyWire(result,ext)
            if err!=nil{t.Fatal(err)}
            r=bytes.NewReader(append(append([]byte{},reply...),0xed))
            back,echo,err:=v4ReadReply(r,req)
            if err!=nil||echo!=ext||back.RecordVersion!=V4RecordVersion||r.Len()!=1{
                t.Fatalf("V2 reply decode/mode/tail role=%d len=%d remaining=%d err=%v",mode,len(reply),r.Len(),err)
            }
            replyLengths[len(reply)]=true
            // The 2B suffix-length header and 32..500 random bytes
            // are always INSIDE the existing protected request/reply.
            v1:=ext;v1.ControlPadded=false;v1.StartupPadding=0
            baseline,err:=v4RequestWire(req,v1)
            if err!=nil{t.Fatal(err)}
            if n:=len(request)-len(baseline)-2;n<v4AdmissionPadMin||n>v4AdmissionPadMax{
                t.Fatalf("out of bound client pad %d",n)
            }
            baseline,err=v4ReplyWire(result,v1)
            if err!=nil{t.Fatal(err)}
            if n:=len(reply)-len(baseline)-2;n<v4AdmissionPadMin||n>v4AdmissionPadMax{
                t.Fatalf("out of bound server pad %d",n)
            }
        }
    }
    if len(reqLengths)<4||len(replyLengths)<4{
        t.Fatalf("encrypted controls unexpectedly have fixed length: request=%d reply=%d",
            len(reqLengths),len(replyLengths))
    }
}

func TestH2200EncryptedControlPaddingStrictV1V2AndTruncation(t *testing.T){
    ext:=V4Extension{Features:v4RequiredFeatures,Epoch:[16]byte{2},ControlPadded:true,StartupPadding:2}
    raw,err:=v4Encode(ext)
    if err!=nil{t.Fatal(err)}
    if binary.BigEndian.Uint16(raw[:2])!=2||raw[23]!=2{t.Fatal("V2 mode not in protected extension")}
    for _,bad:=range []func([]byte){
        func(b []byte){b[23]=3},
        func(b []byte){b[0]=0;b[1]=3},
    }{
        changed:=raw
        bad(changed[:])
        if _,e:=v4Decode(changed[:]);!errors.Is(e,ErrAdmissionParams){t.Fatalf("accepted V2 invalid: %v",e)}
    }
    old:=ext;old.ControlPadded=false;old.StartupPadding=0
    oldWire,err:=v4Encode(old)
    if err!=nil{t.Fatal(err)}
    if binary.BigEndian.Uint16(oldWire[:2])!=1||oldWire[23]!=0{t.Fatal("legacy v1 no longer byte-for-byte old control")}
    if got,e:=v4Decode(oldWire[:]);e!=nil||got!=old{t.Fatalf("legacy roundtrip: %v %v",got,e)}
    oldWire[23]=1
    if _,e:=v4Decode(oldWire[:]);!errors.Is(e,ErrAdmissionParams){t.Fatalf("legacy v1 accepts a forged mode: %v",e)}
    if _,e:=v4Encode(V4Extension{Features:v4RequiredFeatures,StartupPadding:2});!errors.Is(e,ErrAdmissionUnsupported){
        t.Fatalf("unversioned mode allowed: %v",e)
    }
    // Short/malformed random suffixes cannot be silently consumed as a
    // different record; no downgrade to V1 and no side effects.
    for _,wire:=range [][]byte{
        nil,{0,31},{1,245},{0,32,1}, // empty, low, high, truncated
    }{
        if e:=v4ConsumeEncryptedAdmissionPad(bytes.NewReader(wire),ext);e==nil{
            t.Fatalf("accepted short/invalid protected suffix: %x",wire)
        }
    }
    if e:=v4ConsumeEncryptedAdmissionPad(bytes.NewReader(nil),old);e!=nil{
        t.Fatalf("V1 incorrectly expects suffix: %v",e)
    }
    if _,e:=v4AppendEncryptedAdmissionPad(nil,ext,io.LimitReader(bytes.NewReader(nil),0));e==nil{
        t.Fatal("failed CSPRNG reader is not fail closed")
    }
}

func TestH2200RealTLSClientPaddingChoiceConfirmedPerServerSession(t *testing.T){
    for _,mode:=range []uint8{0,1,2}{
        t.Run([]string{"off","tls","flows"}[mode],func(t *testing.T){
            cert:=makeServerCert(t)
            routeKey:=[]byte("0123456789abcdef0123456789abcdef")
            assoc,peer:=newAssociationPeer(t)
            defer assoc.Close();defer peer.Close()
            store,e:=NewV4EpochStore(2)
            if e!=nil{t.Fatal(e)}
            type reply struct{s *V4ServerSession;err error}
            server:=make(chan reply,1)
            go func(){
                s,e:=EstablishServerV4(context.Background(),assoc,ServerAdmissionConfig{
                    TLS:ServerConfig{ServerName:"target.test",RouteKey:routeKey,
                        TLSConfig:&tls.Config{Certificates:[]tls.Certificate{cert}},Timeout:3*time.Second},
                    ExpectedUsername:"alice",ExpectedPassword:"secret",ServerLimit:1400,
                },V4ServerOptions{DataPlaneReady:true,Epochs:store})
                server<-reply{s,e}
            }()
            client,ce:=EstablishClientV4(context.Background(),peer,ClientAdmissionConfig{
                TLS:ClientConfig{ServerName:"target.test",RouteKey:routeKey,
                    RootCAs:v4TestRoots(cert),Timeout:3*time.Second},
                Username:"alice",Password:"secret",TunnelID:[]byte("0123456789abcdef"),
                ClientLimit:1400,DesiredLanes:1,LaneID:1,Policy:v4TestPolicy(1,CipherChaCha),
            },V4ClientOptions{DataPlaneReady:true,ControlPadded:true,StartupPadding:mode})
            select {
            case sr:=<-server:
                if ce!=nil||sr.err!=nil||client==nil||sr.s==nil{
                    t.Fatalf("real TLS V2 request/echo failed: client=%v server=%v",ce,sr.err)
                }
                cm,e:=client.AuthenticatedStartupPaddingMode()
                if e!=nil||cm!=mode{t.Fatalf("client protected echo mismatch got=%d: %v",cm,e)}
                sm,e:=sr.s.AuthenticatedStartupPaddingMode()
                if e!=nil||sm!=mode{t.Fatalf("server accepted mode differs got=%d: %v",sm,e)}
                if client.TLS.Keys!=sr.s.TLS.Keys{
                    t.Fatal("actual original TLS exporter transcript keys disagree")
                }
                // A forged post-TLS mutable selector cannot authorize Rust.
                sr.s.verifiedStartupPadding=(mode+1)%3
                if _,e=sr.s.ColdSnapshot();!errors.Is(e,ErrAdmissionParams){
                    t.Fatalf("server cold snapshot accepted mutable setting: %v",e)
                }
            case <-time.After(6*time.Second):
                t.Fatal("real TLS V2 response timeout")
            }
        })
    }
}
