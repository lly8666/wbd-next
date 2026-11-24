// TEST-ONLY Go runtime isolate. The actual original-Go client is tested
// separately; this program has no WBD TLS/auth/lease or fake protocol.
package main

import (
    "fmt"
    "runtime"
)

func main() {
    fmt.Printf("WBD_ANDROID_ARM64_PURE_GO_RUNTIME_PASS os=%s arch=%s\n", runtime.GOOS, runtime.GOARCH)
}
