//go:build linux

package faketcp

import (
	"encoding/binary"
	"testing"

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
