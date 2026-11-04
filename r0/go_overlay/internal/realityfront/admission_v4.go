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
    "net/netip"
    "sync"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
    "github.com/lly8666/wobuzhidao/internal/logicaltunnel"
    "github.com/lly8666/wobuzhidao/internal/tlsrecord"
    "golang.org/x/crypto/hkdf"
)

const (
    V4RecordVersion uint16 = 4
    v4ExtensionLen = 24
    v4FeatureReceipt = uint16(1)
    v4FeatureSharedGame = uint16(2)
    v4FeatureFEC2 = uint16(4) // reserved: no production FEC2 yet
    v4RequiredFeatures = v4FeatureReceipt | v4FeatureSharedGame
    v4FeedbackPages = byte(8)
)

type V4Extension struct {
    Features uint16
    Epoch [16]byte
    // Exact fixed Game FEC profile+1 (1..7), 0=off. Authenticated
    // inside the existing V4 TLS request/reply; no downgrade or Auto.
    GameFec uint8
    // Normal fixed profile+1; zero for off/auto/Game/legacy V4.
    // Reuses previously reserved byte 22 of the existing protected record.
    NormalFec uint8
}
// Exactly 3(default) or 7(private test), rejecting all unknown/partial sets.
func v4KnownFeatureSet(f uint16)bool{return f==v4RequiredFeatures||f==(v4RequiredFeatures|v4FeatureFEC2)}

func v4Encode(e V4Extension) ([24]byte, error) {
    var buf [24]byte
    if !v4KnownFeatureSet(e.Features)||e.GameFec>7||e.NormalFec>7||
        (e.GameFec!=0&&e.NormalFec!=0)||
        ((e.GameFec!=0||e.NormalFec!=0)&&e.Features!=v4RequiredFeatures|v4FeatureFEC2){
        return buf,ErrAdmissionUnsupported
    }
    binary.BigEndian.PutUint16(buf[0:2], 1)
    binary.BigEndian.PutUint16(buf[2:4], e.Features)
    copy(buf[4:20], e.Epoch[:])
    buf[20] = v4FeedbackPages
    buf[21] = e.GameFec
    buf[22] = e.NormalFec
    return buf, nil
}

func v4Decode(raw []byte) (V4Extension,error) {
    var e V4Extension
    if len(raw)!=v4ExtensionLen { return e,ErrAdmissionParams }
    if binary.BigEndian.Uint16(raw[:2])!=1 || raw[20]!=v4FeedbackPages ||
       raw[22]>7 || raw[23]!=0 || raw[21]>7 { return e,ErrAdmissionParams }
    e.Features=binary.BigEndian.Uint16(raw[2:4])
    if !v4KnownFeatureSet(e.Features) ||
       (raw[21]!=0&&raw[22]!=0)||
       ((raw[21]!=0||raw[22]!=0)&&e.Features!=v4RequiredFeatures|v4FeatureFEC2){
        return V4Extension{},ErrAdmissionUnsupported
    }
    e.GameFec=raw[21]
    e.NormalFec=raw[22]
    copy(e.Epoch[:],raw[4:20])
    return e,nil
}

// Callers must positively attest receipt/Game data-plane readiness before
// opt-in. The bridge MUST NOT set Ready until matching Rust capabilities exist.
type V4ClientOptions struct {
    DataPlaneReady bool
    Epoch [16]byte // zero only for the first lane of a new logical tunnel
    fec2ProbeOnly bool // unexported and default false: no product authority
    fec2Product bool // original-Go TLS + true native Linux feature7 owner only
    GameFec uint8 // 0=off; 1..7 = fixed profile 0..6; TLS-protected
    NormalFec uint8 // 0=off/auto/old V4, 1..7=authenticated Normal fixed profile0..6
}
// The backend is deliberately package-private: a caller cannot provide an
// arbitrary 248-byte cold grammar and ask the engine to call it authenticated.
// Future native Go bridge files in this package may implement it. With no
// backend the legacy fail-closed, cold-only behavior is unchanged.
type v4PreparedOwner interface {
    commit(early []faketcp.TransitionPacket, exactTXBoundary uint32) error
    abort()
}
// Peer MSS is read from the actual FakeTCP SYN association AFTER credential
// verification. It is untrusted *transport input*, not another TLS identity,
// but can only constrain outgoing record size. It must not be supplied by a
// later driver caller, CLI override, or invented native cold bundle.
type v4PeerTransport struct {
    mss uint16
    advertised bool
    // Captured from THIS FakeTCP association, not CLI, cold248, or a
    // later unauthenticated driver packet. It is transport routing evidence,
    // NOT an independently authenticated TLS principal.
    flow faketcp.ServerFlow
}
func v4PeerTransportFromAssociation(a *faketcp.ServerAssociation)(v4PeerTransport,error){
    if a==nil{return v4PeerTransport{},ErrAdmissionParams}
    profile:=a.PeerTCPProfile()
    flow:=a.Flow() // copy immutable IPv4 tuple while the protected call owns a
    if profile.MSS<64 || flow.ClientPort==0 || flow.ServerPort==0 ||
       flow.ClientIP==([4]byte{}) || flow.ServerIP==([4]byte{}) {
        return v4PeerTransport{},ErrAdmissionParams
    }
    return v4PeerTransport{mss:profile.MSS,advertised:profile.AdvertisedMSS,flow:flow},nil
}
// This VERSIONED transport-control command is built in production Go only
// from the real credential-checked private EstablishServerV4 callsite.
// It is not a credential and is never a standalone Rust activation token.
// Layout (BE): magic4/version2/size2/clientIP4/serverIP4/ports4/RXseq4/
// SYN-MSS2/advertised1/reserved5. All bytes are copied synchronously.
const v4PrivateHandoffLen=32
func v4PrivateHandoffV1(rxBoundary uint32, peer v4PeerTransport)([v4PrivateHandoffLen]byte,error){
    var out [v4PrivateHandoffLen]byte
    flow:=peer.flow
    if peer.mss<64 || (!peer.advertised && peer.mss!=536) ||
        flow.ClientPort==0 || flow.ServerPort==0 ||
        flow.ClientIP==([4]byte{}) || flow.ServerIP==([4]byte{}) {
        return out,ErrAdmissionParams
    }
    copy(out[:4],[]byte("WBGH"))
    binary.BigEndian.PutUint16(out[4:6],1)
    binary.BigEndian.PutUint16(out[6:8],v4PrivateHandoffLen)
    copy(out[8:12],flow.ClientIP[:])
    copy(out[12:16],flow.ServerIP[:])
    binary.BigEndian.PutUint16(out[16:18],flow.ClientPort)
    binary.BigEndian.PutUint16(out[18:20],flow.ServerPort)
    binary.BigEndian.PutUint32(out[20:24],rxBoundary)
    binary.BigEndian.PutUint16(out[24:26],peer.mss)
    if peer.advertised {out[26]=1}
    return out,nil
}
// The ONLY variant-2 command constructor consumes the SAME private snapshot
// created after the credential-checked V4 protected request. It does not
// serialize keys or assert that Rust FEC2 production has been activated.
// V1/default remains byte-for-byte unchanged.
func v4PrivateHandoffFromVerifiedSession(
    boundary uint32,peer v4PeerTransport,s V4ColdSessionSnapshot,
)([v4PrivateHandoffLen]byte,error){
    var zero [v4PrivateHandoffLen]byte
    if !s.server || s.principal=="" || s.epoch==[16]byte{} ||
       !v4KnownFeatureSet(s.features) {
        return zero,ErrAdmissionParams
    }
    command,err:=v4PrivateHandoffV1(boundary,peer)
    if err!=nil{return zero,err}
    if s.features==v4RequiredFeatures|v4FeatureFEC2 {
        binary.BigEndian.PutUint16(command[4:6],2)
        binary.BigEndian.PutUint16(command[27:29],s.features)
    }
    return command,nil
}
// Authenticated verified CLIENT result is symmetric to the original Go
// server v2 feature7 command. A raw caller cannot submit these bytes as
// proof of the Go TLS exporter; this stays package-private.
func v4PrivateHandoffFromVerifiedClientSession(
    boundary uint32,peer v4PeerTransport,s V4ColdSessionSnapshot,
)([v4PrivateHandoffLen]byte,error){
    var zero [v4PrivateHandoffLen]byte
    if s.server||s.principal==""||s.epoch==[16]byte{}||
        !v4KnownFeatureSet(s.features){return zero,ErrAdmissionParams}
    command,err:=v4PrivateHandoffV1(boundary,peer)
    if err!=nil{return zero,err}
    if s.features==(v4RequiredFeatures|v4FeatureFEC2){
        binary.BigEndian.PutUint16(command[4:6],2)
        binary.BigEndian.PutUint16(command[27:29],s.features)
    }
    return command,nil
}

type v4OwnerBridge interface {
    prepare(verified V4ColdSessionSnapshot, rxBoundary uint32, observedPeer v4PeerTransport) (v4PreparedOwner, error)
}

// M0↔M4 original-Go V4 lifecycle seam, not a cold/credential/ACK authority.
// M0 supplies the REAL backend; M4 Windows native cleanup must never run
// before an actual original Rust owner and its kernel borrows have completed
// Stop and generation release. This does not enable product FEC2.
type V4OwnerStopCompletion struct {
    Epoch [16]byte
    OwnerAndDriversDrained bool
    GenerationReleased bool
}
type V4OriginalOwnerStopper interface {
    StopAndReleaseOriginalOwner() (V4OwnerStopCompletion,error)
}
// V4StopThenCleanupNetwork enforces Stop→owned native Cleanup order.
// Any real Stop error retains network ownership for later recovery; never
// invoke cleanup, never fabricate a "disconnected" result. Cleanup failure
// propagates as partial network recovery AFTER verified owner shutdown.
func V4StopThenCleanupNetwork(
    owner V4OriginalOwnerStopper,cleanup func()error,
)(V4OwnerStopCompletion,error){
    var zero V4OwnerStopCompletion
    if owner==nil||cleanup==nil{return zero,ErrAdmissionParams}
    completed,err:=owner.StopAndReleaseOriginalOwner()
    if err!=nil{return zero,err}
    if completed.Epoch==[16]byte{} || !completed.OwnerAndDriversDrained ||
       !completed.GenerationReleased{return zero,ErrAdmissionParams}
    if err:=cleanup();err!=nil{return completed,err}
    return completed,nil
}
type V4ServerOptions struct {
    DataPlaneReady bool
    fec2ProbeOnly bool // package-private, no production caller switch
    fec2Product bool // package-private genuine Linux fixed/auto owner
    // Shared Normal server only: select EXISTING FEC2 capability per
    // authenticated TLS policy instead of its process-scoped CLI mode.
    // No new on-wire flag, no pre-TLS hint or unauthenticated admission.
    perClientNormalFEC bool
    GameFec uint8 // 0=off; 1..7=Game fixed profiles 0..6, private TLS
    NormalFec uint8 // server-owned fixed Normal profile+1 in strict singleton mode
    Epochs *V4EpochStore // shared by all lanes of the same server instance
    // Explicit cold admission capability only. The native shared owner must
    // independently prove that two generations can coexist before enabling.
    // Default false preserves reject-duplicate semantics on old call sites.
    AllowLaneReplacement bool
    // A server-owned, explicit manual /32 used ONLY for protected new
    // generation replacement. Never obtained from client-supplied IP.
    ManualLease4 string
    // Cold V4 only: optional server account roster, checked AFTER real TLS
    // protected request and BEFORE any epoch/lease/native owner reservation.
    // Nil uses original exact ExpectedUsername/ExpectedPassword pair.
    Authenticate func(username,password string)bool
    ownerBridge v4OwnerBridge // unexported, no public arbitrary-bytes activation
}

// v4ServerCheckedManualLease4 accepts only an explicitly provisioned
// server-side /32. It is evaluated AFTER credential authentication in
// EstablishServerV4 and never grants authority based on a client packet.
func v4ServerCheckedManualLease4(s string,auto bool)(string,error){
    if s==""{return "",nil}
    if auto{return "",ErrAdmissionParams}
    p,e:=netip.ParsePrefix(s)
    if e!=nil||!p.Addr().Is4()||p.Bits()!=32||
       p.Addr().IsUnspecified()||p.Addr().IsMulticast()||
       p.Addr().IsLoopback()||p.Addr().IsLinkLocalUnicast(){
        return "",ErrAdmissionParams
    }
    return p.String(),nil
}
type V4ClientSession struct {
    *ClientAdmissionSession
    Epoch [16]byte
    // Freeze only the protected reply's validated IPv4 lease, never user
    // requested MTU or mutable Negotiated fields as OS network authority.
    verifiedLease4 string
    // Only EstablishClientV4 after verified protected reply and KDF may set this.
    coldAuthenticated bool
    authenticatedPrincipal string
    verifiedNormalFec uint8 // copied from authenticated reply; not user mutable
    // Freeze once, so caller-mutable Negotiated fields never mint new authority.
    verifiedCold V4ColdSessionSnapshot
    verifiedPolicy AdmissionPolicy // original verified TLS policy, not caller-mutable Negotiated
    negotiatedFeatures uint16
}
type V4ServerSession struct {
    *ServerAdmissionSession
    Epoch [16]byte
    verifiedLease4 string
    // Server-local manual /32, assigned only after verified protected
    // credentials and exact tunnel scope; NOT serialized into the legacy
    // manual V4 TLS reply (which contains no auto-lease four-byte field).
    serverOwnedManualLease4 string
    // Only EstablishServerV4 after credentials, protected reply and Detach may set this.
    coldAuthenticated bool
    authenticatedPrincipal string
    verifiedNormalFec uint8 // original credential-checked protected request
    verifiedCold V4ColdSessionSnapshot
    verifiedPolicy AdmissionPolicy // original verified TLS policy, not caller-mutable Negotiated
    negotiatedFeatures uint16
}

// Reuse the pinned original logicaltunnel allocator: 7-day memory lease,
 // account+installation-derived stable tunnel identity, active lease renewal.
// The allocator is called by EstablishServerV4 only AFTER credentials are
// checked. Never mint a tunnel ID merely from a source IP/NAT tuple.
func V4AllocateAutomaticLease(registry *logicaltunnel.LeaseRegistry,req AdmissionRequest)(string,error){
    if registry==nil||!req.AutoLease||len(req.InstallationID)!=16||
       len(req.TunnelID)!=16||req.Username==""{return "",ErrAdmissionParams}
    var install logicaltunnel.InstallationID
    copy(install[:],req.InstallationID)
    if install==[16]byte{} {return "",ErrAdmissionParams}
    id,err:=logicaltunnel.TunnelIDFromBytes(req.TunnelID)
    if err!=nil||id!=logicaltunnel.DerivedTunnelID(req.Username,install){
        return "",ErrAdmissionParams
    }
    lease,err:=registry.Acquire(req.Username,install,id)
    if err!=nil {return "",err}
    return lease.Config.Address4,nil
}

// AuthenticatedLeaseIPv4 exposes only a fully validated TLS reply's effective
// lease and rejects caller mutation of Negotiated, for OS installation BEFORE
// starting the Rust raw/TUN business loop. Empty means manual-IP admission.
func (s *V4ClientSession) AuthenticatedLeaseIPv4()(string,error){
    if s==nil||s.ClientAdmissionSession==nil{return "",ErrAdmissionUnsupported}
    if _,err:=s.ColdSnapshot();err!=nil{return "",err}
    if s.Negotiated.Lease4!=s.verifiedLease4{return "",ErrAdmissionParams}
    return s.verifiedLease4,nil
}

// Server-side effective client /32 is the original protected lease reply,
 // never an untrusted account, outer tuple, CLI string or mutable result.
func (s *V4ServerSession) AuthenticatedLeaseIPv4()(string,error){
    if s==nil||s.ServerAdmissionSession==nil{return "",ErrAdmissionUnsupported}
    if _,err:=s.ColdSnapshot();err!=nil{return "",err}
    if s.Negotiated.Lease4!=s.verifiedLease4{return "",ErrAdmissionParams}
    if s.serverOwnedManualLease4!=""{
        // No untrusted caller can mutate the old manual reply to invent a
        // sibling route; the /32 is server-provisioned before cold auth.
        if s.verifiedLease4!=""{return "",ErrAdmissionParams}
        return s.serverOwnedManualLease4,nil
    }
    return s.verifiedLease4,nil
}

// A typed tuple makes the authenticated account + fixed 16-byte tunnel scope
// explicit; no ambiguous textual identity keys or binary allocations.
type v4IdentityKey struct{
    username string
    tunnel [16]byte
}
type v4Entry struct {
    epoch [16]byte
    active bool
    lanes uint8 // 1<<lane (IDs 1..4)
    pending uint8
    // One owner incarnation normally; at most old+new during explicit
    // make-before-break. Keys and nonce are unique even when epoch is shared.
    instances [5][][16]byte
    // Once a lane overlaps, epoch-only release can no longer identify an
    // owner. Keep it disabled after old A leaves, until tunnel retirement.
    fenced [5]bool
}

// Per-server explicit-lifecycle store. Session close must release its exact
// authenticated incarnation; do not infer an owner from username or epoch.
type V4EpochStore struct {
    mu sync.Mutex
    entries map[v4IdentityKey]*v4Entry
    max int
}
func NewV4EpochStore(max int) (*V4EpochStore,error) {
    if max<1 || max>4096 { return nil,ErrAdmissionParams }
    return &V4EpochStore{entries:make(map[v4IdentityKey]*v4Entry),max:max},nil
}
func v4Identity(username string,tunnelID []byte) v4IdentityKey {
    var tunnel [16]byte
    copy(tunnel[:],tunnelID)
    return v4IdentityKey{username:username,tunnel:tunnel}
}

// ReleaseLane keeps only the legacy non-overlapping lifecycle working.
// After overlap it refuses epoch-only release, including after one of the two
// generations has retired: a stale callback must not remove its successor.
func (s *V4EpochStore) ReleaseLane(username string,tunnelID []byte,lane uint8,epoch [16]byte) error {
    if s==nil || !validAdmissionLaneID(lane) || len(tunnelID)!=16 {return ErrAdmissionParams}
    key:=v4Identity(username,tunnelID)
    s.mu.Lock()
    defer s.mu.Unlock()
    e:=s.entries[key]
    if e==nil || e.epoch!=epoch || !e.active ||
       e.fenced[lane] || len(e.instances[lane])!=1 {return ErrAdmissionParams}
    e.instances[lane]=nil
    e.lanes &^= uint8(1<<lane)
    if e.lanes==0 && e.pending==0 {delete(s.entries,key)}
    return nil
}

// ReleaseLaneInstance is the only safe Stop/retire path for a replacement.
// The immutable nonce comes from the verified TLS snapshot, not user input.
func (s *V4EpochStore) ReleaseLaneInstance(
    username string,tunnelID []byte,lane uint8,epoch,incarnation [16]byte,
) error {
    if s==nil || !validAdmissionLaneID(lane) || len(tunnelID)!=16 ||
       incarnation==[16]byte{} {return ErrAdmissionParams}
    key:=v4Identity(username,tunnelID)
    s.mu.Lock()
    defer s.mu.Unlock()
    e:=s.entries[key]
    if e==nil || !e.active || e.epoch!=epoch {return ErrAdmissionParams}
    index:=-1
    for i,instance:=range e.instances[lane] {
        if instance==incarnation {index=i;break}
    }
    if index<0 {return ErrAdmissionParams}
    instances:=e.instances[lane]
    copy(instances[index:],instances[index+1:])
    instances=instances[:len(instances)-1]
    e.instances[lane]=instances
    if len(instances)==0 {e.lanes &^= uint8(1<<lane)}
    if e.lanes==0 && e.pending==0 {delete(s.entries,key)}
    return nil
}

// Lease expiry is a cold admission operation, not per-packet routing.
// A pending authenticated candidate must pin its address just like an
// active owner; otherwise another login could steal the same IPv4 while
// the original TLS/Detach is still completing.
func (s *V4EpochStore) HasLiveTunnel(id logicaltunnel.TunnelID)bool{
    if s==nil{return false}
    s.mu.Lock()
    defer s.mu.Unlock()
    for key,e:=range s.entries{
        if key.tunnel==[16]byte(id) && (e.lanes!=0||e.pending!=0){return true}
    }
    return false
}

// prepare runs only after TLS credential verification. The first attempt
// creates a new logical epoch; additional lanes join that epoch. Explicit
// replacement can reserve one additional instance of the SAME lane, but no
// third owner and never two simultaneously pending candidates. The per-lane
// random incarnation is drawn here, before the protected reply, and reused
// as the immutable generation-fencing token for its exact Stop callback.
func (s *V4EpochStore) prepare(
    username string,tunnelID []byte,lane uint8,want [16]byte,
    rng io.Reader,allowReplacement bool,
)([16]byte,[16]byte,func(bool),error) {
    var zero [16]byte
    if s==nil || rng==nil || !validAdmissionLaneID(lane) ||
       len(tunnelID)!=16 {return zero,zero,nil,ErrAdmissionParams}
    key:=v4Identity(username,tunnelID)
    bit:=uint8(1<<lane)
    s.mu.Lock()
    defer s.mu.Unlock()
    e,found:=s.entries[key]
    // A fresh original-Go TLS request intentionally carries zero epoch.
    // Only the SERVER may authorize overlap for the exact authenticated
    // principal+derived installation/TunnelID+lane that is already active.
    // Reuse its logical epoch, but mint a NEW random incarnation and
    // exporter-derived keys. No client-provided IP/outer tuple decides this.
    newTunnel:=want==zero&&!found
    if newTunnel {
        if len(s.entries)>=s.max {return zero,zero,nil,ErrAdmissionParams}
        var epoch [16]byte
        if _,err:=io.ReadFull(rng,epoch[:]);err!=nil{return zero,zero,nil,err}
        if epoch==zero{return zero,zero,nil,ErrAdmissionParams}
        e=&v4Entry{epoch:epoch}
    } else {
        if !found || !e.active || e.pending&bit!=0 ||
           (want!=zero && e.epoch!=want) {
            return zero,zero,nil,ErrAdmissionParams
        }
        n:=len(e.instances[lane])
        // Zero-epoch reconnect is ONLY an exact 1->2 same-lane handoff.
        // Explicit-epoch Game lane joins remain on their prior contract.
        if want==zero && (!allowReplacement || n!=1) {
            return zero,zero,nil,ErrAdmissionParams
        }
        if n>0 && (!allowReplacement || n>=2) {
            return zero,zero,nil,ErrAdmissionParams
        }
    }
    var nonce [16]byte
    if _,err:=io.ReadFull(rng,nonce[:]);err!=nil{return zero,zero,nil,err}
    if nonce==zero{return zero,zero,nil,ErrAdmissionParams}
    for _,old:=range e.instances[lane] {
        if old==nonce {return zero,zero,nil,ErrAdmissionParams}
    }
    e.pending|=bit
    if newTunnel {s.entries[key]=e}
    actual:=e.epoch
    ended:=false
    finish:=func(commit bool) {
        s.mu.Lock()
        defer s.mu.Unlock()
        if ended{return}
        ended=true
        current:=s.entries[key]
        if current!=e{return}
        e.pending &^= bit
        if commit {
            if len(e.instances[lane])!=0 {e.fenced[lane]=true}
            e.instances[lane]=append(e.instances[lane],nonce)
            e.lanes|=bit
            e.active=true
        } else if e.lanes==0 && e.pending==0 {
            delete(s.entries,key)
        }
    }
    return actual,nonce,finish,nil
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
    if !opt.DataPlaneReady||opt.GameFec>7||opt.NormalFec>7||
       (opt.GameFec!=0&&opt.NormalFec!=0)||
       (opt.GameFec!=0&&(!opt.fec2Product||cfg.Policy.Transport!=TransportGame))||
       (opt.NormalFec!=0&&(!opt.fec2Product||cfg.Policy.Transport!=TransportNormal||
         cfg.Policy.FECMode!=FECFixed)){
        return nil,ErrAdmissionUnsupported
    }
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
    offeredFeatures:=v4RequiredFeatures
    if opt.fec2ProbeOnly||opt.fec2Product {offeredFeatures |= v4FeatureFEC2}
    wire,err:=v4RequestWire(req,V4Extension{Features:offeredFeatures,Epoch:opt.Epoch,GameFec:opt.GameFec,NormalFec:opt.NormalFec})
    if err!=nil{return nil,err}
    // The route classifier secret must be provisioned BEFORE opening
    // transport. A missing key is an ordinary local config failure: no
    // WB-R1/private challenge, no alternative first payload or downgrade.
    if len(cfg.TLS.RouteKey)!=32{return nil,ErrAdmissionParams}
    guard,err:=beginCandidateDeadline(ctx,conn,cfg.TLS.Timeout)
    if err!=nil{return nil,err}
    success:=false
    defer func(){ guard.Finish(success);if !success {_=conn.Close()} }()
    tlsCfg:=cfg.TLS
    // Certificate verification is mandatory even for an explicit route-key;
    // key possession is NOT a server identity proof.
    tlsCfg.VerifyServer=true
    tlsCfg.Timeout=guard.Remaining()
    client,err:=handshakeClientConn(ctx,conn,tlsCfg)
    if err!=nil{return nil,candidateError(ctx,err)}
    if err:=guard.Rearm();err!=nil{return nil,err}
    if err:=writeFull(client,wire);err!=nil{return nil,candidateError(ctx,err)}
    result,extension,err:=v4ReadReply(client,req)
    if err!=nil{return nil,candidateError(ctx,err)}
    // No protected reply feature downgrade/upgrade is admissible.
    if extension.Features!=offeredFeatures || extension.GameFec!=opt.GameFec ||
       extension.NormalFec!=opt.NormalFec || extension.Epoch==[16]byte{} ||
       (opt.Epoch!=[16]byte{} && opt.Epoch!=extension.Epoch) {
        return nil,ErrAdmissionParams
    }
    state:=client.ConnectionState()
    keys,err:=v4DeriveRecordKeys(&state,result,extension)
    if err!=nil{return nil,err}
    result.Keys=keys
    result.TLSCipherSuite=state.CipherSuite
    frozen,err:=v4ColdSnapshot(result,extension.Epoch,cfg.Username,false,extension.Features)
    if err!=nil{return nil,err}
    success=true
    return &V4ClientSession{
        ClientAdmissionSession:&ClientAdmissionSession{TLS:&ClientSession{Keys:keys},Negotiated:result},
        Epoch:extension.Epoch,verifiedLease4:result.Lease4,
        coldAuthenticated:true, authenticatedPrincipal:cfg.Username,
        verifiedNormalFec:extension.NormalFec,verifiedCold:frozen,verifiedPolicy:result.Policy,negotiatedFeatures:extension.Features,
    },nil
}

// A shared Normal server can accept Off, Fixed or Auto per independently
// authenticated device using the original, immutable 10-byte V3 policy.
// It does NOT interpret an unauthenticated SYN, packet or route-key as mode.
// The exact original feature3/feature7 extension and TLS record remain.
func v4ProtectedNormalFECFeatures(p AdmissionPolicy)(uint16,error){
    if p.Schema!=PolicySchemaV3||p.Transport!=TransportNormal||
       p.DesiredLanes!=1||p.SupportedNow()!=nil{
        return 0,ErrAdmissionUnsupported
    }
    switch p.FECMode{
    case FECOff:
        return v4RequiredFeatures,nil
    case FECFixed,FECAuto:
        return v4RequiredFeatures|v4FeatureFEC2,nil
    default:
        return 0,ErrAdmissionUnsupported
    }
}

// Strict shared Normal fixed profile selection from an EXISTING protected
// 24-byte V4 extension. A new shared server does not silently guess a
// device's fixed strength from its own process-level --fec-profile.
func v4ProtectedNormalFECProfile(p AdmissionPolicy,profile uint8,shared bool)(uint8,error){
    if _,err:=v4ProtectedNormalFECFeatures(p);err!=nil{return 0,err}
    if p.FECMode!=FECFixed {
        if profile!=0{return 0,ErrAdmissionUnsupported}
        return 0,nil
    }
    if profile==0 {
        if shared{return 0,ErrAdmissionUnsupported}
        return 0,nil // old strict single-session admission
    }
    if profile>7{return 0,ErrAdmissionUnsupported}
    return profile-1,nil
}

// EstablishServerV4 uses original recognized TLS and Prepare/Detach handoff.
// Epoch becomes active only after successful authenticated reply and detach.
// Caller must ReleaseLane on tunnel teardown. Legacy EstablishServer is intact.
func EstablishServerV4(ctx context.Context,assoc *faketcp.ServerAssociation,cfg ServerAdmissionConfig,opt V4ServerOptions)(*V4ServerSession,error) {
    if !opt.DataPlaneReady||opt.Epochs==nil||opt.GameFec>7||
       (opt.GameFec!=0&&!opt.fec2Product){return nil,ErrAdmissionUnsupported}
    if assoc==nil || (opt.Authenticate==nil&&(cfg.ExpectedUsername==""||cfg.ExpectedPassword=="")) ||
       !validRecordLimit(cfg.ServerLimit) {
        return nil,ErrAdmissionParams
    }
    if len(cfg.TLS.RouteKey)!=32{return nil,ErrAdmissionParams}
    conn:=assoc.BootstrapConn()
    guard,err:=beginCandidateDeadline(ctx,conn,cfg.TLS.Timeout)
    if err!=nil{return nil,err}
    success:=false
    defer func(){guard.Finish(success);if !success {assoc.Close()} }()
    tlsCfg:=cfg.TLS
    // Only a valid TLS ClientHello with its existing compatible HMAC
    // SessionID reaches the actual crypto/tls server; no earlier payload.
    hello,err:=ReadHello(conn,tlsCfg.ServerName,tlsCfg.RouteKey,guard.Remaining())
    if err!=nil{return nil,candidateError(ctx,err)}
    if err:=guard.Rearm();err!=nil{return nil,err}
    if !hello.Recognized {return nil,ErrMarker}
    tlsCfg.Timeout=guard.Remaining()
    tlsConn,err:=handshakeServerRecognizedConn(ctx,conn,hello,tlsCfg)
    if err!=nil{return nil,candidateError(ctx,err)}
    if err:=guard.Rearm();err!=nil{return nil,err}
    req,offered,err:=v4ReadRequest(tlsConn)
    if err!=nil{_ = writeAdmissionFailure(tlsConn,admissionStatus(err));return nil,candidateError(ctx,err)}
    authenticated:=false
    if opt.Authenticate!=nil {
        authenticated=opt.Authenticate(req.Username,req.Password)
    }else{
        authenticated=credentialsMatch(req.Username,req.Password,cfg.ExpectedUsername,cfg.ExpectedPassword)
    }
    if !authenticated {
        _=writeAdmissionFailure(tlsConn,admissionAuthFail)
        return nil,ErrAdmissionAuth
    }
    serverFeatures:=v4RequiredFeatures
    if opt.fec2ProbeOnly||opt.fec2Product {serverFeatures |= v4FeatureFEC2}
    if opt.perClientNormalFEC {
        // Only the previously parsed, credential-checked protected
        // AdmissionPolicy can select this association's existing FEC owner.
        // A modified feature offer still fails the strict equality below.
        serverFeatures,err=v4ProtectedNormalFECFeatures(req.Policy)
        if err!=nil{
            _=writeAdmissionFailure(tlsConn,admissionParamFail)
            return nil,err
        }
    }
    // Protected, fixed-length cold metadata: one independently chosen
    // Normal fixed strength per authenticated installation, never from
    // the TCP tuple/route key. No new message, TLS prefix or hot-path tag.
    selectedNormalFec:=uint8(0)
    if opt.perClientNormalFEC {
        if _,e:=v4ProtectedNormalFECProfile(req.Policy,offered.NormalFec,true);e!=nil{
            _=writeAdmissionFailure(tlsConn,admissionParamFail)
            return nil,e
        }
        selectedNormalFec=offered.NormalFec
    }else {
        // Standalone fixed servers continue to accept historical zero
        // profile bytes, but do not silently accept a mismatched new client.
        if offered.NormalFec!=0&&offered.NormalFec!=opt.NormalFec {
            _=writeAdmissionFailure(tlsConn,admissionParamFail)
            return nil,ErrAdmissionUnsupported
        }
        selectedNormalFec=offered.NormalFec
    }
    if offered.Features!=serverFeatures||offered.GameFec!=opt.GameFec||
       (opt.GameFec!=0&&req.Policy.Transport!=TransportGame){
        _=writeAdmissionFailure(tlsConn,admissionParamFail)
        return nil,ErrAdmissionUnsupported
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
    epoch,nonce,finish,err:=opt.Epochs.prepare(req.Username,req.TunnelID,req.LaneID,offered.Epoch,source,opt.AllowLaneReplacement)
    if err!=nil {
        _=writeAdmissionFailure(tlsConn,admissionParamFail)
        return nil,err
    }
    // Every unsuccessful pre-detach path MUST roll back the reserved epoch.
    // finish is idempotent; the authenticated successful branch explicitly
    // commits only after protected reply and DetachTransition both succeed.
    defer finish(false)
    lease:=""
    manualLease,manualErr:=v4ServerCheckedManualLease4(opt.ManualLease4,req.AutoLease)
    if manualErr!=nil{
        _=writeAdmissionFailure(tlsConn,admissionParamFail)
        return nil,manualErr
    }
    if req.AutoLease {
        if cfg.AllocateLease==nil {
            _=writeAdmissionFailure(tlsConn,admissionParamFail);return nil,ErrAdmissionParams
        }
        lease,err=cfg.AllocateLease(req)
        if err!=nil || lease=="" {
            _=writeAdmissionFailure(tlsConn,admissionParamFail);return nil,errors.Join(ErrAdmissionParams,err)
        }
    }
    // Manual provisioned /32 remains server-local, not a new wire field:
    // legacy V4 manual reply expects zero lease bytes.
    result:=AdmissionResult{
        Lease4:lease,DesiredLanes:req.DesiredLanes,RecordVersion:V4RecordVersion,Policy:req.Policy,
        LaneID:req.LaneID,IncarnationNonce:nonce,TunnelID:append([]byte(nil),req.TunnelID...),
        ClientLimit:req.ClientLimit,ServerLimit:cfg.ServerLimit,
    }
    ext:=V4Extension{Features:serverFeatures,Epoch:epoch,GameFec:opt.GameFec,NormalFec:selectedNormalFec}
    state:=tlsConn.ConnectionState()
    keys,err:=v4DeriveRecordKeys(&state,result,ext)
    if err!=nil{return nil,err}
    result.Keys=keys
    result.TLSCipherSuite=state.CipherSuite
    // Prepare the immutable copy; publish only after protected reply+detach.
    frozen,err:=v4ColdSnapshot(result,epoch,req.Username,true,ext.Features)
    if err!=nil{return nil,err}
    boundary,err:=assoc.PrepareTransition(int(cfg.ServerLimit))
    if err!=nil{return nil,err}
    // The original SYN's MSS is a *limit*, captured on the same protected
    // session's actual association. It is not authentication and never
    // authorizes a native owner without the credential-checked cold source.
    observedPeer,err:=v4PeerTransportFromAssociation(assoc)
    if err!=nil{assoc.AbortTransition();return nil,err}
    // The private native owner may reserve a fresh Rust generation only after
    // a real credential-checked protected request and the exact Go boundary.
    // It MUST NOT activate or deliver early data until Detach completes.
    var prepared v4PreparedOwner
    if opt.ownerBridge!=nil {
        prepared,err=opt.ownerBridge.prepare(frozen,boundary,observedPeer)
        if err!=nil {assoc.AbortTransition();return nil,err}
        if prepared==nil {assoc.AbortTransition();return nil,ErrAdmissionParams}
        // abort is idempotent and must not destroy an already committed owner.
        defer prepared.abort()
    }
    reply,err:=v4ReplyWire(result,ext)
    if err!=nil{assoc.AbortTransition();return nil,err}
    if err:=writeFull(tlsConn,reply);err!=nil{
        assoc.AbortTransition()
        return nil,candidateError(ctx,err)
    }
    early,err:=assoc.DetachTransition()
    if err!=nil{assoc.AbortTransition();return nil,err}
    // The exact flow at protected Prepare cannot change between routing
    // handoff and CommitAdmission. A changed association invalidates this
    // candidate; never silently attach another peer's TCP sequence space.
    if assoc.Flow()!=observedPeer.flow {
        assoc.AbortTransition()
        return nil,ErrAdmissionParams
    }
    if prepared!=nil {
        // A native failure AFTER protected reply is fatal: never publish Go
        // epoch, keep owner inactive and abort this candidate, not a peer lane.
        if err:=prepared.commit(early,assoc.SenderNext());err!=nil{
            prepared.abort()
            return nil,err
        }
    }
    finish(true) // Go epoch commits only after Rust prepared owner success.
    success=true
    return &V4ServerSession{
        ServerAdmissionSession:&ServerAdmissionSession{
            TLS:&ServerSession{Hello:hello,Keys:keys},
            Negotiated:result,Boundary:boundary,EarlyRecords:early,
        },Epoch:epoch,verifiedLease4:lease,serverOwnedManualLease4:manualLease,
        coldAuthenticated:true, authenticatedPrincipal:req.Username,
        verifiedNormalFec:selectedNormalFec,verifiedCold:frozen,verifiedPolicy:result.Policy,negotiatedFeatures:ext.Features,
    },nil
}


// V4ColdSessionSnapshot is a cold, Go-only view of a real protected V4
// admission. All fields are private: callers cannot create a *positive*
// snapshot from untrusted wire bytes or an operator's DataPlaneReady boolean.
// It is NOT a Rust C ABI, Prepared/CommitAdmission, live lease, or proof that
// the still-disabled runtimeentry V4 data plane can be switched on.
//
// Rust's TunnelKey/LaneKey generation and exact RX/TX transition boundaries
// are local owner decisions, NOT derivable from Go's wire TunnelID/LaneID.
type V4ColdSessionSnapshot struct {
    server bool
    features uint16 // exporter-bound private feature, NOT Rust owner authority
    principal string
    tunnelID [16]byte
    epoch [16]byte
    incarnation [16]byte
    laneID uint8
    cipher uint8
    clientLimit uint16
    serverLimit uint16
    keys tlsrecord.KeyPair
}

// ColdSnapshot is copy-only. It never calls engine_create, activates FEC,
// touches the ABI, or changes the legacy runtime V4 fail-closed gate.
// A snapshot must still be consumed by a separately reviewed versioned
// cold Rust command with fresh owner generation and strict sequence boundaries.
func (s *V4ClientSession) ColdSnapshot() (V4ColdSessionSnapshot,error) {
    if s==nil || !s.coldAuthenticated || s.ClientAdmissionSession==nil ||
       s.ClientAdmissionSession.TLS==nil {
        return V4ColdSessionSnapshot{},ErrAdmissionUnsupported
    }
    current,err:=v4ColdSnapshot(s.Negotiated,s.Epoch,s.authenticatedPrincipal,false,s.negotiatedFeatures)
    if err!=nil{return V4ColdSessionSnapshot{},err}
    // An apparently valid post-TLS edit to cipher, limits or key material
    // must not yield a fresh "authenticated" authority.
    if current!=s.verifiedCold || s.ClientAdmissionSession.TLS.Keys!=s.verifiedCold.keys ||
       s.Negotiated.Policy!=s.verifiedPolicy {
        return V4ColdSessionSnapshot{},ErrAdmissionParams
    }
    return s.verifiedCold,nil
}
func (s *V4ServerSession) ColdSnapshot() (V4ColdSessionSnapshot,error) {
    if s==nil || !s.coldAuthenticated || s.ServerAdmissionSession==nil ||
       s.ServerAdmissionSession.TLS==nil {
        return V4ColdSessionSnapshot{},ErrAdmissionUnsupported
    }
    current,err:=v4ColdSnapshot(s.Negotiated,s.Epoch,s.authenticatedPrincipal,true,s.negotiatedFeatures)
    if err!=nil{return V4ColdSessionSnapshot{},err}
    if current!=s.verifiedCold || s.ServerAdmissionSession.TLS.Keys!=s.verifiedCold.keys ||
       s.Negotiated.Policy!=s.verifiedPolicy {
        return V4ColdSessionSnapshot{},ErrAdmissionParams
    }
    return s.verifiedCold,nil
}
func v4ColdSnapshot(result AdmissionResult,epoch [16]byte,principal string,server bool,features uint16)(V4ColdSessionSnapshot,error){
    var out V4ColdSessionSnapshot
    if !v4KnownFeatureSet(features) || principal=="" || epoch==[16]byte{} || result.RecordVersion!=V4RecordVersion ||
       len(result.TunnelID)!=16 || !validAdmissionLaneID(result.LaneID) ||
       result.ClientLimit==0 || result.ServerLimit==0 ||
       result.Policy.Schema!=PolicySchemaV3 || result.Policy.SupportedNow()!=nil {
        return out,ErrAdmissionParams
    }
    // A real protected exporter yields two independent, nonzero direction
    // keys. These checks are defensive, not a substitute for authentication.
    if result.Keys.C2S==result.Keys.S2C ||
       result.Keys.C2S==(tlsrecord.Keys{}) ||
       result.Keys.S2C==(tlsrecord.Keys{}) {
        return out,ErrAdmissionParams
    }
    copy(out.tunnelID[:],result.TunnelID)
    out.server=server
    out.features=features
    out.principal=principal
    out.epoch=epoch
    out.incarnation=result.IncarnationNonce
    out.laneID=result.LaneID
    out.cipher=result.Policy.Cipher
    out.clientLimit=result.ClientLimit
    out.serverLimit=result.ServerLimit
    out.keys=result.Keys // fixed-array value copy, never alias source buffers
    return out,nil
}

// Getters return copies. No serialization, public constructor or engine
// command is exposed before the authenticated Go→Rust C ABI review.
func (s V4ColdSessionSnapshot) Principal()string{return s.principal}
func (s V4ColdSessionSnapshot) ServerSide()bool{return s.server}
func (s V4ColdSessionSnapshot) TunnelID()[16]byte{return s.tunnelID}
func (s V4ColdSessionSnapshot) Epoch()[16]byte{return s.epoch}
func (s V4ColdSessionSnapshot) Incarnation()[16]byte{return s.incarnation}
func (s V4ColdSessionSnapshot) LaneID()uint8{return s.laneID}
func (s V4ColdSessionSnapshot) Cipher()uint8{return s.cipher}
func (s V4ColdSessionSnapshot) RecordLimits()(uint16,uint16){return s.clientLimit,s.serverLimit}
func (s V4ColdSessionSnapshot) DirectionKeys()tlsrecord.KeyPair{return s.keys}


// V4ColdBundleLen is the exact in-process, VERSIONED, cold-only boundary.
// The output carries raw AEAD keys. It must never be logged, sent on the
// network, persisted by a production process, or exposed as an attestation.
// A *parsed* Rust bundle is UNTRUSTED until a separate authenticated Go
// control capability and owner generation/boundary installation are checked.
const V4ColdBundleLen = 248

func (s V4ColdSessionSnapshot) MarshalColdBundle() ([V4ColdBundleLen]byte,error) {
    var b [V4ColdBundleLen]byte
    if s.principal=="" || s.epoch==[16]byte{} || s.incarnation==[16]byte{} ||
       s.tunnelID==[16]byte{} || !validAdmissionLaneID(s.laneID) ||
       s.cipher<CipherChaCha || s.cipher>CipherAES256 ||
       !validRecordLimit(s.clientLimit) || !validRecordLimit(s.serverLimit) ||
       s.keys.C2S==(tlsrecord.Keys{}) || s.keys.S2C==(tlsrecord.Keys{}) ||
       s.keys.C2S==s.keys.S2C {
        return b,ErrAdmissionParams
    }
    copy(b[:4],[]byte("WBCO"))
    binary.BigEndian.PutUint16(b[4:6],1)
    binary.BigEndian.PutUint16(b[6:8],V4ColdBundleLen)
    if s.server {b[8]=1}
    b[9]=s.laneID
    b[10]=s.cipher
    // b[11] and future reserved bits MUST remain zero.
    copy(b[12:28],s.tunnelID[:])
    copy(b[28:44],s.epoch[:])
    copy(b[44:60],s.incarnation[:])
    binary.BigEndian.PutUint16(b[60:62],s.clientLimit)
    binary.BigEndian.PutUint16(b[62:64],s.serverLimit)
    domain:=append([]byte("WBD-V4-COLD-PRINCIPAL\x00"),[]byte(s.principal)...)
    hash:=sha256.Sum256(domain)
    copy(b[64:96],hash[:])
    appendDir:=func(offset int,key tlsrecord.Keys) {
        copy(b[offset:offset+32],key.AEADKey[:])
        copy(b[offset+32:offset+44],key.IV[:])
        copy(b[offset+44:offset+76],key.HPKey[:])
    }
    appendDir(96,s.keys.C2S)
    appendDir(172,s.keys.S2C)
    return b,nil
}
