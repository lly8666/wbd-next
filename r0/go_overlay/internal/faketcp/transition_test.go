package faketcp

import (
	"bytes"
	"errors"
	"math"
	"testing"
)

func TestStageTransitionPrepareQueuesEarlyRecordWithoutFeedingTLS(t *testing.T) {
	tr, err := NewStageTransition(64)
	if err != nil {
		t.Fatal(err)
	}
	if got, err := tr.Route(90, []byte("tls")); err != nil || got != RouteBootstrap {
		t.Fatalf("pre-prepare route=%v err=%v", got, err)
	}
	if err := tr.Prepare(100); err != nil {
		t.Fatal(err)
	}
	if got, err := tr.Route(95, []byte("old")); err != nil || got != RouteBootstrap {
		t.Fatalf("late bootstrap route=%v err=%v", got, err)
	}
	if got, err := tr.Route(100, []byte("record-0")); err != nil || got != RouteQueuedRecord {
		t.Fatalf("early record route=%v err=%v", got, err)
	}
	if got, err := tr.Route(0, nil); err != nil || got != RouteAckOnly {
		t.Fatalf("ack-only route=%v err=%v", got, err)
	}
	records, bytesN := tr.QueueUsage()
	if records != 1 || bytesN != len("record-0") {
		t.Fatalf("queue records=%d bytes=%d", records, bytesN)
	}
}

func TestStageTransitionDetachTransfersQueueAndKeepsLateBootstrapOutOfRecordPath(t *testing.T) {
	tr, _ := NewStageTransition(64)
	_ = tr.Prepare(500)
	_, _ = tr.Route(500, []byte("first"))
	_, _ = tr.Route(505, []byte("second"))

	q, err := tr.Detach()
	if err != nil {
		t.Fatal(err)
	}
	if len(q) != 2 || q[0].Seq != 500 || q[1].Seq != 505 {
		t.Fatalf("queue=%#v", q)
	}
	if !bytes.Equal(q[0].Payload, []byte("first")) || !bytes.Equal(q[1].Payload, []byte("second")) {
		t.Fatalf("payloads=%q %q", q[0].Payload, q[1].Payload)
	}
	if got, err := tr.Route(490, []byte("old")); err != nil || got != RouteLateBootstrap {
		t.Fatalf("late old route=%v err=%v", got, err)
	}
	if got, err := tr.Route(510, []byte("third")); err != nil || got != RouteRecord {
		t.Fatalf("post-detach record route=%v err=%v", got, err)
	}
}

func TestStageTransitionDeduplicatesExactEarlyRetransmit(t *testing.T) {
	tr, _ := NewStageTransition(64)
	_ = tr.Prepare(100)
	if got, err := tr.Route(100, []byte("same")); err != nil || got != RouteQueuedRecord {
		t.Fatalf("first route=%v err=%v", got, err)
	}
	if got, err := tr.Route(100, []byte("same")); err != nil || got != RouteQueuedDuplicate {
		t.Fatalf("duplicate route=%v err=%v", got, err)
	}
	records, bytesN := tr.QueueUsage()
	if records != 1 || bytesN != 4 {
		t.Fatalf("queue records=%d bytes=%d", records, bytesN)
	}
}

func TestStageTransitionRejectsChangedSameSeqRetransmitAndClearsCandidate(t *testing.T) {
	tr, _ := NewStageTransition(64)
	_ = tr.Prepare(100)
	_, _ = tr.Route(100, []byte("good"))
	_, err := tr.Route(100, []byte("evil"))
	if !errors.Is(err, ErrTransitionConflict) {
		t.Fatalf("err=%v want conflict", err)
	}
	if tr.State() != TransitionAborted {
		t.Fatalf("state=%v want aborted", tr.State())
	}
	records, bytesN := tr.QueueUsage()
	if records != 0 || bytesN != 0 {
		t.Fatalf("aborted queue records=%d bytes=%d", records, bytesN)
	}
	if got, err := tr.Route(0, nil); err != nil || got != RouteAckOnly {
		t.Fatalf("pure ACK after abort route=%v err=%v", got, err)
	}
}

func TestStageTransitionBoundsCountAndWireSize(t *testing.T) {
	tr, _ := NewStageTransition(8)
	_ = tr.Prepare(1000)
	for i := 0; i < MaxTransitionRecords; i++ {
		seq := uint32(1000 + i*8)
		if got, err := tr.Route(seq, []byte("12345678")); err != nil || got != RouteQueuedRecord {
			t.Fatalf("route %d=%v err=%v", i, got, err)
		}
	}
	_, err := tr.Route(2000, []byte("x"))
	if !errors.Is(err, ErrTransitionOverflow) {
		t.Fatalf("err=%v want overflow", err)
	}
	// A full pre-detach DATA queue remains EXACTLY bounded, but excess
	// native M4 DATA is not grounds for revoking an already authenticated
	// cold server candidate while the final protected reply ACK is in flight.
	if tr.State() != TransitionPrepared {
		t.Fatalf("state=%v want prepared after recoverable overflow", tr.State())
	}
	records,bytesN:=tr.QueueUsage()
	if records!=MaxTransitionRecords || bytesN!=MaxTransitionRecords*8 {
		t.Fatalf("bounded existing DATA queue records=%d bytes=%d",records,bytesN)
	}
	queued,err:=tr.Detach()
	if err!=nil || len(queued)!=MaxTransitionRecords {
		t.Fatalf("real server Detach after early-data burst records=%d err=%v",len(queued),err)
	}

	tr2, _ := NewStageTransition(8)
	_ = tr2.Prepare(10)
	_, err = tr2.Route(10, []byte("123456789"))
	if !errors.Is(err, ErrTransitionRecordSize) {
		t.Fatalf("err=%v want size", err)
	}
	if tr2.State()!=TransitionAborted {
		t.Fatal("out-of-budget record remains fail-closed")
	}
}

func TestStageTransitionRejectsBoundaryOverlap(t *testing.T) {
	tr, _ := NewStageTransition(64)
	_ = tr.Prepare(100)
	_, err := tr.Route(99, []byte{1, 2})
	if !errors.Is(err, ErrTransitionOverlap) {
		t.Fatalf("err=%v want overlap", err)
	}
	if tr.State() != TransitionAborted {
		t.Fatalf("state=%v want aborted", tr.State())
	}
}

func TestStageTransitionBoundaryWrap(t *testing.T) {
	tr, _ := NewStageTransition(64)
	_ = tr.Prepare(2)
	if got, err := tr.Route(math.MaxUint32-1, []byte{1, 2, 3, 4}); err != nil || got != RouteBootstrap {
		t.Fatalf("wrapped bootstrap route=%v err=%v", got, err)
	}
	if got, err := tr.Route(2, []byte("new")); err != nil || got != RouteQueuedRecord {
		t.Fatalf("wrapped new route=%v err=%v", got, err)
	}
}

func TestStageTransitionPrepareDetachStateMachine(t *testing.T) {
	tr, _ := NewStageTransition(64)
	if _, ok := tr.Boundary(); ok {
		t.Fatal("boundary visible before prepare")
	}
	if err := tr.Prepare(77); err != nil {
		t.Fatal(err)
	}
	if b, ok := tr.Boundary(); !ok || b != 77 {
		t.Fatalf("boundary=%d ok=%v", b, ok)
	}
	if err := tr.Prepare(88); !errors.Is(err, ErrTransitionState) {
		t.Fatalf("second prepare err=%v", err)
	}
	if _, err := tr.Detach(); err != nil {
		t.Fatal(err)
	}
	if _, err := tr.Detach(); !errors.Is(err, ErrTransitionState) {
		t.Fatalf("second detach err=%v", err)
	}
}
