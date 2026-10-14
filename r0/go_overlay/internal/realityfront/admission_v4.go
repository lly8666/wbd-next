// Package realityfront: R0 V4 protected admission opt-in entrypoints.
//
// This production (non _test) overlay is copied into the exact pinned Go
// control module during R0 Actions. It reuses the mature TLS handshake and
// FakeTCP transition; it DOES NOT enable V4 in old V2/V3 callers, or claim
// that the Rust data-plane receipt/Game capabilities have shipped.
package realityfront

import (
    "bytes"
    "context"
    "crypto/rand"
    "crypto/sha256"
    "encoding/binary"
    "errors"
    "io"
    "net"
    "sync"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
    "github.com/lly8666/wobuzhidao/internal/tlsrecord"
    "golang.org/x/crypto/hkdf"
)

const (
    V4RecordVersion uint16 = 4
    v4ExtensionLen = 24
    v4FeatureReceipt = uint16(1)
    v4FeatureSharedGame = uint16(2)
    v4RequiredFeatures = v4FeatureReceipt | v4FeatureSharedGame
    v4FeedbackPages = byte(8)
)

type V4Extension struct {
    Features uint16
    Epoch [16]byte
}

func v4Encode(e V4Extension) ([24]byte, error) {
    var buf [24]byte
    if e.Features != v4RequiredFeatures { return buf, ErrAdmissionUnsupported }
    binary.BigEndian.PutUint16(buf[0:2], 1)
    binary.BigEndian.PutUint16(buf[2:4], e.Features)
    copy(buf[4:20], e.Epoch[:])
    buf[20] = v4FeedbackPages
    return buf, nil
}

func v4Decode(raw []byte) (V4Extension,error) {
    var e V4Extension
    if len(raw)!=v4ExtensionLen { return e,ErrAdmissionParams }
    if binary.BigEndian.Uint16(raw[:2])!=1 || raw[20]!=v4FeedbackPages ||
       raw[21]!=0 || raw[22]!=0 || raw[23]!=0 { return e,ErrAdmissionParams }
    e.Features=binary.BigEndian.Uint16(raw[2:4])
    if e.Features!=v4RequiredFeatures { return V4Extension{},ErrAdmissionUnsupported }
    copy(e.Epoch[:],raw[4:20])
    return e,nil
}

// Callers must positively attest receipt/Game data-plane readiness before
// opt-in. The bridge MUST NOT set Ready until matching Rust capabilities exist.
type V4ClientOptions struct {
    DataPlaneReady bool
    Epoch [16]byte // zero only for the first lane of a new logical tunnel
}
type V4ServerOptions struct {
    DataPlaneReady bool
    Epochs *V4EpochStore // shared by all lanes of the same server instance
}

type V4ClientSession struct {
    *ClientAdmissionSession
    Epoch [16]byte
}
type V4ServerSession struct {
    *ServerAdmissionSession
    Epoch [16]byte
}

type v4Entry struct {
    epoch [16]byte
    active bool
    lanes uint8 // 1<<lane (IDs 1..4)
    pending uint8
}
// Per-server explicit-lifecycle store. Session close must call ReleaseLane;
// it must not rely on GC, wall-clock or TunnelID alone as a generation.
type V4EpochStore struct {
    mu sync.Mutex
    entries map[string]*v4Entry
    max int
}
func NewV4EpochStore(max int) (*V4EpochStore,error) {
    if max<1 || max>4096 { return nil,ErrAdmissionParams }
    return &V4EpochStore{entries:make(map[string]*v4Entry),max:max},nil
}
func v4Identity(username string,tunnelID []byte) string {
    return username + "/" + string(tunnelID)
}
func (s *V4EpochStore) ReleaseLane(username string,tunnelID []byte,lane uint8,epoch [16]byte) error {
    if s==nil || !validAdmissionLaneID(lane) {return ErrAdmissionParams}
    key:=v4Identity(username,tunnelID)
    s.mu.Lock()
    defer s.mu.Unlock()
    e,ok:=s.entries[key]
    bit:=uint8(1<<lane)
    if !ok || !e.active || e.epoch!=epoch || e.lanes&bit==0 {return ErrAdmissionParams}
    e.lanes &^= bit
    if e.lanes==0 && e.pending==0 {delete(s.entries,key)}
    return nil
}
func (s *V4EpochStore) prepare(username string,tunnelID []byte,lane uint8,want [16]byte,rng io.Reader)([16]byte,func(bool),error) {
    var zero [16]byte
    if s==nil || rng==nil || !validAdmissionLaneID(lane) || len(tunnelID)!=16 {return zero,nil,ErrAdmissionParams}
    key:=v4Identity(username,tunnelID)
    bit:=uint8(1<<lane)
    s.mu.Lock()
    defer s.mu.Unlock()
    e,found:=s.entries[key]
    newTunnel:=want==zero
    if newTunnel {
        if found || len(s.entries)>=s.max {return zero,nil,ErrAdmissionParams}
        var epoch [16]byte
        if _,err:=io.ReadFull(rng,epoch[:]);err!=nil{return zero,nil,err}
        if epoch==zero {return zero,nil,ErrAdmissionParams}
        e=&v4Entry{epoch:epoch,pending:bit}
        s.entries[key]=e
    } else {
        if !found || !e.active || e.epoch!=want || e.pending&bit!=0 || e.lanes&bit!=0 {
            return zero,nil,ErrAdmissionParams
        }
        e.pending|=bit
    }
    actual:=e.epoch
    // Idempotent transaction end, with an explicit commit AFTER DetachTransition.
    ended:=false
    finish:=func(commit bool) {
        s.mu.Lock()
        defer s.mu.Unlock()
        if ended {return}
        ended=true
        current:=s.entries[key]
        if current!=e {return}
        e.pending &^= bit
        if commit {
            e.lanes |= bit
            e.active=true
        } else if newTunnel || (!e.active && e.pending==0) {
            delete(s.entries,key)
        }
    }
    return actual,finish,nil
}

func v4RequestWire(req AdmissionRequest,ext V4Extension)([]byte,error) {
    req.RecordVersion=RecordVersionV3
    raw,err:=marshalAdmissionRequest(req)
    if err!=nil{return nil,err}
    block,err:=v4Encode(ext)
    if err!=nil{return nil,err}
    binary.BigEndian.PutUint16(raw[4:6],V4RecordVersion)
    return append(raw,block[:]...),nil
}
func v4ReadRequest(r io.Reader)(AdmissionRequest,V4Extension,error) {
    var zero V4Extension
    var hdr [admissionRequestLen]byte
    if _,err:=io.ReadFull(r,hdr[:]);err!=nil{return AdmissionRequest{},zero,err}
    if binary.BigEndian.Uint16(hdr[4:6])!=V4RecordVersion {return AdmissionRequest{},zero,ErrAdmissionVersion}
    tunnelLen:=int(binary.BigEndian.Uint16(hdr[9:11]))
    userLen:=int(binary.BigEndian.Uint16(hdr[11:13]))
    passLen:=int(binary.BigEndian.Uint16(hdr[13:15]))
    if tunnelLen!=16 || userLen<1 || userLen>maxAdmissionUserLen || passLen<1 || passLen>maxAdmissionPassLen {
        return AdmissionRequest{},zero,ErrAdmissionParams
    }
    lease:=0
    switch string(hdr[:4]) {
    case admissionMagic:
    case leaseAdmissionMagic: lease=17
    default: return AdmissionRequest{},zero,ErrAdmissionParams
    }
    suffix:=make([]byte,tunnelLen+userLen+passLen+lease+policyV3Len+v4ExtensionLen)
    if _,err:=io.ReadFull(r,suffix);err!=nil{return AdmissionRequest{},zero,err}
    ext,err:=v4Decode(suffix[len(suffix)-v4ExtensionLen:])
    if err!=nil{return AdmissionRequest{},zero,err}
    base:=append(append([]byte{},hdr[:]...),suffix[:len(suffix)-v4ExtensionLen]...)
    binary.BigEndian.PutUint16(base[4:6],RecordVersionV3)
    req,err:=readAdmissionRequest(bytes.NewReader(base))
    if err!=nil{return AdmissionRequest{},zero,err}
    req.RecordVersion=V4RecordVersion
    return req,ext,nil
}

func v4ReplyWire(result AdmissionResult,ext V4Extension)([]byte,error) {
    result.RecordVersion=RecordVersionV3
    raw,err:=marshalAdmissionReply(result)
    if err!=nil{return nil,err}
    block,err:=v4Encode(ext)
    if err!=nil{return nil,err}
    binary.BigEndian.PutUint16(raw[1:3],V4RecordVersion)
    return append(raw,block[:]...),nil
}
func v4ReadReply(r io.Reader,req AdmissionRequest)(AdmissionResult,V4Extension,error) {
    var zero V4Extension
    var header [admissionReplyLen]byte
    if _,err:=io.ReadFull(r,header[:1]);err!=nil{return AdmissionResult{},zero,err}
    if header[0]!=admissionOK {
        switch header[0] {
        case admissionAuthFail:return AdmissionResult{},zero,ErrAdmissionAuth
        case admissionVersionFail:return AdmissionResult{},zero,ErrAdmissionVersion
        default:return AdmissionResult{},zero,ErrAdmissionParams
        }
    }
    if _,err:=io.ReadFull(r,header[1:]);err!=nil{return AdmissionResult{},zero,err}
    if binary.BigEndian.Uint16(header[1:3])!=V4RecordVersion {return AdmissionResult{},zero,ErrAdmissionVersion}
    tunnelLen:=int(binary.BigEndian.Uint16(header[24:26]))
    if tunnelLen!=16 {return AdmissionResult{},zero,ErrAdmissionParams}
    extra:=policyV3Len+v4ExtensionLen
    if req.AutoLease {extra+=4}
    tail:=make([]byte,tunnelLen+extra)
    if _,err:=io.ReadFull(r,tail);err!=nil{return AdmissionResult{},zero,err}
    ext,err:=v4Decode(tail[len(tail)-v4ExtensionLen:])
    if err!=nil{return AdmissionResult{},zero,err}
    original:=append(append([]byte{},header[:]...),tail[:len(tail)-v4ExtensionLen]...)
    binary.BigEndian.PutUint16(original[1:3],RecordVersionV3)
    expectedReq:=req
    expectedReq.RecordVersion=RecordVersionV3
    answer,err:=readAdmissionReply(bytes.NewReader(original),expectedReq)
    if err!=nil{return AdmissionResult{},zero,err}
    answer.RecordVersion=V4RecordVersion
    return answer,ext,nil
}

func v4DeriveRecordKeys(exporter keyingMaterialExporter,result AdmissionResult,ext V4Extension)(tlsrecord.KeyPair,error) {
    var empty tlsrecord.KeyPair
    block,err:=v4Encode(ext)
    if err!=nil{return empty,err}
    policy,err:=result.Policy.Encode()
    if err!=nil{return empty,err}
    contextBytes:=make([]byte,0,2+16+2+16+2+2+10+24)
    var short [2]byte
    binary.BigEndian.PutUint16(short[:],V4RecordVersion)
    contextBytes=append(contextBytes,short[:]...)
    contextBytes=append(contextBytes,result.IncarnationNonce[:]...)
    binary.BigEndian.PutUint16(short[:],uint16(len(result.TunnelID)))
    contextBytes=append(contextBytes,short[:]...)
    contextBytes=append(contextBytes,result.TunnelID...)
    binary.BigEndian.PutUint16(short[:],result.ClientLimit)
    contextBytes=append(contextBytes,short[:]...)
    binary.BigEndian.PutUint16(short[:],result.ServerLimit)
    contextBytes=append(contextBytes,short[:]...)
    contextBytes=append(contextBytes,policy[:]...)
    contextBytes=append(contextBytes,block[:]...)
    hash:=sha256.Sum256(contextBytes)
    master,err:=exporter.ExportKeyingMaterial(tlsrecord.ExporterLabel,hash[:],32)
    if err!=nil{return empty,err}
    suite:=""
    switch result.Policy.Cipher {
    case CipherChaCha:suite="chacha20-poly1305"
    case CipherAES128:suite="aes-128-gcm"
    case CipherAES256:suite="aes-256-gcm"
    default:return empty,ErrAdmissionParams
    }
    derive:=func(dir string)(tlsrecord.Keys,error){
        var out tlsrecord.Keys
        var material [76]byte
        info:=[]byte("WBD-TLSLIKE-V4/"+suite+"/"+dir)
        if _,err:=io.ReadFull(hkdf.New(sha256.New,master,result.IncarnationNonce[:],info),material[:]);err!=nil {
            return out,err
        }
        copy(out.AEADKey[:],material[:32])
        copy(out.IV[:],material[32:44])
        copy(out.HPKey[:],material[44:])
        return out,nil
    }
    c2s,err:=derive("c2s");if err!=nil{return empty,err}
    s2c,err:=derive("s2c");if err!=nil{return empty,err}
    return tlsrecord.KeyPair{C2S:c2s,S2C:s2c},nil
}

// EstablishClientV4 preserves exactly one protected request and reply; no
// additional RTT. This opt-in API is fail-closed until caller proves readiness.
func EstablishClientV4(ctx context.Context,conn net.Conn,cfg ClientAdmissionConfig,opt V4ClientOptions)(*V4ClientSession,error) {
    if !opt.DataPlaneReady {return nil,ErrAdmissionUnsupported}
    lane:=cfg.LaneID
    if lane==0 {lane=1}
    req:=AdmissionRequest{
        AutoLease:cfg.AutoLease,DesiredLanes:cfg.DesiredLanes,
        InstallationID:append([]byte(nil),cfg.InstallationID...),
        RecordVersion:V4RecordVersion,Policy:cfg.Policy,LaneID:lane,
        TunnelID:append([]byte(nil),cfg.TunnelID...),ClientLimit:cfg.ClientLimit,
        Username:cfg.Username,Password:cfg.Password,
    }
    if cfg.Policy.Schema!=PolicySchemaV3 || cfg.Policy.SupportedNow()!=nil {return nil,ErrAdmissionUnsupported}
    wire,err:=v4RequestWire(req,V4Extension{Features:v4RequiredFeatures,Epoch:opt.Epoch})
    if err!=nil{return nil,err}
    guard,err:=beginCandidateDeadline(ctx,conn,cfg.TLS.Timeout)
    if err!=nil{return nil,err}
    success:=false
    defer func(){ guard.Finish(success);if !success {_=conn.Close()} }()
    tlsCfg:=cfg.TLS
    tlsCfg.Timeout=guard.Remaining()
    client,err:=handshakeClientConn(ctx,conn,tlsCfg)
    if err!=nil{return nil,candidateError(ctx,err)}
    if err:=guard.Rearm();err!=nil{return nil,err}
    if err:=writeFull(client,wire);err!=nil{return nil,candidateError(ctx,err)}
    result,extension,err:=v4ReadReply(client,req)
    if err!=nil{return nil,candidateError(ctx,err)}
    if extension.Features!=v4RequiredFeatures || extension.Epoch==[16]byte{} ||
       (opt.Epoch!=[16]byte{} && opt.Epoch!=extension.Epoch) {
        return nil,ErrAdmissionParams
    }
    state:=client.ConnectionState()
    keys,err:=v4DeriveRecordKeys(&state,result,extension)
    if err!=nil{return nil,err}
    result.Keys=keys
    result.TLSCipherSuite=state.CipherSuite
    success=true
    return &V4ClientSession{
        ClientAdmissionSession:&ClientAdmissionSession{TLS:&ClientSession{Keys:keys},Negotiated:result},
        Epoch:extension.Epoch,
    },nil
}

// EstablishServerV4 uses original recognized TLS and Prepare/Detach handoff.
// Epoch becomes active only after successful authenticated reply and detach.
// Caller must ReleaseLane on tunnel teardown. Legacy EstablishServer is intact.
func EstablishServerV4(ctx context.Context,assoc *faketcp.ServerAssociation,cfg ServerAdmissionConfig,opt V4ServerOptions)(*V4ServerSession,error) {
    if !opt.DataPlaneReady || opt.Epochs==nil {return nil,ErrAdmissionUnsupported}
    if assoc==nil || cfg.ExpectedUsername=="" || cfg.ExpectedPassword=="" || !validRecordLimit(cfg.ServerLimit) {
        return nil,ErrAdmissionParams
    }
    conn:=assoc.BootstrapConn()
    guard,err:=beginCandidateDeadline(ctx,conn,cfg.TLS.Timeout)
    if err!=nil{return nil,err}
    success:=false
    defer func(){guard.Finish(success);if !success {assoc.Close()} }()
    hello,err:=ReadHello(conn,cfg.TLS.ServerName,cfg.TLS.RouteKey,guard.Remaining())
    if err!=nil{return nil,candidateError(ctx,err)}
    if err:=guard.Rearm();err!=nil{return nil,err}
    if !hello.Recognized {return nil,ErrMarker}
    tlsCfg:=cfg.TLS
    tlsCfg.Timeout=guard.Remaining()
    tlsConn,err:=handshakeServerRecognizedConn(ctx,conn,hello,tlsCfg)
    if err!=nil{return nil,candidateError(ctx,err)}
    if err:=guard.Rearm();err!=nil{return nil,err}
    req,offered,err:=v4ReadRequest(tlsConn)
    if err!=nil{_ = writeAdmissionFailure(tlsConn,admissionStatus(err));return nil,candidateError(ctx,err)}
    if !credentialsMatch(req.Username,req.Password,cfg.ExpectedUsername,cfg.ExpectedPassword) {
        _=writeAdmissionFailure(tlsConn,admissionAuthFail)
        return nil,ErrAdmissionAuth
    }
    if err:=req.Policy.SupportedNow();err!=nil{
        _=writeAdmissionFailure(tlsConn,admissionParamFail)
        return nil,err
    }
    if cfg.PolicyAllow!=nil {
        if err:=cfg.PolicyAllow(req.Policy);err!=nil {
            _=writeAdmissionFailure(tlsConn,admissionParamFail)
            return nil,errors.Join(ErrAdmissionUnsupported,err)
        }
    }
    if cfg.ValidateRequest!=nil {
        if err:=cfg.ValidateRequest(req);err!=nil {
            _=writeAdmissionFailure(tlsConn,admissionParamFail)
            return nil,errors.Join(ErrAdmissionParams,err)
        }
    }
    source:=cfg.Random
    if source==nil {source=rand.Reader}
    epoch,finish,err:=opt.Epochs.prepare(req.Username,req.TunnelID,req.LaneID,offered.Epoch,source)
    if err!=nil {
        _=writeAdmissionFailure(tlsConn,admissionParamFail)
        return nil,err
    }
    committed:=false
    defer func(){finish(committed)}()
    var nonce [16]byte
    if _,err:=io.ReadFull(source,nonce[:]);err!=nil{return nil,err}
    lease:=""
    if req.AutoLease {
        if cfg.AllocateLease==nil {
            _=writeAdmissionFailure(tlsConn,admissionParamFail);return nil,ErrAdmissionParams
        }
        lease,err=cfg.AllocateLease(req)
        if err!=nil || lease=="" {
            _=writeAdmissionFailure(tlsConn,admissionParamFail);return nil,errors.Join(ErrAdmissionParams,err)
        }
    }
    result:=AdmissionResult{
        Lease4:lease,DesiredLanes:req.DesiredLanes,RecordVersion:V4RecordVersion,Policy:req.Policy,
        LaneID:req.LaneID,IncarnationNonce:nonce,TunnelID:append([]byte(nil),req.TunnelID...),
        ClientLimit:req.ClientLimit,ServerLimit:cfg.ServerLimit,
    }
    ext:=V4Extension{Features:v4RequiredFeatures,Epoch:epoch}
    state:=tlsConn.ConnectionState()
    keys,err:=v4DeriveRecordKeys(&state,result,ext)
    if err!=nil{return nil,err}
    result.Keys=keys
    result.TLSCipherSuite=state.CipherSuite
    boundary,err:=assoc.PrepareTransition(int(cfg.ServerLimit))
    if err!=nil{return nil,err}
    reply,err:=v4ReplyWire(result,ext)
    if err!=nil{assoc.AbortTransition();return nil,err}
    if err:=writeFull(tlsConn,reply);err!=nil{
        assoc.AbortTransition()
        return nil,candidateError(ctx,err)
    }
    early,err:=assoc.DetachTransition()
    if err!=nil{assoc.AbortTransition();return nil,err}
    committed=true
    success=true
    return &V4ServerSession{
        ServerAdmissionSession:&ServerAdmissionSession{
            TLS:&ServerSession{Hello:hello,Keys:keys},
            Negotiated:result,Boundary:boundary,EarlyRecords:early,
        },Epoch:epoch,
    },nil
}
