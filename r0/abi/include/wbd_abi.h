#ifndef WBD_R0_ABI_H
#define WBD_R0_ABI_H
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif

// R0 sentinel ONLY; not the qualified product engine.
// Explicit fixed width types; no pointers, BufferKeys or Rust repr dumps.
#define WBD_R0_ABI_VERSION 1u
#define WBD_R0_FEATURES 0ull
#define WBD_R0_OK 0
#define WBD_R0_NULL_ARG 1
#define WBD_R0_BAD_SIZE 2
#define WBD_R0_BAD_VERSION 3
#define WBD_R0_UNSUPPORTED 4
#define WBD_R0_STALE 5
#define WBD_R0_NO_CAPACITY 6
#define WBD_R0_INTERNAL 7

typedef struct WbdAbiInfoV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint64_t features;
    uint64_t reserved;
} WbdAbiInfoV1;
typedef struct WbdAbiConfigV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t flags;
    uint32_t reserved;
} WbdAbiConfigV1;
typedef struct WbdEngineToken { uint64_t value; } WbdEngineToken;
typedef struct WbdLaneToken { uint64_t value; } WbdLaneToken;

_Static_assert(sizeof(WbdAbiInfoV1)==24, "R0 ABI info size");
_Static_assert(sizeof(WbdAbiConfigV1)==16, "R0 ABI config size");
_Static_assert(sizeof(WbdEngineToken)==8, "R0 ABI engine token");
_Static_assert(sizeof(WbdLaneToken)==8, "R0 ABI lane token");
_Static_assert(offsetof(WbdAbiInfoV1,features)==8, "R0 ABI info offsets");
_Static_assert(offsetof(WbdAbiConfigV1,reserved)==12, "R0 ABI config offsets");

int32_t wbd_r0_abi_query(WbdAbiInfoV1 *out, uint32_t out_size);
int32_t wbd_r0_engine_open(const WbdAbiConfigV1 *cfg, uint32_t input_size, WbdEngineToken *out);
int32_t wbd_r0_engine_close(WbdEngineToken engine);
int32_t wbd_r0_lane_open(WbdEngineToken engine, WbdLaneToken *out);
int32_t wbd_r0_lane_close(WbdLaneToken lane);
#ifdef __cplusplus
}
#endif
#endif
