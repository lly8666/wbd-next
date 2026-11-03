//go:build linux

package faketcp

import (
	"encoding/binary"
	"errors"
	"net"

	"golang.org/x/sys/unix"
)

// detachedDataKernelFilter starts with the existing receive-port filter. Before
// an authenticated ownership transfer, the original Go listener must see
// every TLS/bootstrap DATA packet. Afterwards ONLY payload-bearing packets
// from the detached four-tuple are excluded at socket ingress; new SYNs,
// pure ACK/FIN/RST, and other peers on the listening port remain visible.
// Both Normal and Game Rust M4 owners have independently opened exact-tuple
// raw receivers before this gate is armed.
func detachedDataKernelFilter(local [4]byte, port uint16, peer [4]byte, peerPort uint16) []unix.SockFilter {
	filters := rawReceivePortFilter(local, port)
	// Port-filter accept (instruction 14) continues to the tuple/data gate.
	// Its original reject at 15 remains the target of all earlier branches.
	filters[len(filters)-2] = unix.SockFilter{Code: unix.BPF_JMP | unix.BPF_JA, K: 1}
	acceptJumps := make([]int, 0, 4)
	appendCheck := func(ins unix.SockFilter, acceptOnFalse bool) {
		idx := len(filters)
		filters = append(filters, ins)
		if acceptOnFalse {
			acceptJumps = append(acceptJumps, idx)
		}
	}
	filters = append(filters, unix.SockFilter{Code: unix.BPF_LD | unix.BPF_W | unix.BPF_ABS, K: 26}) // IPv4 source
	appendCheck(unix.SockFilter{Code: unix.BPF_JMP | unix.BPF_JEQ | unix.BPF_K, K: binary.BigEndian.Uint32(peer[:])}, true)
	filters = append(filters,
		unix.SockFilter{Code: unix.BPF_LDX | unix.BPF_B | unix.BPF_MSH, K: 14}, // X = IP header bytes
		unix.SockFilter{Code: unix.BPF_LD | unix.BPF_H | unix.BPF_IND, K: 14},  // TCP source port
	)
	appendCheck(unix.SockFilter{Code: unix.BPF_JMP | unix.BPF_JEQ | unix.BPF_K, K: uint32(peerPort)}, true)
	filters = append(filters, unix.SockFilter{Code: unix.BPF_LD | unix.BPF_B | unix.BPF_IND, K: 27}) // TCP flags
	flagJump := len(filters)
	filters = append(filters, unix.SockFilter{Code: unix.BPF_JMP | unix.BPF_JSET | unix.BPF_K, K: 0x07}) // FIN|SYN|RST -> Go
	filters = append(filters,
		unix.SockFilter{Code: unix.BPF_LD | unix.BPF_H | unix.BPF_ABS, K: 16}, // IP total length
		unix.SockFilter{Code: unix.BPF_ST, K: 0},
		unix.SockFilter{Code: unix.BPF_LD | unix.BPF_B | unix.BPF_ABS, K: 14},
		unix.SockFilter{Code: unix.BPF_ALU | unix.BPF_AND | unix.BPF_K, K: 0x0f},
		unix.SockFilter{Code: unix.BPF_ALU | unix.BPF_LSH | unix.BPF_K, K: 2},
		unix.SockFilter{Code: unix.BPF_ST, K: 1}, // IP header bytes
		unix.SockFilter{Code: unix.BPF_LDX | unix.BPF_B | unix.BPF_MSH, K: 14},
		unix.SockFilter{Code: unix.BPF_LD | unix.BPF_B | unix.BPF_IND, K: 26}, // TCP data offset
		unix.SockFilter{Code: unix.BPF_ALU | unix.BPF_AND | unix.BPF_K, K: 0xf0},
		unix.SockFilter{Code: unix.BPF_ALU | unix.BPF_RSH | unix.BPF_K, K: 2},
		unix.SockFilter{Code: unix.BPF_MISC | unix.BPF_TAX}, // X = TCP header bytes
		unix.SockFilter{Code: unix.BPF_LD | unix.BPF_W | unix.BPF_MEM, K: 0},
		unix.SockFilter{Code: unix.BPF_ALU | unix.BPF_SUB | unix.BPF_X},
		unix.SockFilter{Code: unix.BPF_LDX | unix.BPF_W | unix.BPF_MEM, K: 1},
		unix.SockFilter{Code: unix.BPF_ALU | unix.BPF_SUB | unix.BPF_X},
	)
	zeroPayloadJump := len(filters)
	filters = append(filters,
		unix.SockFilter{Code: unix.BPF_JMP | unix.BPF_JEQ | unix.BPF_K, K: 0},
		unix.SockFilter{Code: unix.BPF_RET | unix.BPF_K, K: 0},          // detached DATA: drop before Go read/copy
		unix.SockFilter{Code: unix.BPF_RET | unix.BPF_K, K: ^uint32(0)}, // all other packets: preserve Go
	)
	accept := len(filters) - 1
	for _, idx := range acceptJumps {
		filters[idx].Jf = uint8(accept - idx - 1)
	}
	filters[flagJump].Jt = uint8(accept - flagJump - 1)
	filters[zeroPayloadJump].Jt = uint8(accept - zeroPayloadJump - 1)
	return filters
}

// ExcludeDetachedData is called only after the complete, authenticated
// Go->Rust Normal or Game M4 handoff reports success. Fail closed if the original listener
// has no exact kernel receive-port filter; never silently pay Go DATA CPU.
// The separate raw send FD is deliberately left open for control/cleanup.
func (e *RawIPv4Endpoint) ExcludeDetachedData(peerIP [4]byte, peerPort uint16) error {
	if e == nil {
		return errors.New("faketcp: nil detached original TLS endpoint")
	}
	e.mu.Lock()
	defer e.mu.Unlock()
	if e.closed {
		return net.ErrClosed
	}
	if !e.kernelPortFilter || e.receivePort == 0 || peerPort == 0 || peerIP == ([4]byte{}) {
		return errors.New("faketcp: detached original TLS requires exact kernel port and peer scope")
	}
	ins := detachedDataKernelFilter(e.localIP, e.receivePort, peerIP, peerPort)
	program := unix.SockFprog{Len: uint16(len(ins)), Filter: &ins[0]}
	return unix.SetsockoptSockFprog(e.recvFD, unix.SOL_SOCKET, unix.SO_ATTACH_FILTER, &program)
}


// DetachedPeer is the inbound exact transport peer of a credential-checked
// original Go Game lane. All entries use one server IP and listening port.
// A same-source-IP NAT client is distinguished by its true TCP source port.
type DetachedPeer struct{
    IP [4]byte
    Port uint16
}

// Unlike installing a new classic BPF program per lane (which overwrites the
// previous exclusion), compile up to 32 authenticated TCP tuples into ONE
// existing kernel listener filter: one Game2/4 lane group OR multiple
// independent protected-TLS device sessions. New SYN/control is still visible
// on the same port while native Rust owns their DATA.
func detachedDataKernelFilterSet(local [4]byte,port uint16,peers []DetachedPeer)([]unix.SockFilter,error){
    if port==0||len(peers)<1||len(peers)>32{return nil,errors.New("faketcp: expected 1..32 independently authenticated peers")}
    seen:=make(map[DetachedPeer]bool,len(peers))
    for _,peer:=range peers{
        if peer.Port==0||peer.IP==[4]byte{}||seen[peer]{
            return nil,errors.New("faketcp: invalid or repeated authenticated Game tuple")
        }
        seen[peer]=true
    }
    filter:=rawReceivePortFilter(local,port)
    // The port filter's success return is replaced by a branch over its
    // reject instruction into the exact peer tuple checks.
    filter[len(filter)-2]=unix.SockFilter{Code:unix.BPF_JMP|unix.BPF_JA,K:1}
    jumps:=make([]int,0,len(peers))
    for _,peer:=range peers{
        filter=append(filter,
            unix.SockFilter{Code:unix.BPF_LD|unix.BPF_W|unix.BPF_ABS,K:26},
            // Jf=4 skips source-port tests plus their branch on IP mismatch.
            unix.SockFilter{Code:unix.BPF_JMP|unix.BPF_JEQ|unix.BPF_K,Jf:4,K:binary.BigEndian.Uint32(peer.IP[:])},
            unix.SockFilter{Code:unix.BPF_LDX|unix.BPF_B|unix.BPF_MSH,K:14},
            unix.SockFilter{Code:unix.BPF_LD|unix.BPF_H|unix.BPF_IND,K:14},
            // Jf=1 skips the following jump when source port mismatches.
            unix.SockFilter{Code:unix.BPF_JMP|unix.BPF_JEQ|unix.BPF_K,Jf:1,K:uint32(peer.Port)},
        )
        jumps=append(jumps,len(filter))
        filter=append(filter,unix.SockFilter{Code:unix.BPF_JMP|unix.BPF_JA})
    }
    // New peer (including one using the same NAT IP) stays eligible for TLS.
    filter=append(filter,unix.SockFilter{Code:unix.BPF_RET|unix.BPF_K,K:^uint32(0)})
    common:=len(filter)
    // Reuse the already qualified IPv4/TCP header and DATA length gate.
    // No second parser, no per-packet Go loop, no wire changes.
    original:=detachedDataKernelFilter(local,port,peers[0].IP,peers[0].Port)
    filter=append(filter,original[len(rawReceivePortFilter(local,port))+5:]...)
    accept:=len(filter)-1
    for _,idx:=range jumps{
        filter[idx].K=uint32(common-idx-1)
    }
    for idx:=common;idx<len(filter);idx++{
        ins:=&filter[idx]
        if ins.Code==unix.BPF_JMP|unix.BPF_JSET|unix.BPF_K&&ins.K==0x07{
            ins.Jt=uint8(accept-idx-1)
        }
        if ins.Code==unix.BPF_JMP|unix.BPF_JEQ|unix.BPF_K&&
           ins.K==0&&idx+1<len(filter)&&
           filter[idx+1].Code==unix.BPF_RET|unix.BPF_K&&filter[idx+1].K==0{
            ins.Jt=uint8(accept-idx-1)
        }
    }
    return filter,nil
}

// Only after every original protected TLS lane has detached and one Rust
// GameAdapter has installed exact tuple M4 receivers. A single Linux packet
// filter handles all accepted lanes; repeated ExcludeDetachedData calls would
// accidentally re-expose earlier ciphertext to the Go hot path.
func (e *RawIPv4Endpoint) ExcludeDetachedDataSet(peers []DetachedPeer)error{
    if e==nil{return errors.New("faketcp: nil shared original TLS listener")}
    e.mu.Lock()
    defer e.mu.Unlock()
    if e.closed{return net.ErrClosed}
    if !e.kernelPortFilter||e.receivePort==0{
        return errors.New("faketcp: shared Game listener requires original receive-port filter")
    }
    ins,err:=detachedDataKernelFilterSet(e.localIP,e.receivePort,peers)
    if err!=nil{return err}
    program:=unix.SockFprog{Len:uint16(len(ins)),Filter:&ins[0]}
    return unix.SetsockoptSockFprog(e.recvFD,unix.SOL_SOCKET,unix.SO_ATTACH_FILTER,&program)
}
