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

// The mandatory v2 grammar is inside authenticated TLS1.3 ApplicationData.
// No legacy branch: off-mode also gets an independent random control tail.
func TestH2202MandatoryEncryptedAdmissionRequestAndReplyRandomLengths(t *testing.T){
    policy:=v4TestPolicy(1,CipherChaCha)
    req:=AdmissionRequest{
        RecordVersion:V4RecordVersion,Policy:policy,DesiredLanes:1,LaneID:1,
        TunnelID:[]byte("0123456789abcdef"),ClientLimit:1400,
        Username:"alice",Password:"secret",
    }
    answer:=AdmissionResult{
        RecordVersion:V4RecordVersion,Policy:policy,DesiredLanes:1,LaneID:1,
        TunnelID:[]byte("0123456789abcdef"),ClientLimit:1400,ServerLimit:1400,
        IncarnationNonce:[16]byte{1},
    }
    v3req:=req;v3req.RecordVersion=RecordVersionV3
    rawReq,e:=marshalAdmissionRequest(v3req)
    if e!=nil{t.Fatal(e)}
    reqBase:=len(rawReq)+v4ExtensionLen
    v3reply:=answer;v3reply.RecordVersion=RecordVersionV3
    rawReply,e:=marshalAdmissionReply(v3reply)
    if e!=nil{t.Fatal(e)}
    replyBase:=len(rawReply)+v4ExtensionLen
    reqLengths:=map[int]bool{}
    replyLengths:=map[int]bool{}
    for _,mode:=range []uint8{0,1,2}{
        ext:=V4Extension{Features:v4RequiredFeatures,Epoch:[16]byte{4},StartupPadding:mode}
        for trial:=0;trial<8;trial++{
            request,e:=v4RequestWire(req,ext)
            if e!=nil{t.Fatal(e)}
            n:=int(binary.BigEndian.Uint16(request[reqBase:reqBase+2]))
            if n<v4AdmissionPadMin||n>v4AdmissionPadMax||len(request)!=reqBase+2+n{
                t.Fatalf("bad request tail: mode=%d len=%d pad=%d",mode,len(request),n)
            }
            rr:=bytes.NewReader(append(append([]byte{},request...),0xee))
            got,decoded,e:=v4ReadRequest(rr)
            if e!=nil||decoded!=ext||got.Username!=req.Username||
               got.RecordVersion!=V4RecordVersion||rr.Len()!=1{
                t.Fatalf("v2 request not exactly consumed: %+v %v remains=%d",decoded,e,rr.Len())
            }
            reqLengths[len(request)]=true
            reply,e:=v4ReplyWire(answer,ext)
            if e!=nil{t.Fatal(e)}
            n=int(binary.BigEndian.Uint16(reply[replyBase:replyBase+2]))
            if n<v4AdmissionPadMin||n>v4AdmissionPadMax||len(reply)!=replyBase+2+n{
                t.Fatalf("bad reply tail: mode=%d len=%d pad=%d",mode,len(reply),n)
            }
            rr=bytes.NewReader(append(append([]byte{},reply...),0xed))
            gotAnswer,echo,e:=v4ReadReply(rr,req)
            if e!=nil||echo!=ext||gotAnswer.RecordVersion!=V4RecordVersion||rr.Len()!=1{
                t.Fatalf("v2 reply not exactly consumed: %+v %v remains=%d",echo,e,rr.Len())
            }
            replyLengths[len(reply)]=true
        }
    }
    if len(reqLengths)<4||len(replyLengths)<4{
        t.Fatalf("TLS protected controls had fixed lengths: request=%d reply=%d",len(reqLengths),len(replyLengths))
    }
}

func TestH2202StrictSingleVersionAndNoUnpaddedDowngrade(t *testing.T){
    ext:=V4Extension{Features:v4RequiredFeatures,Epoch:[16]byte{2},StartupPadding:2}
    raw,e:=v4Encode(ext)
    if e!=nil{t.Fatal(e)}
    if binary.BigEndian.Uint16(raw[:2])!=v4ControlVersion||raw[23]!=2{
        t.Fatal("mandatory protocol version / client mode not encoded")
    }
    for _,mutate:=range []func([]byte){
        func(b []byte){b[0]=0;b[1]=1}, // former v1 cannot negotiate
        func(b []byte){b[0]=0;b[1]=3}, // unknown future version
        func(b []byte){b[23]=3}, // unknown padding policy
    }{
        changed:=raw
        mutate(changed[:])
        if _,e:=v4Decode(changed[:]);!errors.Is(e,ErrAdmissionParams){
            t.Fatalf("old/invalid extension accepted: %v",e)
        }
    }
    for _,mode:=range []uint8{0,1,2}{
        good:=ext;good.StartupPadding=mode
        b,e:=v4Encode(good)
        if e!=nil{t.Fatal(e)}
        decoded,e:=v4Decode(b[:])
        if e!=nil||decoded!=good{t.Fatalf("v2 mode=%d failed: %+v %v",mode,decoded,e)}
    }
    for _,wire:=range [][]byte{
        nil,{0,31},{1,245},{0,32,1}, // no length, too short, >500, truncated
    }{
        if e:=v4ConsumeEncryptedAdmissionPad(bytes.NewReader(wire));e==nil{
            t.Fatalf("accepted malformed required TLS control tail: %x",wire)
        }
    }
    if _,e:=v4AppendEncryptedAdmissionPad(nil,io.LimitReader(bytes.NewReader(nil),0));e==nil{
        t.Fatal("failed CSPRNG source allowed a control message")
    }
    if _,e:=v4AppendEncryptedAdmissionPad(nil,nil);!errors.Is(e,ErrAdmissionParams){
        t.Fatalf("nil entropy source did not fail closed: %v",e)
    }
}

func TestH2202RejectedTLSReplyIsAlsoRandomizedAndFullyConsumed(t *testing.T){
    statuses:=[]struct{status byte;expected error}{
        {admissionAuthFail,ErrAdmissionAuth},
        {admissionParamFail,ErrAdmissionParams},
        {admissionVersionFail,ErrAdmissionVersion},
    }
    distinct:=map[int]bool{}
    for _,tc:=range statuses{
        for i:=0;i<8;i++{
            var output bytes.Buffer
            if e:=v4WriteFailure(&output,tc.status);e!=nil{t.Fatal(e)}
            wire:=output.Bytes()
            if len(wire)<1+2+v4AdmissionPadMin||len(wire)>1+2+v4AdmissionPadMax||
               int(binary.BigEndian.Uint16(wire[1:3]))!=len(wire)-3{
                t.Fatalf("bad encrypted failure length status=%d len=%d",tc.status,len(wire))
            }
            r:=bytes.NewReader(append(append([]byte{},wire...),0xf1))
            _,_,e:=v4ReadReply(r,AdmissionRequest{})
            if !errors.Is(e,tc.expected)||r.Len()!=1{
                t.Fatalf("wrong failure status/consumption: %v remaining=%d",e,r.Len())
            }
            distinct[len(wire)]=true
        }
    }
    if len(distinct)<4{t.Fatalf("failure replies have fixed size, lengths=%d",len(distinct))}
    for _,bad:=range [][]byte{{admissionAuthFail}, {admissionAuthFail,0,31}, {admissionAuthFail,1,245}}{
        _,_,e:=v4ReadReply(bytes.NewReader(bad),AdmissionRequest{})
        if e==nil||errors.Is(e,ErrAdmissionAuth){
            t.Fatalf("unframed legacy short reject accepted: %x %v",bad,e)
        }
    }
}

func TestH2202RealTLSOriginalCredentialsPadChoiceAndFrozenServerAuthority(t *testing.T){
    for _,mode:=range []uint8{0,1,2}{
        t.Run([]string{"off","tls","flows"}[mode],func(t *testing.T){
            cert:=makeServerCert(t)
            key:=[]byte("0123456789abcdef0123456789abcdef")
            assoc,peer:=newAssociationPeer(t)
            defer assoc.Close();defer peer.Close()
            epochs,e:=NewV4EpochStore(2)
            if e!=nil{t.Fatal(e)}
            type result struct{s *V4ServerSession;err error}
            done:=make(chan result,1)
            go func(){
                s,e:=EstablishServerV4(context.Background(),assoc,ServerAdmissionConfig{
                    TLS:ServerConfig{ServerName:"target.test",RouteKey:key,
                        TLSConfig:&tls.Config{Certificates:[]tls.Certificate{cert}},Timeout:3*time.Second},
                    ExpectedUsername:"alice",ExpectedPassword:"secret",ServerLimit:1400,
                },V4ServerOptions{DataPlaneReady:true,Epochs:epochs})
                done<-result{s,e}
            }()
            client,ce:=EstablishClientV4(context.Background(),peer,ClientAdmissionConfig{
                TLS:ClientConfig{ServerName:"target.test",RouteKey:key,
                    RootCAs:v4TestRoots(cert),Timeout:3*time.Second},
                Username:"alice",Password:"secret",TunnelID:[]byte("0123456789abcdef"),
                ClientLimit:1400,DesiredLanes:1,LaneID:1,Policy:v4TestPolicy(1,CipherChaCha),
            },V4ClientOptions{DataPlaneReady:true,StartupPadding:mode})
            select {
            case sr:=<-done:
                if ce!=nil||sr.err!=nil||client==nil||sr.s==nil{
                    t.Fatalf("v2 real TLS peer failure: client=%v server=%v",ce,sr.err)
                }
                cm,e:=client.AuthenticatedStartupPaddingMode()
                if e!=nil||cm!=mode{t.Fatalf("bad TLS confirmed client mode=%d: %v",cm,e)}
                sm,e:=sr.s.AuthenticatedStartupPaddingMode()
                if e!=nil||sm!=mode{t.Fatalf("bad credential-checked server mode=%d: %v",sm,e)}
                if client.TLS.Keys!=sr.s.TLS.Keys{t.Fatal("KDF exporter differs")}
                sr.s.verifiedStartupPadding=(mode+1)%3
                if _,e=sr.s.ColdSnapshot();!errors.Is(e,ErrAdmissionParams){
                    t.Fatalf("post-TLS mode mutation minted Rust owner: %v",e)
                }
            case <-time.After(6*time.Second):
                t.Fatal("real TLS V2 peer blocked")
            }
        })
    }
}
func TestH2202RealTLSBadPasswordReceivesRandomizedProtectedReject(t *testing.T){
    cert:=makeServerCert(t)
    key:=[]byte("0123456789abcdef0123456789abcdef")
    assoc,peer:=newAssociationPeer(t)
    defer assoc.Close();defer peer.Close()
    store,e:=NewV4EpochStore(1)
    if e!=nil{t.Fatal(e)}
    done:=make(chan error,1)
    go func(){
        _,e:=EstablishServerV4(context.Background(),assoc,ServerAdmissionConfig{
            TLS:ServerConfig{ServerName:"target.test",RouteKey:key,
                TLSConfig:&tls.Config{Certificates:[]tls.Certificate{cert}},Timeout:3*time.Second},
            ExpectedUsername:"alice",ExpectedPassword:"correct",ServerLimit:1400,
        },V4ServerOptions{DataPlaneReady:true,Epochs:store})
        done<-e
    }()
    _,ce:=EstablishClientV4(context.Background(),peer,ClientAdmissionConfig{
        TLS:ClientConfig{ServerName:"target.test",RouteKey:key,RootCAs:v4TestRoots(cert),Timeout:3*time.Second},
        Username:"alice",Password:"wrong",TunnelID:[]byte("0123456789abcdef"),
        ClientLimit:1400,DesiredLanes:1,LaneID:1,Policy:v4TestPolicy(1,CipherChaCha),
    },V4ClientOptions{DataPlaneReady:true,StartupPadding:2})
    select {
    case se:=<-done:
        if !errors.Is(ce,ErrAdmissionAuth)||!errors.Is(se,ErrAdmissionAuth){
            t.Fatalf("bad credentials not rejected after framed encrypted response: client=%v server=%v",ce,se)
        }
    case <-time.After(6*time.Second):t.Fatal("bad-password rejection timeout")
    }
}
