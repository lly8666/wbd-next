//go:build linux

package faketcp

import (
	"encoding/binary"
	"errors"
	"net"

	"golang.org/x/sys/unix"
)

// detachedGameDataFilter starts with the existing receive-port filter. Before
// an authenticated ownership transfer, the original Go listener must see
// every TLS/bootstrap DATA packet. Afterwards ONLY payload-bearing packets
// from the detached four-tuple are excluded at socket ingress; new SYNs,
// pure ACK/FIN/RST, and other peers on the listening port remain visible.
// Rust has a separately opened exact-tuple raw receiver before this is armed.
func detachedGameDataFilter(local [4]byte, port uint16, peer [4]byte, peerPort uint16) []unix.SockFilter {
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

// ExcludeDetachedGameData is called only after the complete, authenticated
// Go->Rust Game handoff reports success. Fail closed if the original listener
// has no exact kernel receive-port filter; never silently pay Go DATA CPU.
// The separate raw send FD is deliberately left open for control/cleanup.
func (e *RawIPv4Endpoint) ExcludeDetachedGameData(peerIP [4]byte, peerPort uint16) error {
	if e == nil {
		return errors.New("faketcp: nil detached Game endpoint")
	}
	e.mu.Lock()
	defer e.mu.Unlock()
	if e.closed {
		return net.ErrClosed
	}
	if !e.kernelPortFilter || e.receivePort == 0 || peerPort == 0 || peerIP == ([4]byte{}) {
		return errors.New("faketcp: detached Game requires exact kernel port and peer scope")
	}
	ins := detachedGameDataFilter(e.localIP, e.receivePort, peerIP, peerPort)
	program := unix.SockFprog{Len: uint16(len(ins)), Filter: &ins[0]}
	return unix.SetsockoptSockFprog(e.recvFD, unix.SOL_SOCKET, unix.SO_ATTACH_FILTER, &program)
}
