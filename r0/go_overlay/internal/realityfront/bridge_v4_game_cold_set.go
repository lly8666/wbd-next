package realityfront

// PLAN012 original-Go Game 2/4 cold set. This is a read-only bridge input,
// never a credential grant, FEC2 public opt-in, kernel send, or Stop authority.
// Only genuine post-TLS V4 sessions can supply ColdSnapshot. Each original
// logical lane must have its own exporter keys and immutable policy.
func v4CheckAuthenticatedGameLanes(
    snapshots []V4ColdSessionSnapshot, policies []AdmissionPolicy, server bool,
)([]V4ColdSessionSnapshot,error){
    n:=len(snapshots)
    if (n!=2&&n!=4)||len(policies)!=n{return nil,ErrAdmissionParams}
    var ordered [4]V4ColdSessionSnapshot
    var seen uint8
    for i,cold:=range snapshots{
        p:=policies[i]
        if cold.server!=server||cold.principal==""||
            cold.epoch==[16]byte{}||cold.tunnelID==[16]byte{}||
            (cold.features!=v4RequiredFeatures &&
                cold.features!=(v4RequiredFeatures|v4FeatureFEC2))||
            p.Transport!=TransportGame||p.DesiredLanes!=uint8(n)||
            cold.laneID==0||int(cold.laneID)>n{
            return nil,ErrAdmissionUnsupported
        }
        slot:=cold.laneID-1
        bit:=uint8(1)<<slot
        if seen&bit!=0{return nil,ErrAdmissionParams}
        seen|=bit
        if i!=0{
            base:=snapshots[0]
            if cold.principal!=base.principal||
                cold.tunnelID!=base.tunnelID||cold.epoch!=base.epoch||
                cold.features!=base.features||cold.cipher!=base.cipher||
                cold.clientLimit!=base.clientLimit||
                cold.serverLimit!=base.serverLimit{
                return nil,ErrAdmissionParams
            }
            for _,prior:=range snapshots[:i]{
                if cold.incarnation==prior.incarnation||
                    cold.keys.C2S==prior.keys.C2S||
                    cold.keys.S2C==prior.keys.S2C{
                    return nil,ErrAdmissionParams
                }
            }
        }
        ordered[slot]=cold
    }
    if seen!=uint8((1<<n)-1){return nil,ErrAdmissionParams}
    // A private cold copy cannot itself activate a driver, issue APPLIED,
    // or authorize production. Only one later original owner can commit
    // these session-scoped lane inputs after verified kernel admission.
    return append([]V4ColdSessionSnapshot(nil),ordered[:n]...),nil
}

// The protected request's lane is trusted only inside EstablishServerV4
// after original TLS credentials. A Game connection's raw source port,
// SYN arrival index and collection index are NOT lane identities.
func v4ServerGameProtectedLaneRequest(req AdmissionRequest,n int)error{
    if (n!=2&&n!=4)||req.LaneID==0||int(req.LaneID)>n||
        req.DesiredLanes!=uint8(n){return ErrAdmissionUnsupported}
    return nil
}

// Map async protected-TLS completion indices back to immutable 1..n lanes.
// The original TLS snapshot verifier also enforces a single principal,
// tunnel, epoch, cipher, limits and independent exporter keys. Never install
// per-lane M4/bind network before this complete set has been verified.
func v4GameServerTLSArrivalOrder(sessions []*V4ServerSession)([]int,error){
    if _,err:=v4OriginalGameServerColdSet(sessions...);err!=nil{
        return nil,err
    }
    order:=make([]int,len(sessions))
    for arrival,s:=range sessions{
        cold,err:=s.ColdSnapshot()
        if err!=nil{return nil,err}
        order[int(cold.LaneID())-1]=arrival
    }
    return order,nil
}

func v4OriginalGameClientColdSet(
    sessions ...*V4ClientSession,
)([]V4ColdSessionSnapshot,error){
    if len(sessions)!=2&&len(sessions)!=4{return nil,ErrAdmissionParams}
    snapshots:=make([]V4ColdSessionSnapshot,0,len(sessions))
    policies:=make([]AdmissionPolicy,0,len(sessions))
    for _,s:=range sessions{
        if s==nil{return nil,ErrAdmissionUnsupported}
        cold,err:=s.ColdSnapshot()
        if err!=nil{return nil,err}
        snapshots=append(snapshots,cold)
        policies=append(policies,s.verifiedPolicy)
    }
    return v4CheckAuthenticatedGameLanes(snapshots,policies,false)
}

func v4OriginalGameServerColdSet(
    sessions ...*V4ServerSession,
)([]V4ColdSessionSnapshot,error){
    if len(sessions)!=2&&len(sessions)!=4{return nil,ErrAdmissionParams}
    snapshots:=make([]V4ColdSessionSnapshot,0,len(sessions))
    policies:=make([]AdmissionPolicy,0,len(sessions))
    for _,s:=range sessions{
        if s==nil{return nil,ErrAdmissionUnsupported}
        cold,err:=s.ColdSnapshot()
        if err!=nil{return nil,err}
        snapshots=append(snapshots,cold)
        policies=append(policies,s.verifiedPolicy)
    }
    return v4CheckAuthenticatedGameLanes(snapshots,policies,true)
}
