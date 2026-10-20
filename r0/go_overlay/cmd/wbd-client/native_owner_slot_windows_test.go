//go:build windows

package main

import (
    "errors"
    "testing"

    "golang.org/x/sys/windows"
)

// TestPLAN010OwnerSlotIsActuallyExclusive proves the original Windows CLI
// slot rejects a simultaneous second owner, including same-process repeated
// CreateEvent. No network/driver/admin operations are performed.
func TestPLAN010OwnerSlotIsActuallyExclusive(t *testing.T) {
    first, err := acquireGUIClientSlot()
    if err != nil { t.Fatalf("first native owner slot: %v",err) }
    closed := false
    defer func(){ if !closed { windows.CloseHandle(first) } }()

    duplicate, duplicateErr := acquireGUIClientSlot()
    if duplicateErr == nil {
        windows.CloseHandle(duplicate)
        t.Fatal("second native Windows client acquired the same owner event")
    }
    if duplicate != 0 {
        windows.CloseHandle(duplicate)
        t.Fatal("rejected second slot leaked an owned handle")
    }
    if !errors.Is(duplicateErr, windows.ERROR_ALREADY_EXISTS) &&
        duplicateErr.Error() != "another Windows client is running or cleaning up" {
        t.Fatalf("unexpected duplicate owner failure: %v",duplicateErr)
    }
    if err:=windows.CloseHandle(first);err!=nil{t.Fatal(err)}
    closed=true
    third, err := acquireGUIClientSlot()
    if err != nil {t.Fatalf("OS event not released after closing first owner: %v",err)}
    if err:=windows.CloseHandle(third);err!=nil{t.Fatal(err)}
}
