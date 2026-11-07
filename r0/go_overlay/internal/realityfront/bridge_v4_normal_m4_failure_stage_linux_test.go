//go:build linux && cgo && wbd_v4_embedded_go

package realityfront

import (
    "errors"
    "fmt"
    "strings"
    "testing"
)

// A genuine server Normal admission can reject after the protected TLS
// reply and client local Ready. This verifies that the native refusal is
// identifiable at its precise M4 boundary, without ever logging untrusted
// error text or losing errors.Is/As and an original numeric Rust status.
func TestPLAN028NormalM4StageErrorPreservesEvidenceAndSecrets(t *testing.T){
    status:=&v4EmbeddedNativeStatus{Operation:"rust_loop_start",Code:7}
    cause:=fmt.Errorf("%w: Rust original owner loop=%d",status,status.Code)
    wrapped:=errors.Join(normalM4Fail("rust_loop_start",cause),
        errors.New("cleanup completed"))
    if V4NormalM4FailureStage(wrapped)!="rust_loop_start"{
        t.Fatalf("lost native M4 failure stage: %q",V4NormalM4FailureStage(wrapped))
    }
    if V4NormalM4NativeCode(wrapped)!=7{
        t.Fatalf("lost native RC: %d",V4NormalM4NativeCode(wrapped))
    }
    if !errors.Is(wrapped,errV4Embedded){t.Fatal("lost original fail-closed error")}
    if strings.Contains(wrapped.Error(),"user-secret")||
        strings.Contains(wrapped.Error(),"internal account"){
        t.Fatal("unsafe rejection diagnostic")
    }
    if V4NormalM4FailureStage(errors.New("unknown"))!="unclassified"||
        V4NormalM4NativeCode(errors.New("unknown"))!=-1{
        t.Fatal("untyped failure must stay explicit unknown, never pretend native RC=0")
    }
}

// A verified Game4 replacement may fail *after* FakeTCP Detach. Distinguish
// early 64-record Rust staging from final native Commit, never confuse a
// client-local M4 Ready with a real server native owner.
func TestPLAN028Game4OriginalM4CommitSubstageIsTypedAndSecretFree(t *testing.T){
    for _,operation:=range []string{"original_early_stage","original_native_commit"}{
        status:=&v4EmbeddedNativeStatus{Operation:operation,Code:1}
        wrapped:=fmt.Errorf("%w: protected server native M4 refused",fmt.Errorf(
            "%w: protected after-reply",status))
        if V4OriginalNativeM4FailureStage(wrapped)!=operation{
            t.Fatalf("lost exact authenticated native M4 substage: %s",operation)
        }
        if V4NormalM4NativeCode(wrapped)!=1||!errors.Is(wrapped,errV4Embedded){
            t.Fatalf("lost real native refusal: %s",operation)
        }
        if strings.Contains(wrapped.Error(),"passphrase")||strings.Contains(wrapped.Error(),"secret"){
            t.Fatal("native failure exposed secret-looking field")
        }
    }
    if got:=V4OriginalNativeM4FailureStage(errors.New("untyped"));got!="unclassified"{
        t.Fatalf("unknown M4 substage fabricated: %s",got)
    }
    if got:=V4OriginalNativeM4FailureStage(&v4EmbeddedNativeStatus{
        Operation:"raw_rx_attach",Code:4,
    });got!="unclassified"{
        t.Fatalf("other native stage mislabeled as protected Commit: %s",got)
    }
}
