//go:build linux

package faketcp

import (
	"golang.org/x/sys/unix"
	"encoding/binary"
	"testing"
	"time"

	"golang.org/x/net/bpf"
)

// No privileged raw socket is needed: execute precisely the proposed classic
// BPF program over complete AF_PACKET-shaped frames, including IP/TCP options.
func TestDetachedDataKernelFilterPreservesHandshakeAndControl(t *testing.T) {
	local := [4]byte{192, 0, 2, 8}
	peer := [4]byte{198, 51, 100, 9}
	filters := detachedDataKernelFilter(local, 443, peer, 51000)
	raw := make([]bpf.RawInstruction, len(filters))
	for i, f := range filters {
		raw[i] = bpf.RawInstruction{Op: f.Code, Jt: f.Jt, Jf: f.Jf, K: f.K}
	}
	code, ok := bpf.Disassemble(raw)
	if !ok {
		t.Fatal("unrecognized classic BPF program")
	}
	vm, err := bpf.NewVM(code)
	if err != nil {
		t.Fatal(err)
	}
	frame := func(src [4]byte, srcPort, dstPort uint16, ipLen, tcpLen, payload int, flags byte) []byte {
		l3 := ipLen + tcpLen + payload
		b := make([]byte, 14+l3)
		b[12], b[13] = 0x08, 0x00
		b[14] = 0x40 | byte(ipLen/4)
		binary.BigEndian.PutUint16(b[16:], uint16(l3))
		b[23] = 6
		copy(b[26:30], src[:])
		copy(b[30:34], local[:])
		tcp := 14 + ipLen
		binary.BigEndian.PutUint16(b[tcp:], srcPort)
		binary.BigEndian.PutUint16(b[tcp+2:], dstPort)
		b[tcp+12] = byte(tcpLen/4) << 4
		b[tcp+13] = flags
		return b
	}
	cases := []struct {
		name   string
		b      []byte
		wantGo bool
	}{
		{"matching detached ordinary DATA", frame(peer, 51000, 443, 20, 20, 128, 0x18), false},
		{"matching detached DATA IP and TCP options", frame(peer, 51000, 443, 24, 32, 64, 0x10), false},
		{"matching pure ACK control", frame(peer, 51000, 443, 20, 20, 0, 0x10), true},
		{"matching FIN control", frame(peer, 51000, 443, 20, 20, 0, 0x11), true},
		{"matching RST control", frame(peer, 51000, 443, 20, 20, 0, 0x14), true},
		{"same tuple new SYN with payload", frame(peer, 51000, 443, 20, 20, 16, 0x12), true},
		{"new peer on listening port", frame([4]byte{198, 51, 100, 10}, 51000, 443, 20, 20, 50, 0x18), true},
		{"new peer port", frame(peer, 51001, 443, 20, 20, 50, 0x18), true},
		{"unrelated local port", frame(peer, 51000, 444, 20, 20, 50, 0x18), false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			n, err := vm.Run(tc.b)
			if err != nil {
				t.Fatal(err)
			}
			if (n != 0) != tc.wantGo {
				t.Fatalf("kernel gate return=%d wantGo=%v", n, tc.wantGo)
			}
		})
	}
}


// PLAN028 Game2/4 single shared server port must exclude every authenticated
// lane from Go AFTER Rust attach; a new 5-tuple on the port remains eligible
// for protected TLS even behind the same NAT. Pure classic-BPF VM, no mocks
// of Go/Rust identity and no root privileges.
func TestPLAN028SharedGamePortKernelFourTupleGate(t *testing.T){
    local:=[4]byte{192,0,2,8}
    peers:=[]DetachedPeer{
        {IP:[4]byte{198,51,100,9},Port:50011},
        {IP:[4]byte{198,51,100,9},Port:50012},
        {IP:[4]byte{198,51,100,10},Port:55103},
        {IP:[4]byte{203,0,113,12},Port:55104},
    }
    filter,err:=detachedDataKernelFilterSet(local,443,peers)
    if err!=nil{t.Fatal(err)}
    raw:=make([]bpf.RawInstruction,len(filter))
    for i,f:=range filter{raw[i]=bpf.RawInstruction{Op:f.Code,Jt:f.Jt,Jf:f.Jf,K:f.K}}
    decoded,ok:=bpf.Disassemble(raw)
    if !ok{t.Fatal("invalid single-listener cBPF")}
    vm,err:=bpf.NewVM(decoded)
    if err!=nil{t.Fatal(err)}
    frame:=func(src [4]byte,srcPort,dstPort uint16,ipLen,tcpLen,payload int,flags byte)[]byte{
        size:=ipLen+tcpLen+payload
        data:=make([]byte,14+size)
        data[12],data[13]=8,0
        data[14]=0x40|byte(ipLen/4)
        binary.BigEndian.PutUint16(data[16:],uint16(size))
        data[23]=6
        copy(data[26:30],src[:])
        copy(data[30:34],local[:])
        tcp:=14+ipLen
        binary.BigEndian.PutUint16(data[tcp:],srcPort)
        binary.BigEndian.PutUint16(data[tcp+2:],dstPort)
        data[tcp+12]=byte(tcpLen/4)<<4
        data[tcp+13]=flags
        return data
    }
    for _,peer:=range peers{
        for _,tc:=range []struct{payload int;flags byte;ipLen,tcpLen int;wantGo bool}{
            {128,0x18,20,20,false},
            {64,0x10,24,32,false},
            {0,0x10,20,20,true}, // pure ACK
            {23,0x02,20,20,true}, // new SYN
            {23,0x01,20,20,true}, // FIN
            {23,0x04,20,20,true}, // RST
        }{
            got,err:=vm.Run(frame(peer.IP,peer.Port,443,tc.ipLen,tc.tcpLen,tc.payload,tc.flags))
            if err!=nil{t.Fatal(err)}
            if (got!=0)!=tc.wantGo{
                t.Fatalf("peer=%v:%d flags=%x payload=%d got=%d wantGo=%t",
                    peer.IP,peer.Port,tc.flags,tc.payload,got,tc.wantGo)
            }
        }
    }
    for _,tc:=range []struct{src [4]byte;port,dst uint16;want bool}{
        {peers[0].IP,60000,443,true}, // same NAT, new client
        {[4]byte{198,51,100,99},50011,443,true}, // same port, new IP
        {peers[0].IP,peers[0].Port,444,false}, // unrelated listener port
    }{
        result,err:=vm.Run(frame(tc.src,tc.port,tc.dst,20,20,128,0x18))
        if err!=nil|| (result!=0)!=tc.want{
            t.Fatalf("new tuple classification port=%d dst=%d got=%d err=%v",tc.port,tc.dst,result,err)
        }
    }
    if _,err:=detachedDataKernelFilterSet(local,443,append(peers,peers[0]));err==nil{
        t.Fatal("duplicate/overcapacity kernel tuple set admitted")
    }
    if _,err:=detachedDataKernelFilterSet(local,443,nil);err==nil{
        t.Fatal("empty detached set admitted")
    }
    if _,err:=detachedDataKernelFilterSet(local,443,[]DetachedPeer{{IP:peers[0].IP,Port:0}});err==nil{
        t.Fatal("invalid peer port admitted")
    }
}


// PLAN028 real single-server-port: 32 separately authenticated device
// flow tuples, including multiple clients behind the same NAT address.
// The real classic-BPF VM verifies this is still a FILTER, not Go DATA
// copy or an in-process simulated router.
func TestPLAN028OriginalTLS32ConcurrentPortKernelExclusion(t *testing.T){
    local:=[4]byte{192,0,2,8}
    nat:=[4]byte{198,51,100,9}
    peers:=make([]DetachedPeer,32)
    for i:=range peers{
        peers[i]=DetachedPeer{IP:nat,Port:uint16(50000+i)}
    }
    if _,err:=detachedDataKernelFilterSet(local,443,append(peers,
       DetachedPeer{IP:nat,Port:50032}));err==nil{
        t.Fatal("33rd flow bypassed bounded original raw listener")
    }
    program,err:=detachedDataKernelFilterSet(local,443,peers)
    if err!=nil{t.Fatal(err)}
    raw:=make([]bpf.RawInstruction,len(program))
    for i,f:=range program{
        raw[i]=bpf.RawInstruction{Op:f.Code,Jt:f.Jt,Jf:f.Jf,K:f.K}
    }
    decoded,ok:=bpf.Disassemble(raw)
    if !ok{t.Fatal("32-connection cBPF invalid")}
    vm,err:=bpf.NewVM(decoded)
    if err!=nil{t.Fatal(err)}
    frame:=func(srcPort uint16,flags byte)[]byte{
        data:=make([]byte,14+20+20+48)
        data[12],data[13]=8,0
        data[14]=0x45
        binary.BigEndian.PutUint16(data[16:],88)
        data[23]=6
        copy(data[26:30],nat[:])
        copy(data[30:34],local[:])
        binary.BigEndian.PutUint16(data[34:],srcPort)
        binary.BigEndian.PutUint16(data[36:],443)
        data[46]=0x50
        data[47]=flags
        return data
    }
    for _,peer:=range peers{
        n,err:=vm.Run(frame(peer.Port,0x18))
        if err!=nil||n!=0{
            t.Fatalf("old Rust-owned DATA exposed to Go %d: n=%d err=%v",peer.Port,n,err)
        }
        n,err=vm.Run(frame(peer.Port,0x02))
        if err!=nil||n==0{
            t.Fatalf("new control/SYN suppressed %d: n=%d err=%v",peer.Port,n,err)
        }
    }
    n,err:=vm.Run(frame(50032,0x18))
    if err!=nil||n==0{
        t.Fatalf("new same-NAT client lost admission: n=%d err=%v",n,err)
    }
}

// Once the final genuine native Game owner is drained, reusing an old
// NAT four-tuple must not silently blackhole the NEXT original TLS ClientHello.
// Compare the exact Linux socket BPF programs, not a Go mock of the decision.
func TestPLAN028GameLastGroupRearmsOriginalTLSFourTuple(t *testing.T){
    local:=[4]byte{192,0,2,8}
    peer:=DetachedPeer{IP:[4]byte{198,51,100,9},Port:41031}
    detached,err:=detachedDataKernelFilterSet(local,443,[]DetachedPeer{peer})
    if err!=nil{t.Fatal(err)}
    bootstrap:=rawReceivePortFilter(local,443)
    run:=func(ins []unix.SockFilter,srcPort,dstPort uint16)int{
        t.Helper()
        raw:=make([]bpf.RawInstruction,len(ins))
        for i,x:=range ins{raw[i]=bpf.RawInstruction{
            Op:x.Code,Jt:x.Jt,Jf:x.Jf,K:x.K,
        }}
        decoded,ok:=bpf.Disassemble(raw)
        if !ok{t.Fatal("invalid exact Linux AF_PACKET BPF")}
        vm,e:=bpf.NewVM(decoded)
        if e!=nil{t.Fatal(e)}
        // Ethernet + IPv4/20 + TCP/20 + TLS payload/64.
        b:=make([]byte,14+20+20+64)
        b[12],b[13]=8,0;b[14]=0x45;b[23]=6
        binary.BigEndian.PutUint16(b[16:],uint16(20+20+64))
        copy(b[26:30],peer.IP[:]);copy(b[30:34],local[:])
        binary.BigEndian.PutUint16(b[34:],srcPort)
        binary.BigEndian.PutUint16(b[36:],dstPort)
        b[46]=0x50;b[47]=0x18 // TCP data offset, PSH|ACK
        accepted,e:=vm.Run(b)
        if e!=nil{t.Fatal(e)}
        return accepted
    }
    if n:=run(detached,peer.Port,443);n!=0{
        t.Fatalf("old detached Game DATA reentered Go: n=%d",n)
    }
    if n:=run(bootstrap,peer.Port,443);n==0{
        t.Fatal("after last Game Stop original TLS payload from recycled tuple blackholed")
    }
    if n:=run(bootstrap,peer.Port,444);n!=0{
        t.Fatal("restored TLS port filter leaked unrelated server port")
    }
}


// A lost final TLS reply ACK must not strand the original server's
// ACK-barrier after the client hands the DATA RX lane to native Rust M4.
// No raw socket privileges required: this uses the actual FakeTCP Sender
// ACK barrier and the exported, state-gated duplicate pure ACK.
func TestPLAN028DetachedLastProtectedTLSAckUnblocksOriginalSender(t *testing.T){
    sender:=NewSender(7000,time.Second)
    wire:=sender.Enqueue([]byte{0xaa,0xbb,0xcc},time.Now())
    f:=ClientFlow{
        LocalIP:[4]byte{10,50,0,2},PeerIP:[4]byte{10,50,0,1},
        LocalPort:50123,PeerPort:443,
    }
    emitted:=make([]Segment,0,3)
    assoc,err:=NewClientAssociation(f,3500,time.Second,func(s Segment)error{
        emitted=append(emitted,s)
        return nil
    })
    if err!=nil{t.Fatal(err)}
    stream,err:=NewBootstrapStream(wire.End,
        func([]byte)(uint32,error){return 0,nil},
        func(uint32,time.Time)error{return nil},nil,nil)
    if err!=nil{t.Fatal(err)}
    assoc.mu.Lock()
    assoc.state=ClientAssociationDetached
    assoc.bootstrap=stream
    assoc.mu.Unlock()
    if err:=assoc.RepeatDetachedBootstrapACK();err!=nil{t.Fatal(err)}
    if len(emitted)!=1{t.Fatalf("duplicate ACK count=%d",len(emitted))}
    ack:=emitted[0]
    if ack.Ack!=wire.End||ack.Flags!=FlagACK||len(ack.Payload)!=0||
        ack.Seq!=assoc.sender.NextSeq()||ack.SrcPort!=f.LocalPort||
        ack.DstPort!=f.PeerPort{
        t.Fatalf("not an exact cumulative pre-M4 pure ACK: %+v",ack)
    }
    if err:=sender.AckChecked(ack.Ack,time.Now());err!=nil{t.Fatal(err)}
    if err:=sender.WaitAck(wire.End,time.Now().Add(100*time.Millisecond));err!=nil{
        t.Fatalf("lost final reply ACK barrier not restored: %v",err)
    }
    if err:=assoc.RepeatDetachedBootstrapACK();err!=nil{t.Fatal(err)}
    if len(emitted)!=2||emitted[1].Seq!=ack.Seq||
        emitted[1].Ack!=ack.Ack||emitted[1].Flags!=FlagACK||
        len(emitted[1].Payload)!=0{
        t.Fatal("the original detached duplicate ACK changed seq/ACK or emitted DATA")
    }
    assoc.mu.Lock();assoc.state=ClientAssociationClosed;assoc.mu.Unlock()
    if err:=assoc.RepeatDetachedBootstrapACK();err==nil||len(emitted)!=2{
        t.Fatal("closed native client emitted another TCP packet after exact Stop")
    }
}
