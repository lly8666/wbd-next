//go:build linux && cgo && wbd_v4_embedded_go

package v4productcli

import (
    "bytes"
    "context"
    "sync"
    "testing"
    "time"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
)

// This uses the real original FakeTCP cumulative-ACK sender and bootstrap
// conn. The simulated underlay drops the client's first TLS application
// segment but keeps the original SYN/SYNACK. No synthetic ACK or second
// packet owner is permitted to unstick the original Write.
func TestPLAN028OriginalClientFakeTCPTLSDataRTOAndDetachBound(t *testing.T){
    // Original FakeTCP requires a native-derived, explicitly installed SYN
    // MSS. This deterministic test uses the same legal 1460 value, not a
    // bypass of the production guard.
    if err:=faketcp.SetPublicV4AdvertisedMSS(1460);err!=nil{t.Fatal(err)}
    flow:=faketcp.ClientFlow{
        LocalIP:[4]byte{10,0,0,2},PeerIP:[4]byte{10,0,0,1},
        LocalPort:55043,PeerPort:443,
    }
    var mu sync.Mutex
    var sent []faketcp.Segment
    emit:=func(seg faketcp.Segment)error{
        seg.Payload=append([]byte(nil),seg.Payload...)
        mu.Lock();sent=append(sent,seg);mu.Unlock()
        return nil
    }
    assoc,err:=faketcp.NewClientAssociation(flow,1000,time.Second,emit)
    if err!=nil{t.Fatal(err)}
    defer assoc.Close()
    if err=assoc.Start(time.Now());err!=nil{t.Fatal(err)}
    inbound:=faketcp.Segment{
        SrcIP:flow.PeerIP,DstIP:flow.LocalIP,
        SrcPort:flow.PeerPort,DstPort:flow.LocalPort,
        Seq:2000,Ack:1001,Flags:faketcp.FlagSYN|faketcp.FlagACK,
        Window:65535,MSS:1460,MSSSet:true,
    }
    if err=assoc.HandleSegment(inbound,time.Now());err!=nil{t.Fatal(err)}
    if assoc.State()!=faketcp.ClientAssociationEstablished{
        t.Fatal("client did not establish real FakeTCP")
    }
    ctx,cancel:=context.WithTimeout(context.Background(),3500*time.Millisecond)
    defer cancel()
    stop:=driveOriginalClientColdBootstrapRTO(ctx,assoc)
    result:=make(chan error,1)
    conn:=assoc.BootstrapConn()
    if conn==nil{t.Fatal("missing original bootstrap stream")}
    payload:=[]byte("original authenticated TLS client request payload - rto")
    go func(){_,err:=conn.Write(payload);result<-err}()
    deadline:=time.Now().Add(2800*time.Millisecond)
    var first *faketcp.Segment
    repeated:=false
    for time.Now().Before(deadline){
        mu.Lock()
        for _,seg:=range sent{
            if len(seg.Payload)==0{continue}
            if first==nil{
                s:=seg
                first=&s
            }else if seg.Seq==first.Seq&&bytes.Equal(seg.Payload,first.Payload){
                repeated=true
                break
            }
        }
        mu.Unlock()
        if repeated{break}
        time.Sleep(25*time.Millisecond)
    }
    n,rtoErr:=stop()
    if rtoErr!=nil||n==0||first==nil||!repeated{
        t.Fatalf("original TLS sender never retried without ACK: count=%d err=%v first=%v duplicate=%v",n,rtoErr,first!=nil,repeated)
    }
    if !bytes.Equal(first.Payload,payload){
        t.Fatalf("cold retransmission mutated original payload")
    }
    // No second controller survives the authenticated bootstrap: once
    // the cold RTO pump is stopped the packet source must stay frozen.
    mu.Lock();before:=len(sent);mu.Unlock()
    time.Sleep(225*time.Millisecond)
    mu.Lock();after:=len(sent);mu.Unlock()
    if after!=before{
        t.Fatalf("original DATA retransmitted after cold guard Stop: %d -> %d",before,after)
    }
    // The blocked original Write is intentionally unacked. Close releases
    // it; the test never manufactures peer ACK for an absent packet.
    assoc.Close()
    select{
    case <-result:
    case <-time.After(time.Second):
        t.Fatal("original sender Write leaked after owner Stop")
    }
}
