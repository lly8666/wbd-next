/* R0 cross-target ABI layout + Rust dynamic-library link probe.
 * Compile/link only: NEVER run on an unrelated Actions host.
 */
#include "wbd_abi.h"

_Static_assert(sizeof(void*) == 8, "R0 targets require 64-bit pointers");
_Static_assert(sizeof(uint32_t) == 4 && sizeof(uint64_t) == 8, "C width");
_Static_assert(sizeof(WbdAbiInfoV1) == 24, "info layout");
_Static_assert(_Alignof(WbdAbiInfoV1) == 8, "info alignment");
_Static_assert(offsetof(WbdAbiInfoV1, abi_version) == 0, "info version offset");
_Static_assert(offsetof(WbdAbiInfoV1, struct_size) == 4, "info size offset");
_Static_assert(offsetof(WbdAbiInfoV1, features) == 8, "info features offset");
_Static_assert(offsetof(WbdAbiInfoV1, reserved) == 16, "info reserved offset");
_Static_assert(sizeof(WbdAbiConfigV1) == 16, "config layout");
_Static_assert(offsetof(WbdAbiConfigV1, abi_version) == 0, "config version offset");
_Static_assert(offsetof(WbdAbiConfigV1, struct_size) == 4, "config size offset");
_Static_assert(offsetof(WbdAbiConfigV1, flags) == 8, "config flags offset");
_Static_assert(offsetof(WbdAbiConfigV1, reserved) == 12, "config reserved offset");
_Static_assert(sizeof(WbdEngineToken) == 8 && sizeof(WbdLaneToken) == 8, "opaque tokens");

int main(void) {
    /* Refer to every exported ABI symbol so linking tests compatibility,
     * not just C preprocessing or Rust source-code visibility.
     * These calls are never executed in the cross-build workflow.
     */
    WbdAbiInfoV1 info = {0};
    WbdAbiConfigV1 cfg = {WBD_R0_ABI_VERSION, sizeof(WbdAbiConfigV1), 0, 0};
    WbdEngineToken engine = {0};
    WbdLaneToken lane = {0};
    if (wbd_r0_abi_query(&info, sizeof(info)) != WBD_R0_OK) return 1;
    if (info.features != WBD_R0_FEATURES || info.abi_version != WBD_R0_ABI_VERSION) return 2;
    if (wbd_r0_engine_open(&cfg, sizeof(cfg), &engine) != WBD_R0_OK) return 3;
    if (wbd_r0_lane_open(engine, &lane) != WBD_R0_OK) return 4;
    if (wbd_r0_lane_close(lane) != WBD_R0_OK) return 5;
    if (wbd_r0_engine_close(engine) != WBD_R0_OK) return 6;
    return 0;
}
