// TEST-ONLY Android ARM64 Go c-shared NativeBridge qualification.
// No WBD protocol logic or Java/JNI data path. The real client remains
// the original same-source Go binary + shared Rust AEAD owner.
package main

/*
#include <stdint.h>
*/
import "C"

//export WBD_AndroidGoCSharedProbe
func WBD_AndroidGoCSharedProbe() C.int {
    return 2666
}

func main() {}
