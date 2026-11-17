//go:build android && arm64 && cgo && wbd_v4_embedded_go && wbd_ksu_cshared_test
//
// TEST-ONLY NativeBridge Go c-shared entry to the ACTUAL original-Go product.
// This is NEVER part of the signed Root APK or official Go executable.
// It calls the unmodified product Run("client") path; no fake TLS, lease,
// synthetic server, Java packet callbacks or alternate Rust implementation.
package main

/*
#include <stdint.h>
*/
import "C"

import (
    "errors"
    "flag"

    "github.com/lly8666/wobuzhidao/internal/v4productcli"
)

//export WBD_AndroidRootOriginalGoHelp
func WBD_AndroidRootOriginalGoHelp() C.int {
    // An ordinary flag.ContinueOnError --help parse exits before opening
    // TUN/RAW, making this a truthful first runtime admission only.
    err := v4productcli.Run("client", []string{"--help"})
    if errors.Is(err, flag.ErrHelp) {
        println("WBD_ANDROID_ARM64_ORIGINAL_GO_CLIENT_HELP_RETURNED")
        return 0
    }
    if err != nil {
        println("WBD_ANDROID_ARM64_ORIGINAL_GO_CLIENT_HELP_ERROR:", err.Error())
        return 2
    }
    // A surprising nil return must not silently pass a malformed CLI.
    println("WBD_ANDROID_ARM64_ORIGINAL_GO_CLIENT_HELP_UNEXPECTED_NIL")
    return 3
}
